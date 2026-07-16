"""Typed application settings — replaces config_manager + config.json + settings.json."""
import json
import logging

from pydantic import BaseModel, Field

from app.core.paths import CONFIG_PATH

logger = logging.getLogger(__name__)


class AISettings(BaseModel):
    ollama_url: str = "http://localhost:11434"
    model: str = "qwen3"
    available_models: list[str] = Field(default_factory=lambda: ["qwen3", "llama3.1"])
    temperature: float = 0.3


class AppearanceSettings(BaseModel):
    theme: str = "dark"


class AppSettings(BaseModel):
    ai: AISettings = Field(default_factory=AISettings)
    appearance: AppearanceSettings = Field(default_factory=AppearanceSettings)


_DEFAULT = AppSettings()


def load_settings() -> AppSettings:
    if not CONFIG_PATH.exists():
        logger.debug("Settings file not found, creating default")
        save_settings(_DEFAULT)
        return _DEFAULT.model_copy()

    try:
        raw = CONFIG_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        settings = AppSettings.model_validate(data)
        logger.debug("Loaded settings from %s", CONFIG_PATH)
        return settings
    except Exception:
        logger.warning("Failed to load settings, using defaults")
        return _DEFAULT.model_copy()


def save_settings(settings: AppSettings) -> None:
    CONFIG_PATH.write_text(
        settings.model_dump_json(indent=4),
        encoding="utf-8",
    )
    logger.debug("Saved settings to %s", CONFIG_PATH)


def update_settings(patch: dict) -> AppSettings:
    settings = load_settings()
    merged = settings.model_dump()
    _deep_merge(merged, patch)
    updated = AppSettings.model_validate(merged)
    save_settings(updated)
    return updated


def _deep_merge(base: dict, patch: dict) -> None:
    for key, value in patch.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
