"""Config package — backward-compatible re-exports.

New code should import from:
  - app.core.settings
  - app.core.paths
"""
from app.core.paths import DB_PATH, USER_DATA_DIR
from app.core.settings import (
    AISettings,
    AppearanceSettings,
    AppSettings,
    load_settings,
    save_settings,
    update_settings,
)
from typing import Literal

# Legacy re-exports for backward compatibility
DEFAULT_CONFIG = {
    "theme": "dark",
    "ollama_url": "http://localhost:11434",
    "model": "qwen3",
    "available_models": ["qwen3", "llama3.1"],
    "temperature": 0.3,
}


def load_config() -> dict:
    """Load settings as a flat dict for backward compatibility."""
    settings = load_settings()
    return {
        "theme": settings.appearance.theme,
        "ollama_url": settings.ai.ollama_url,
        "model": settings.ai.model,
        "available_models": settings.ai.available_models,
        "temperature": settings.ai.temperature,
    }


def save_config(config: dict) -> None:
    """Save a flat dict to typed settings for backward compatibility."""
    theme_value = config.get("theme", DEFAULT_CONFIG["theme"])
    theme: Literal["dark", "light", "system"] = (
        theme_value if theme_value in ("dark", "light", "system") else "dark"
    )
    settings = AppSettings(
        ai=AISettings(
            ollama_url=str(config.get("ollama_url", DEFAULT_CONFIG["ollama_url"])),
            model=str(config.get("model", DEFAULT_CONFIG["model"])),
            available_models=list(config.get("available_models", DEFAULT_CONFIG["available_models"])),
            temperature=float(config.get("temperature", DEFAULT_CONFIG["temperature"])),
        ),
        appearance=AppearanceSettings(theme=theme),
    )
    save_settings(settings)


__all__ = [
    "DB_PATH",
    "USER_DATA_DIR",
    "AppSettings",
    "load_settings",
    "save_settings",
    "update_settings",
    "DEFAULT_CONFIG",
    "load_config",
    "save_config",
]
