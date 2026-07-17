"""Thin client for the local Ollama HTTP API."""
import json
import logging
import re
import threading
from typing import TypeVar

import requests
from pydantic import BaseModel, ValidationError

from app.core.settings import load_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def clean_ai_text(text: str) -> str:
    """
    Remove unwanted AI formatting.
    """

    replacements = [
        ("**", ""),
        ("__", ""),
        ("`", ""),
        ("<b>", ""),
        ("</b>", ""),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    return text.strip()

class OllamaError(Exception):
    """Raised when the Ollama API is unreachable or returns bad data."""


class OllamaCancelledError(OllamaError):
    """Raised when a request is cancelled by the user."""


class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        settings = load_settings()
        self.base_url = (base_url or settings.ai.ollama_url).rstrip("/")
        self.model = model or settings.ai.model
        self.temperature = settings.ai.temperature
        self._cancel_event: threading.Event | None = None

    def set_cancel_event(self, event: threading.Event | None) -> None:
        """Set a threading.Event to check for cancellation."""
        self._cancel_event = event

    def _check_cancelled(self) -> None:
        if self._cancel_event is not None and self._cancel_event.is_set():
            raise OllamaCancelledError("Request cancelled by user")

    def is_available(self) -> bool:
        try:
            available = requests.get(f"{self.base_url}/api/tags", timeout=3).ok
            logger.debug("Ollama availability check: %s", available)
            return available
        except requests.RequestException:
            logger.debug("Ollama not reachable at %s", self.base_url)
            return False

    def list_models(self) -> list[str]:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError(f"Cannot reach Ollama at {self.base_url}: {exc}") from exc
        return [m["name"] for m in resp.json().get("models", [])]

    def generate(self, prompt: str, system: str | None = None, json_mode: bool = False) -> str:
        self._check_cancelled()
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"
        try:
            logger.info("Ollama request: model=%s json_mode=%s", self.model, json_mode)
            resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=600)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Ollama request failed: %s", exc)
            raise OllamaError(
                f"Ollama request failed: {exc}. Is Ollama running at {self.base_url}? "
                f"Start it with 'ollama serve' and pull the model with 'ollama pull {self.model}'."
            ) from exc
        data = resp.json()
        text = data.get("response", "")
        done = data.get("done", False)
        if not done:
            logger.warning("Ollama response marked as not done")
        logger.debug("Ollama raw response (first 500 chars): %s", text[:500])

        text = clean_ai_text(text)
        # Strip reasoning blocks emitted by thinking models such as qwen3.
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
        return text.strip()

    def generate_json(self, prompt: str, system: str | None = None) -> dict:
        try:
            text = self.generate(
                prompt,
                system=system,
                json_mode=True
            )
        except OllamaError:
            logger.warning("JSON mode failed, retrying without format constraint")
            text = self.generate(
                prompt,
                system=system,
                json_mode=False
            )

        text = clean_ai_text(text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
            raise OllamaError("The model did not return valid JSON. Try again or switch models.")

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system: str | None = None,
        max_retries: int = 2,
    ) -> T:
        """Generate JSON and validate against a Pydantic model with retry."""
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                data = self.generate_json(prompt, system=system)
                return schema.model_validate(data)
            except (ValidationError, OllamaError) as exc:
                last_error = exc
                logger.warning(
                    "Validation attempt %d/%d failed: %s",
                    attempt + 1,
                    max_retries + 1,
                    exc,
                )
                if attempt < max_retries:
                    prompt = (
                        f"{prompt}\n\n"
                        f"Previous response was invalid: {exc}\n"
                        "Please return a valid JSON response matching the required schema."
                    )
        raise OllamaError(
            f"AI response validation failed after {max_retries + 1} attempts: {last_error}"
        )

    def pre_warm(self) -> bool:
        """Send a minimal prompt to load the model into VRAM."""
        try:
            self.generate("hello", system="Reply with one word.")
            logger.info("Model pre-warmed successfully")
            return True
        except OllamaError:
            logger.debug("Model pre-warm skipped (Ollama not reachable)")
            return False
