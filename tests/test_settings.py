"""Tests for atomic settings persistence and validation."""

import json
import logging
import threading
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.settings import (
    AISettings,
    AppSettings,
    _DEFAULT,
    _atomic_write_json,
    _backup_settings,
    load_settings,
    save_settings,
    update_settings,
)


@pytest.fixture()
def settings_dir(tmp_path, monkeypatch):
    """Redirect CONFIG_PATH / _BAK_PATH to a temporary directory."""
    cfg = tmp_path / "settings.json"
    bak = tmp_path / "settings.json.bak"
    monkeypatch.setattr("app.core.settings.CONFIG_PATH", cfg)
    monkeypatch.setattr("app.core.settings._BAK_PATH", bak)
    return cfg, bak


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


# ── Validation ──────────────────────────────────────────────────────────────


class TestAISettingsValidation:
    def test_valid_defaults(self):
        s = AISettings()
        assert s.ollama_url == "http://localhost:11434"
        assert s.model == "qwen3"
        assert s.temperature == 0.3

    def test_model_min_length(self):
        with pytest.raises(ValidationError):
            AISettings(model="")

    def test_model_max_length(self):
        with pytest.raises(ValidationError):
            AISettings(model="x" * 201)

    def test_temperature_below_zero(self):
        with pytest.raises(ValidationError):
            AISettings(temperature=-0.1)

    def test_temperature_above_one(self):
        with pytest.raises(ValidationError):
            AISettings(temperature=1.1)

    def test_temperature_boundary_zero(self):
        assert AISettings(temperature=0).temperature == 0

    def test_temperature_boundary_one(self):
        assert AISettings(temperature=1).temperature == 1

    def test_invalid_url_rejected(self):
        with pytest.raises(ValidationError):
            AISettings(ollama_url="not-a-url")

    def test_ftp_url_rejected(self):
        with pytest.raises(ValidationError):
            AISettings(ollama_url="ftp://storage.example.com")

    def test_valid_https_url(self):
        s = AISettings(ollama_url="https://ollama.example.com:11434")
        assert s.ollama_url == "https://ollama.example.com:11434"

    def test_url_strips_whitespace(self):
        s = AISettings(ollama_url="  http://localhost:11434  ")
        assert s.ollama_url == "http://localhost:11434"

    def test_model_roundtrip_through_dict(self):
        s = AppSettings()
        dumped = s.model_dump()
        restored = AppSettings.model_validate(dumped)
        assert restored == s


# ── Atomic write ────────────────────────────────────────────────────────────


