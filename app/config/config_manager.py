"""Configuration manager for Resume Optimizer."""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_FILE = Path(__file__).parent / "config.json"

DEFAULT_CONFIG = {
    "theme": "light",
    "ollama_url": "http://localhost:11434",
    "model": "qwen3",
    "available_models": ["qwen3", "llama3.1"],
    "temperature": 0.3,
}


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        logger.debug("Config file not found, creating default")
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        config = DEFAULT_CONFIG.copy()
        config.update(data)
        logger.debug("Loaded config from %s", CONFIG_FILE)
        return config
    except Exception:
        logger.warning("Failed to load config, using defaults")
        return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    logger.debug("Saved config to %s", CONFIG_FILE)


def update_config(key: str, value: object) -> None:
    config = load_config()
    config[key] = value
    save_config(config)
