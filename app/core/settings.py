"""Typed application settings — replaces config_manager + config.json + settings.json.

Writes are atomic: tmp → flush → fsync → rename. A `.bak` copy of the
previous valid file is kept so that a corrupted live file can be recovered.
"""

import json
import logging
import os
import re
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from app.core.paths import CONFIG_PATH

logger = logging.getLogger(__name__)

_BAK_PATH = CONFIG_PATH.with_suffix(".json.bak")

_URL_RE = re.compile(r"^https?://\S+$")


class AISettings(BaseModel):
    ollama_url: str = "http://localhost:11434"
    model: str = Field(default="qwen3", min_length=1, max_length=200)
    available_models: list[str] = Field(default_factory=lambda: ["qwen3", "llama3.1"])
    temperature: float = Field(default=0.3, ge=0, le=1)
    custom_skills: list[str] = Field(default_factory=list)

    @field_validator("ollama_url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        v = v.strip()
        if not _URL_RE.match(v):
            raise ValueError("Must be a valid HTTP or HTTPS URL")
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Only http and https schemes are allowed")
        return v


class AppearanceSettings(BaseModel):
    theme: str = "dark"


class AppSettings(BaseModel):
    ai: AISettings = Field(default_factory=AISettings)
    appearance: AppearanceSettings = Field(default_factory=AppearanceSettings)


_DEFAULT = AppSettings()

_settings_lock = threading.Lock()


# ── Atomic write ────────────────────────────────────────────────────────────

_MAX_REPLACE_RETRIES = 3
_RETRY_DELAY = 0.01


def _atomic_write_json(path: Path, data: str) -> None:
    """Write *data* to *path* atomically.

    1. Write to a temporary file in the same directory.
    2. Flush and fsync to durable storage.
    3. Atomically replace the original via ``os.replace``.

    On Windows, ``os.replace`` may raise ``PermissionError`` if another
    handle is open, so we retry with exponential back-off.
    """
    dir_ = path.parent
    fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp", prefix=path.stem)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        _replace_with_retry(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _replace_with_retry(src: Path, dst: Path) -> None:
    """``os.replace`` with retries for Windows sharing violations."""
    last_err: OSError | None = None
    for attempt in range(_MAX_REPLACE_RETRIES):
        try:
            os.replace(src, dst)
            return
        except PermissionError as exc:
            last_err = exc
            import time
            time.sleep(_RETRY_DELAY * (2 ** attempt))
    raise last_err  # type: ignore[misc]


def _backup_settings() -> None:
    """Copy the current settings file to ``.bak`` if it exists."""
    if CONFIG_PATH.exists():
        try:
            shutil.copy2(CONFIG_PATH, _BAK_PATH)
        except OSError:
            logger.debug("Could not create settings backup", exc_info=True)


# ── Load / save ─────────────────────────────────────────────────────────────


def load_settings() -> AppSettings:
    """Load settings from disk, falling back to backup then defaults."""
    if not CONFIG_PATH.exists():
        logger.debug("Settings file not found — creating defaults")
        save_settings(_DEFAULT)
        return _DEFAULT.model_copy(deep=True)

    try:
        raw = CONFIG_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        settings = AppSettings.model_validate(data)
        logger.debug("Loaded settings from %s", CONFIG_PATH)
        return settings
    except json.JSONDecodeError as exc:
        logger.warning("Corrupted settings file (%s) — attempting recovery", exc)
        _quarantine_settings(f"Invalid JSON: {exc}")
        return _recover_settings(f"Invalid JSON: {exc}")
    except Exception as exc:
        logger.warning("Invalid settings (%s) — attempting recovery", exc)
        _quarantine_settings(str(exc))
        return _recover_settings(str(exc))


def _recover_settings(error_detail: str) -> AppSettings:
    """Try to recover from ``.bak``; fall back to defaults.

    Persists the recovered configuration to the live path so that
    subsequent loads don't fall back to defaults.
    """
    if _BAK_PATH.exists():
        try:
            raw = _BAK_PATH.read_text(encoding="utf-8")
            settings = AppSettings.model_validate(json.loads(raw))
            # Persist the recovered settings so next load uses them
            _atomic_write_json(
                CONFIG_PATH,
                settings.model_dump_json(indent=4),
            )
            logger.warning(
                "Recovered and restored settings from backup: %s", error_detail,
            )
            return settings
        except Exception:
            logger.warning("Backup also corrupted — falling back to defaults")

    # Persist defaults so the user can edit them in the UI
    defaults = _DEFAULT.model_copy(deep=True)
    _atomic_write_json(
        CONFIG_PATH,
        defaults.model_dump_json(indent=4),
    )
    logger.warning(
        "Settings lost. Using defaults. Reason: %s — "
        "your previous settings could not be recovered.", error_detail,
    )
    return defaults


def _quarantine_settings(error_detail: str) -> None:
    """Rename a broken settings file so it doesn't block future startups."""
    if not CONFIG_PATH.exists():
        return
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    quarantine_path = CONFIG_PATH.with_name(
        f"{CONFIG_PATH.stem}.{timestamp}.invalid.json"
    )
    try:
        CONFIG_PATH.rename(quarantine_path)
        logger.warning(
            "Moved broken settings to %s — reason: %s", quarantine_path, error_detail,
        )
    except OSError:
        logger.debug("Could not quarantine broken settings file", exc_info=True)


def save_settings(settings: AppSettings) -> None:
    """Atomically persist *settings*, keeping a ``.bak`` of the previous version."""
    with _settings_lock:
        _backup_settings()
        _atomic_write_json(CONFIG_PATH, settings.model_dump_json(indent=4))
        logger.debug("Saved settings to %s", CONFIG_PATH)


# ── Helpers ─────────────────────────────────────────────────────────────────


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


# ── SettingsService (single source of truth) ────────────────────────────────


class SettingsService:
    """In-process singleton that owns the current settings.

    All callers read from and write through this service so that every
    component in the application sees the same values.  After a
    :meth:`save` the :attr:`settings` property is updated **and** the
    :attr:`on_changed` callback is invoked so that UI widgets and
    background workers can react.
    """

    def __init__(self) -> None:
        self._settings = load_settings()
        self._on_changed_callbacks: list = []

    @property
    def settings(self) -> AppSettings:
        return self._settings.model_copy(deep=True)

    @property
    def theme(self) -> str:
        return self._settings.appearance.theme

    @property
    def model(self) -> str:
        return self._settings.ai.model

    @property
    def ollama_url(self) -> str:
        return self._settings.ai.ollama_url

    @property
    def temperature(self) -> float:
        return self._settings.ai.temperature

    def save(self, settings: AppSettings) -> None:
        """Persist *settings* to disk and notify all listeners."""
        save_settings(settings)
        self._settings = settings
        self._notify()

    def update(self, patch: dict) -> AppSettings:
        """Merge *patch* into current settings, save, and notify."""
        merged = self._settings.model_dump()
        _deep_merge(merged, patch)
        updated = AppSettings.model_validate(merged)
        self.save(updated)
        return updated

    def on_changed(self, callback) -> None:
        """Register *callback* to be called after every :meth:`save`."""
        self._on_changed_callbacks.append(callback)

    def _notify(self) -> None:
        for cb in self._on_changed_callbacks:
            try:
                cb(self._settings)
            except Exception:
                logger.debug("settings_changed callback error", exc_info=True)


# Module-level singleton — importable by any component.
settings_service = SettingsService()
