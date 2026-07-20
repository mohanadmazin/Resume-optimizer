"""Tests for backup & restore service."""
from __future__ import annotations

import sqlite3

import pytest

from app.core.paths import DB_PATH, EXPORT_DIR


@pytest.fixture(autouse=True)
def _ensure_db_exists():
    """Create a minimal DB if none exists for testing."""
    if not DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        conn.execute("CREATE TABLE IF NOT EXISTS _test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
    yield


class TestBackup:
    def test_backup_creates_file(self):
        from app.infrastructure.backup import backup_database

        result = backup_database()
        assert result.exists()
        assert result.suffix == ".db"
        assert result.parent == EXPORT_DIR

    def test_backup_integrity(self):
        from app.infrastructure.backup import backup_database

        result = backup_database()
        conn = sqlite3.connect(result)
        check = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        assert check[0] == "ok"

    def test_backup_custom_path(self, tmp_path):
        from app.infrastructure.backup import backup_database

        dest = tmp_path / "custom_backup.db"
        result = backup_database(export_path=dest)
        assert result == dest
        assert dest.exists()

    def test_backup_no_db_raises(self, tmp_path, monkeypatch):
        from app.infrastructure import backup as mod

        monkeypatch.setattr(mod, "DB_PATH", tmp_path / "nonexistent.db")
        with pytest.raises(FileNotFoundError, match="No database found"):
            mod.backup_database()


class TestRestore:
    def test_restore_replaces_database(self, tmp_path):
        from app.infrastructure.backup import backup_database, restore_database

        backup_path = backup_database()
        restore_database(backup_path)
        assert DB_PATH.exists()

    def test_restore_nonexistent_raises(self, tmp_path):
        from app.infrastructure.backup import restore_database

        with pytest.raises(FileNotFoundError, match="Backup file not found"):
            restore_database(tmp_path / "nope.db")

    def test_restore_corrupt_raises(self, tmp_path):
        from app.infrastructure.backup import restore_database

        corrupt = tmp_path / "corrupt.db"
        corrupt.write_bytes(b"not a database")
        with pytest.raises(RuntimeError, match="integrity check"):
            restore_database(corrupt)


class TestListBackups:
    def test_list_backups_empty(self, tmp_path, monkeypatch):
        from app.infrastructure import backup as mod

        empty = tmp_path / "empty_exports"
        empty.mkdir()
        monkeypatch.setattr(mod, "EXPORT_DIR", empty)
        assert mod.list_backups() == []

    def test_list_backups_sorted(self, tmp_path, monkeypatch):
        from app.infrastructure import backup as mod

        export_dir = tmp_path / "exports"
        export_dir.mkdir()
        monkeypatch.setattr(mod, "EXPORT_DIR", export_dir)

        for i in range(3):
            f = export_dir / f"resume_optimizer_backup_{i}.db"
            f.write_bytes(b"data")
            # Stagger mtimes
            import time
            time.sleep(0.01)

        backups = mod.list_backups()
        assert len(backups) == 3
        # Newest first
        assert backups[0].stat().st_mtime >= backups[-1].stat().st_mtime
