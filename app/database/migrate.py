"""Database migration manager.

Replaces the old ``init_db()`` / ``create_all()`` approach with proper
Alembic migrations.  Handles three scenarios:

1. **Fresh install** — database does not exist; ``upgrade("head")`` creates
   all tables from scratch.
2. **Pre-Alembic database** — exists, has tables, but no ``alembic_version``
   table.  The schema is already current (created by ``create_all()``), so we
   stamp at head to register the version without re-running migrations.
3. **Alembic-tracked database** — has ``alembic_version``.  We back up the
   database, run ``upgrade("head")``, and restore from backup on failure.
"""

import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.paths import BACKUP_DIR, DB_PATH

logger = logging.getLogger(__name__)

MAX_BACKUPS = 5


# ── Alembic config ──────────────────────────────────────────────────────────


def _get_alembic_config() -> Config:
    """Build an Alembic ``Config`` pointing at the project migrations."""
    project_root = Path(__file__).resolve().parent.parent.parent
    migrations_dir = project_root / "migrations"

    config = Config()
    config.set_main_option("script_location", str(migrations_dir))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{DB_PATH}")
    return config


# ── Database introspection ──────────────────────────────────────────────────


def _has_tables(db_path: Path) -> bool:
    """Return True if the SQLite database contains any tables."""
    if not db_path.exists():
        return False
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()
            return row is not None and row[0] > 0
        finally:
            conn.close()
    except sqlite3.DatabaseError:
        return False


def _has_alembic_version(db_path: Path) -> bool:
    """Return True if the database contains the ``alembic_version`` table."""
    if not db_path.exists():
        return False
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE type='table' AND name='alembic_version'"
            ).fetchone()
            return row is not None and row[0] > 0
        finally:
            conn.close()
    except sqlite3.DatabaseError:
        return False


# ── Backup / restore ────────────────────────────────────────────────────────


def _backup_database(db_path: Path) -> Path | None:
    """Copy the database to *BACKUP_DIR* and prune old copies.

    Returns the path of the new backup, or ``None`` if the source does not
    exist.
    """
    if not db_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"resume_optimizer_{timestamp}.db"

    shutil.copy2(db_path, backup_path)

    # Copy WAL / SHM sidecar files if present.
    for suffix in ("-wal", "-shm"):
        sidecar = db_path.with_name(db_path.name + suffix)
        if sidecar.exists():
            shutil.copy2(sidecar, backup_path.with_name(backup_path.name + suffix))

    logger.info("Backed up database to %s", backup_path)
    _prune_backups()
    return backup_path


def _prune_backups(keep: int = MAX_BACKUPS) -> None:
    """Delete the oldest backups, keeping at most *keep* copies."""
    backups = sorted(
        BACKUP_DIR.glob("resume_optimizer_*.db"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    for old in backups[keep:]:
        old.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm"):
            old.with_name(old.name + suffix).unlink(missing_ok=True)
        logger.debug("Pruned old backup %s", old)


def _restore_backup(backup_path: Path, db_path: Path) -> None:
    """Overwrite the database with *backup_path*."""
    shutil.copy2(backup_path, db_path)
    for suffix in ("-wal", "-shm"):
        src = backup_path.with_name(backup_path.name + suffix)
        dst = db_path.with_name(db_path.name + suffix)
        if src.exists():
            shutil.copy2(src, dst)
        elif dst.exists():
            dst.unlink()
    logger.info("Restored database from %s", backup_path)


# ── Public API ──────────────────────────────────────────────────────────────


def run_migrations() -> None:
    """Run Alembic migrations to bring the database to the latest schema.

    Called at application startup instead of the old ``create_all()`` path.
    """
    config = _get_alembic_config()

    # ── Scenario 1: fresh install ──────────────────────────────────────
    if not DB_PATH.exists() or not _has_tables(DB_PATH):
        if not DB_PATH.exists():
            logger.info("Fresh install — creating database with Alembic")
        else:
            logger.info("Database file exists but is empty — running migrations")
        command.upgrade(config, "head")
        logger.info("Database schema is up to date")
        return

    # ── Scenario 2: pre-Alembic database (created by create_all) ──────
    if not _has_alembic_version(DB_PATH):
        logger.info(
            "Pre-Alembic database detected (no alembic_version table) — "
            "stamping at head"
        )
        command.stamp(config, "head")
        logger.info("Database stamped at head revision")
        return

    # ── Scenario 3: Alembic-tracked database ──────────────────────────
    backup_path = _backup_database(DB_PATH)
    try:
        logger.info("Running Alembic migrations…")
        command.upgrade(config, "head")
        logger.info("Migrations completed successfully")
    except Exception:
        logger.exception("Migration failed")
        if backup_path is not None:
            logger.info("Restoring from backup %s", backup_path)
            _restore_backup(backup_path, DB_PATH)
        raise
