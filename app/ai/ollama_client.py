"""Thin client for the local Ollama HTTP API."""
import json
import logging
import threading
from typing import TypeVar

import requests
from circuitbreaker import CircuitBreakerError, circuit
from pydantic import BaseModel, ValidationError

from app.ai.post_processor import PostProcessor
from app.core.settings import load_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class OllamaError(Exception):
    """Raised when the Ollama API is unreachable or returns bad data."""


class OllamaTransportError(OllamaError):
    """Network-level failure (connection refused, timeout, etc.)."""


class OllamaProtocolError(OllamaError):
    """The model returned invalid or unparseable output."""


class OllamaCancelledError(OllamaError):
    """Raised when a request is cancelled by the user."""


class AIBusyError(OllamaError):
    """Raised when another AI generation is already in progress."""


class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        settings = load_settings()
        self.base_url = (base_url or settings.ai.ollama_url).rstrip("/")
        self.model = model or settings.ai.model
        self.temperature = settings.ai.temperature
        self._cancel_event: threading.Event | None = None
        self._generation_lock = threading.Lock()
        self._post = PostProcessor()

    def set_cancel_event(self, event: threading.Event | None) -> None:
        """Set a threading.Event to check for cancellation."""
        self._cancel_event = event

    def _check_cancelled(self) -> None:
        if self._cancel_event is not None and self._cancel_event.is_set():
            raise OllamaCancelledError("Request cancelled by user")

    def list_models(self) -> list[str]:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaTransportError(f"Cannot reach Ollama at {self.base_url}: {exc}") from exc
        return [m["name"] for m in resp.json().get("models", [])]

    def generate(self, prompt: str, system: str | None = None, json_mode: bool = False) -> str:
        if not self._generation_lock.acquire(blocking=False):
            raise AIBusyError("Another AI generation is already in progress. Please wait.")
        try:
            json_schema = "json" if json_mode else None
            return self._generate_impl(prompt, system=system, json_schema=json_schema)
        except CircuitBreakerError as exc:
            logger.error("Ollama circuit breaker open — too many failures")
            raise OllamaTransportError(
                "Ollama is unresponsive (circuit breaker open). "
                "Wait 60 seconds or restart Ollama with 'ollama serve'."
            ) from exc
        except requests.RequestException as exc:
            logger.error("Ollama request failed: %s", exc)
            raise OllamaTransportError(
                f"Ollama request failed: {exc}. Is Ollama running at {self.base_url}? "
                f"Start it with 'ollama serve' and pull the model with 'ollama pull {self.model}'."
            ) from exc
        finally:
            self._generation_lock.release()

    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=requests.RequestException)
    def _generate_impl(
        self,
        prompt: str,
        system: str | None = None,
        json_schema: dict | str | None = None,
    ) -> str:
        self._check_cancelled()

        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": self.temperature,
            },
        }

        if system:
            payload["system"] = system

        if json_schema is not None:
            payload["format"] = json_schema

        pieces: list[str] = []

        try:
            logger.info("Ollama request: model=%s json_schema=%s", self.model, json_schema is not None)
            with requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=(5, 120),
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    self._check_cancelled()

                    if not line:
                        continue

                    event = json.loads(line)

                    if error_message := event.get("error"):
                        raise OllamaProtocolError(str(error_message))

                    pieces.append(str(event.get("response", "")))

                    if event.get("done"):
                        break
        except OllamaCancelledError:
            raise
        except json.JSONDecodeError as exc:
            raise OllamaProtocolError("Ollama returned malformed NDJSON.") from exc

        text = "".join(pieces)
        logger.debug("Ollama raw response (first 500 chars): %s", text[:500])

        text = self._post.clean_for_resume(text)
        return text.strip()

    def generate_json(self, prompt: str, system: str | None = None) -> dict:
        try:
            text = self.generate(prompt, system=system, json_mode=True)
        except OllamaCancelledError:
            raise
        except OllamaTransportError:
            raise
        except OllamaProtocolError:
            logger.warning("JSON mode failed, retrying without format constraint")
            text = self.generate(prompt, system=system, json_mode=False)

        result = self._post.extract_json(text)
        if not result:
            raise OllamaProtocolError("The model did not return valid JSON. Try again or switch models.")
        return result

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system: str | None = None,
        max_validation_attempts: int = 2,
    ) -> T:
        """Generate JSON and validate against a Pydantic model with retry.

        Uses Ollama's JSON-schema structured output for reliable parsing.
        Only retries on protocol/validation errors. Transport errors and
        cancellations are raised immediately.
        """
        schema_definition = schema.model_json_schema()
        last_error = None
        current_prompt = prompt

        for attempt in range(max_validation_attempts + 1):
            self._check_cancelled()

            try:
                raw = self._generate_impl(
                    current_prompt,
                    system=system,
                    json_schema=schema_definition,
                )
                return schema.model_validate_json(raw)
            except (OllamaCancelledError, OllamaTransportError):
                raise
            except (OllamaProtocolError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "Validation attempt %d/%d failed: %s",
                    attempt + 1,
                    max_validation_attempts + 1,
                    exc,
                )
                if attempt >= max_validation_attempts:
                    raise OllamaProtocolError(
                        f"Invalid structured output: {exc}"
                    ) from exc

                current_prompt = (
                    f"{prompt}\n\n"
                    "Return only data matching the supplied JSON schema. "
                    f"Previous validation error: {exc}"
                )

        raise AssertionError("Unreachable")

    def pre_warm(self) -> bool:
        """Send a minimal prompt to load the model into VRAM."""
        try:
            self.generate("hello", system="Reply with one word.")
            logger.info("Model pre-warmed successfully")
            return True
        except OllamaError:
            logger.debug("Model pre-warm skipped (Ollama not reachable)")
            return False