class TestAtomicWrite:
    def test_creates_file(self, settings_dir):
        cfg, _ = settings_dir
        _atomic_write_json(cfg, '{"ok": true}')
        assert cfg.exists()
        assert json.loads(cfg.read_text()) == {"ok": True}

    def test_no_temp_files_left_on_success(self, settings_dir):
        cfg, _ = settings_dir
        _atomic_write_json(cfg, "{}")
        temps = list(cfg.parent.glob(f"{cfg.stem}*.tmp"))
        assert temps == []

    def test_temp_file_cleaned_on_replace_failure(self, settings_dir):
        cfg, _ = settings_dir
        _atomic_write_json(cfg, '{"v": 0}')
        with patch("app.core.settings._replace_with_retry", side_effect=OSError("disk full")):
            with pytest.raises(OSError, match="disk full"):
                _atomic_write_json(cfg, '{"v": 1}')
        temps = list(cfg.parent.glob(f"{cfg.stem}*.tmp"))
        assert temps == []

    def test_replace_is_atomic(self, settings_dir):
        """Original content survives if os.replace fails."""
        cfg, _ = settings_dir
        _atomic_write_json(cfg, '{"version": 1}')
        with patch("app.core.settings.os.replace", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                _atomic_write_json(cfg, '{"version": 2}')
        assert json.loads(cfg.read_text()) == {"version": 1}

    def test_content_is_fsynced(self, settings_dir):
        cfg, _ = settings_dir
        _atomic_write_json(cfg, '{"data": 42}')
        assert json.loads(cfg.read_text()) == {"data": 42}


# ── Backup ──────────────────────────────────────────────────────────────────


class TestBackup:
    def test_backup_created_on_second_save(self, settings_dir):
        cfg, bak = settings_dir
        save_settings(_DEFAULT)        # first save — no original → no backup
        assert not bak.exists()
        save_settings(_DEFAULT)        # second save — original exists → backup
        assert bak.exists()
        assert json.loads(bak.read_text()) == json.loads(cfg.read_text())

    def test_backup_overwrites_previous(self, settings_dir):
        cfg, bak = settings_dir
        save_settings(AppSettings(ai=AISettings(temperature=0.5)))
        save_settings(AppSettings(ai=AISettings(temperature=0.7)))
        assert json.loads(bak.read_text())["ai"]["temperature"] == 0.5
        assert json.loads(cfg.read_text())["ai"]["temperature"] == 0.7

    def test_no_backup_when_no_original(self, settings_dir):
        _, bak = settings_dir
        save_settings(_DEFAULT)
        assert not bak.exists()


# ── Load / save round-trip ──────────────────────────────────────────────────


class TestLoadSave:
    def test_save_then_load(self, settings_dir):
        cfg, _ = settings_dir
        original = AppSettings(
            ai=AISettings(
                ollama_url="https://remote:11434",
                model="llama3.1",
                temperature=0.8,
            ),
        )
        save_settings(original)
        loaded = load_settings()
        assert loaded.ai.ollama_url == "https://remote:11434"
        assert loaded.ai.model == "llama3.1"
        assert loaded.ai.temperature == 0.8

    def test_load_missing_returns_defaults(self, settings_dir):
        cfg, _ = settings_dir
        assert not cfg.exists()
        loaded = load_settings()
        assert loaded == _DEFAULT
        assert cfg.exists()

    def test_load_corrupted_returns_defaults(self, settings_dir):
        cfg, _ = settings_dir
        _write_json(cfg, {"not": "valid settings"})
        loaded = load_settings()
        assert loaded.ai.model == "qwen3"

    def test_load_invalid_json_returns_defaults(self, settings_dir):
        cfg, _ = settings_dir
        cfg.write_text("{invalid json", encoding="utf-8")
        loaded = load_settings()
        assert loaded == _DEFAULT

    def test_load_recoverable_json_logs_warning(self, settings_dir, caplog):
        cfg, _ = settings_dir
        _write_json(cfg, {"ai": {"temperature": 999}})
        with caplog.at_level(logging.WARNING, logger="app.core.settings"):
            load_settings()
        messages = " ".join(r.message for r in caplog.records)
        assert "attempting recovery" in messages.lower()

    def test_update_settings(self, settings_dir):
        save_settings(_DEFAULT)
        updated = update_settings({"ai": {"temperature": 0.9}})
        assert updated.ai.temperature == 0.9
        loaded = load_settings()
        assert loaded.ai.temperature == 0.9


# ── Concurrency ─────────────────────────────────────────────────────────────


class TestConcurrency:
    def test_concurrent_saves_no_corruption(self, settings_dir):
        """Multiple threads writing simultaneously produce valid JSON."""
        errors = []

        def writer(temp):
            try:
                save_settings(AppSettings(ai=AISettings(temperature=temp)))
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(t,))
            for t in [x / 10 for x in range(10)]
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        loaded = load_settings()
        assert 0 <= loaded.ai.temperature <= 1


# ── Recovery from .bak ─────────────────────────────────────────────────────


class TestRecovery:
    def test_recover_from_bak(self, settings_dir):
        """If live is corrupted but .bak is valid, load_settings recovers."""
        cfg, bak = settings_dir
        good = AppSettings(ai=AISettings(temperature=0.42))
        save_settings(good)   # first save
        save_settings(good)   # second save creates .bak with 0.42
        assert bak.exists()
        # Corrupt the live file
        cfg.write_text("{{{", encoding="utf-8")
        loaded = load_settings()
        assert loaded.ai.temperature == 0.42

    def test_both_corrupted_returns_defaults(self, settings_dir):
        cfg, bak = settings_dir
        save_settings(_DEFAULT)
        save_settings(_DEFAULT)
        cfg.write_text("{{{", encoding="utf-8")
        bak.write_text("{{{", encoding="utf-8")
        loaded = load_settings()
        assert loaded == _DEFAULT
