"""Thin client for the local Ollama HTTP API."""
import json
import re

import requests

from app import config

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


class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        cfg = config.load_config()
        self.base_url = (base_url or cfg["ollama_url"]).rstrip("/")
        self.model = model or cfg["model"]
        self.temperature = float(cfg.get("temperature", 0.3))

    def is_available(self) -> bool:
        try:
            return requests.get(f"{self.base_url}/api/tags", timeout=3).ok
        except requests.RequestException:
            return False

    def list_models(self) -> list[str]:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError(f"Cannot reach Ollama at {self.base_url}: {exc}") from exc
        return [m["name"] for m in resp.json().get("models", [])]

    def generate(self, prompt: str, system: str | None = None, json_mode: bool = False) -> str:
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
            resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=600)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError(
                f"Ollama request failed: {exc}. Is Ollama running at {self.base_url}? "
                f"Start it with 'ollama serve' and pull the model with 'ollama pull {self.model}'."
            ) from exc
        text = resp.json().get("response", "")

        text = clean_ai_text(text)
        # Strip reasoning blocks emitted by thinking models such as qwen3.
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
        return text.strip()

    def generate_json(self, prompt: str, system: str | None = None) -> dict:
        text = self.generate(
            prompt,
            system=system,
            json_mode=True
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
