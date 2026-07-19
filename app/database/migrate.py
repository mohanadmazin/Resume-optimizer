"""Database migration manager.

Replaces the old ``init_db()`` / ``create_all()`` approach with proper
Alembic migrations.  Handles three scenarios:

1. **Fresh install** — database does not exist; ``upgrade("head")`` creates
   all tables from scratch.
2. **Pre-Alembic database** — exists, has tables, but no ``alembic_version``
   table.  We infer the actual schema revision, stamp there, then upgrade.
3. **Alembic-tracked database** — has ``alembic_version``.  We back up the
   database, run ``upgrade("head")``, and restore from backup on failure.
"""

import logging
import shutil
import sqlite3
from datetime import datetime
from enum import Enum
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.paths import BACKUP_DIR, DB_PATH

logger = logging.getLogger(__name__)

MAX_BACKUPS = 5


# ── Alembic config ──────────────────────────────────────────────────────────


def _get_alembic_config(db_path: Path = DB_PATH) -> Config:
    """Build an Alembic ``Config`` pointing at the project migrations."""
    project_root = Path(__file__).resolve().parent.parent.parent
    migrations_dir = project_root / "migrations"

    config = Config()
    config.set_main_option("script_location", str(migrations_dir))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


# ── Database introspection ──────────────────────────────────────────────────


class DatabaseState(Enum):
    MISSING = "missing"
    EMPTY = "empty"
    VALID = "valid"
    CORRUPT = "corrupt"


def inspect_database(db_path: Path) -> DatabaseState:
    if not db_path.exists():
        return DatabaseState.MISSING
    try:
        with sqlite3.connect(db_path) as connection:
            integrity = connection.execute("PRAGMA quick_check").fetchone()
            if not integrity or integrity[0] != "ok":
                return DatabaseState.CORRUPT
            count = connection.execute(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchone()[0]
            return DatabaseState.VALID if count else DatabaseState.EMPTY
    except sqlite3.DatabaseError:
        return DatabaseState.CORRUPT


def _has_tables(db_path: Path) -> bool:
    """Return True if the SQLite database contains any tables."""
    return inspect_database(db_path) == DatabaseState.VALID


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


def _table_columns(db_path: Path, table: str) -> set[str]:
    """Return the set of column names for *table*."""
    if table not in _INTROSPECTABLE_TABLES:
        raise ValueError(f"Table {table!r} is not in the introspectable tables whitelist")
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()  # noqa: S608
    finally:
        conn.close()
    return {row[1] for row in rows}


def _has_cascade_fk(
    db_path: Path,
    table: str,
    referenced_table: str,
) -> bool:
    """Check whether *table* has an ON DELETE CASCADE FK to *referenced_table*."""
    if table not in _INTROSPECTABLE_TABLES or referenced_table not in _INTROSPECTABLE_TABLES:
        raise ValueError(
            f"Tables must be in the whitelist: {table!r}, {referenced_table!r}"
        )
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()  # noqa: S608
    finally:
        conn.close()
    # PRAGMA foreign_key_list columns: id, seq, table, from, to, on_update, on_delete, match
    return any(
        row[2] == referenced_table and row[6].upper() == "CASCADE"
        for row in rows
    )


_TRACKING_COLUMNS = {
    "source_type",
    "source_filename",
    "source_hash",
    "is_original",
}

# Whitelist of tables that may be introspected by PRAGMA queries.
# PRAGMAs do not support parameterized queries, so we validate against this set.
_INTROSPECTABLE_TABLES = frozenset({"resumes", "analyses", "optimizations"})


def _infer_legacy_revision(db_path: Path) -> str:
    """Infer the Alembic revision that matches the current schema.

    Returns:
        "0001" if tracking columns are missing.
        "0002" if tracking columns exist but cascade FKs are missing.
        "head" if the schema is already fully current.
    """
    columns = _table_columns(db_path, "resumes")

    if not _TRACKING_COLUMNS.issubset(columns):
        return "0001"

    analyses_cascade = _has_cascade_fk(db_path, "analyses", "resumes")
    optimizations_cascade = _has_cascade_fk(db_path, "optimizations", "resumes")

    if analyses_cascade and optimizations_cascade:
        return "head"

    return "0002"


# ── Backup / restore ────────────────────────────────────────────────────────


def _backup_database(db_path: Path) -> Path | None:
    """Create a transactionally consistent backup using SQLite's online backup API.

    Returns the path of the new backup, or ``None`` if the source does not
    exist.
    """
    if not db_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = BACKUP_DIR / f"resume_optimizer_{timestamp}.db"
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    source_uri = f"file:{db_path.as_posix()}?mode=ro"

    with sqlite3.connect(source_uri, uri=True) as source:
        with sqlite3.connect(backup_path) as destination:
            source.backup(destination)

            integrity = destination.execute(
                "PRAGMA integrity_check"
            ).fetchone()

            if not integrity or integrity[0] != "ok":
                raise RuntimeError(
                    "SQLite backup failed integrity verification."
                )

    logger.info("Created consistent database backup at %s", backup_path)
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
        logger.debug("Pruned old backup %s", old)


def _restore_backup(backup_path: Path, db_path: Path) -> None:
    """Overwrite the database with *backup_path* using SQLite backup API."""
    with sqlite3.connect(backup_path) as source:
        with sqlite3.connect(db_path) as destination:
            source.backup(destination)
    logger.info("Restored database from %s", backup_path)


# ── Public API ──────────────────────────────────────────────────────────────


def run_migrations() -> None:
    """Run Alembic migrations to bring the database to the latest schema.

    Called at application startup instead of the old ``create_all()`` path.
    """
    config = _get_alembic_config(DB_PATH)
    state = inspect_database(DB_PATH)

    if state == DatabaseState.CORRUPT:
        quarantine = DB_PATH.with_suffix(
            f".corrupt-{datetime.now():%Y%m%d-%H%M%S-%f}.db"
        )
        shutil.copy2(DB_PATH, quarantine)
        raise RuntimeError(
            "Database integrity check failed. "
            f"A copy was preserved at {quarantine}."
        )

    # ── Scenario 1: fresh install ──────────────────────────────────────
    if state in (DatabaseState.MISSING, DatabaseState.EMPTY):
        if state == DatabaseState.MISSING:
            logger.info("Fresh install — creating database with Alembic")
        else:
            logger.info("Database file exists but is empty — running migrations")
        command.upgrade(config, "head")
        logger.info("Database schema is up to date")
        return

    # ── Scenario 2: pre-Alembic database (no alembic_version) ─────────
    if not _has_alembic_version(DB_PATH):
        legacy_revision = _infer_legacy_revision(DB_PATH)
        logger.info(
            "Pre-Alembic database detected — inferred revision: %s",
            legacy_revision,
        )

        backup_path = _backup_database(DB_PATH)
        try:
            command.stamp(config, legacy_revision)
            if legacy_revision != "head":
                command.upgrade(config, "head")
            logger.info("Migrations completed successfully")
        except Exception:
            logger.exception("Migration failed during legacy upgrade")
            if backup_path is not None:
                logger.info("Restoring from backup %s", backup_path)
                _restore_backup(backup_path, DB_PATH)
            raise
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
