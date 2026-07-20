"""Backup & restore service — export/import database snapshots."""
from __future__ import annotations

import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from app.core.paths import DB_PATH, EXPORT_DIR

logger = logging.getLogger(__name__)


def backup_database(export_path: Path | None = None) -> Path:
    """Create a portable copy of the database.

    Parameters
    ----------
    export_path:
        Optional explicit destination. When *None* a timestamped file
        is created inside ``EXPORT_DIR``.

    Returns
    -------
    Path to the exported file.
    """
    if export_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = EXPORT_DIR / f"resume_optimizer_backup_{ts}.db"

    export_path.parent.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        raise FileNotFoundError("No database found to back up.")

    source_uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    with sqlite3.connect(source_uri, uri=True) as source:
        with sqlite3.connect(export_path) as dest:
            source.backup(dest)
            integrity = dest.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise RuntimeError("Backup integrity check failed.")

    logger.info("Backup created at %s", export_path)
    return export_path


def restore_database(source_path: Path) -> None:
    """Replace the current database with *source_path*.

    The current database is backed up first. Raises if the source
    fails an integrity check.
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Backup file not found: {source_path}")

    integrity = _check_integrity(source_path)
    if not integrity:
        raise RuntimeError("Source backup failed integrity check.")

    pre_restore = DB_PATH.with_suffix(".pre_restore.db")
    if DB_PATH.exists():
        shutil.copy2(DB_PATH, pre_restore)

    shutil.copy2(source_path, DB_PATH)
    logger.info("Database restored from %s", source_path)


def list_backups() -> list[Path]:
    """Return exported backup files sorted newest-first."""
    if not EXPORT_DIR.exists():
        return []
    backups = sorted(
        EXPORT_DIR.glob("resume_optimizer_backup_*.db"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return backups


def _check_integrity(path: Path) -> bool:
    """Return True if the SQLite file passes PRAGMA integrity_check."""
    try:
        conn = sqlite3.connect(path)
        result = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        return bool(result and result[0] == "ok")
    except Exception:
        logger.exception("Integrity check failed for %s", path)
        return False
