"""Application configuration stored in the user's home directory."""
import json
from pathlib import Path

APP_DIR = Path.home() / ".resume_optimizer"
CONFIG_PATH = APP_DIR / "config.json"
DB_PATH = APP_DIR / "resume_optimizer.db"

DEFAULTS = {
    "ollama_url": "http://localhost:11434",
    "model": "qwen3",
    "available_models": ["qwen3", "llama3.1"],
    "temperature": 0.3,
}


def load_config() -> dict:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
