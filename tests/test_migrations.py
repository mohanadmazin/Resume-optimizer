"""Tests for the Alembic migration manager.

Each test uses a temporary database so the real user database is never touched.
"""

import sqlite3
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from app.database.migrate import (
    _backup_database,
    _has_alembic_version,
    _has_tables,
    _prune_backups,
    _restore_backup,
    run_migrations,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _alembic_config(db_path: Path) -> Config:
    """Build an Alembic Config pointing at *db_path*."""
    project_root = Path(__file__).resolve().parent.parent
    migrations_dir = project_root / "migrations"
    config = Config()
    config.set_main_option("script_location", str(migrations_dir))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def _create_schema_0001(db_path: Path) -> None:
    """Create the database with only the migration-0001 schema (no tracking columns)."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        textwrap.dedent("""\
            CREATE TABLE resumes (
                id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                data_json TEXT NOT NULL,
                raw_text TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE job_descriptions (
                id INTEGER PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE analyses (
                id INTEGER PRIMARY KEY,
                resume_id INTEGER NOT NULL REFERENCES resumes(id),
                job_id INTEGER NOT NULL REFERENCES job_descriptions(id),
                ats_score INTEGER NOT NULL,
                keyword_match FLOAT DEFAULT 0.0,
                skills_match FLOAT DEFAULT 0.0,
                missing_keywords TEXT DEFAULT '[]',
                suggestions TEXT DEFAULT '[]',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE optimizations (
                id INTEGER PRIMARY KEY,
                resume_id INTEGER NOT NULL REFERENCES resumes(id),
                job_id INTEGER NOT NULL REFERENCES job_descriptions(id),
                model VARCHAR(100) DEFAULT '',
                optimized_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
    )
    conn.close()


def _create_schema_full(db_path: Path) -> None:
    """Create the database with the full schema (all columns, like create_all)."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        textwrap.dedent("""\
            CREATE TABLE resumes (
                id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                data_json TEXT NOT NULL,
                raw_text TEXT DEFAULT '',
                source_type VARCHAR(50) DEFAULT 'import',
                source_filename VARCHAR(500) DEFAULT '',
                source_hash VARCHAR(64) DEFAULT '',
                is_original BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE job_descriptions (
                id INTEGER PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE analyses (
                id INTEGER PRIMARY KEY,
                resume_id INTEGER NOT NULL REFERENCES resumes(id),
                job_id INTEGER NOT NULL REFERENCES job_descriptions(id),
                ats_score INTEGER NOT NULL,
                keyword_match FLOAT DEFAULT 0.0,
                skills_match FLOAT DEFAULT 0.0,
                missing_keywords TEXT DEFAULT '[]',
                suggestions TEXT DEFAULT '[]',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE optimizations (
                id INTEGER PRIMARY KEY,
                resume_id INTEGER NOT NULL REFERENCES resumes(id),
                job_id INTEGER NOT NULL REFERENCES job_descriptions(id),
                model VARCHAR(100) DEFAULT '',
                optimized_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
    )
    conn.close()


def _get_columns(db_path: Path, table: str) -> list[str]:
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()  # noqa: S608
    conn.close()
    return [row[1] for row in rows]


def _get_version(db_path: Path) -> str | None:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        return row[0] if row else None
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()


def _test_engine(db_path: Path):
    """Create a SQLAlchemy engine for *db_path* with the same PRAGMAs as the real engine."""
    from sqlalchemy import event as sa_event, create_engine as _create_engine

    eng = _create_engine(f"sqlite:///{db_path}", echo=False)

    @sa_event.listens_for(eng, "connect")
    def _pragmas(dbapi_conn, _rec):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()

    return eng


# ── Unit tests for helpers ──────────────────────────────────────────────────


def test_has_tables_returns_false_for_missing(tmp_path):
    assert _has_tables(tmp_path / "nope.db") is False


def test_has_tables_returns_false_for_empty_file(tmp_path):
    db = tmp_path / "empty.db"
    db.touch()
    assert _has_tables(db) is False


def test_has_tables_returns_true(tmp_path):
    db = tmp_path / "real.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    conn.close()
    assert _has_tables(db) is True


def test_has_alembic_version_returns_false_for_missing(tmp_path):
    assert _has_alembic_version(tmp_path / "nope.db") is False


def test_has_alembic_version_returns_false_without_table(tmp_path):
    db = tmp_path / "noalembic.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    conn.close()
    assert _has_alembic_version(db) is False


def test_has_alembic_version_returns_true(tmp_path):
    db = tmp_path / "versioned.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32))")
    conn.execute("INSERT INTO alembic_version VALUES ('0001')")
    conn.close()
    assert _has_alembic_version(db) is True


# ── Backup / restore tests ─────────────────────────────────────────────────


def test_backup_creates_copy(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE t (id INTEGER)")
    conn.close()

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("app.database.migrate.BACKUP_DIR", backup_dir)

    backup_path = _backup_database(db)
    assert backup_path is not None
    assert backup_path.exists()

    # Verify the backup is a valid SQLite database
    conn = sqlite3.connect(str(backup_path))
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    conn.close()
    assert "t" in tables


def test_backup_returns_none_for_missing(tmp_path, monkeypatch):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("app.database.migrate.BACKUP_DIR", backup_dir)

    assert _backup_database(tmp_path / "nope.db") is None


def test_prune_keeps_most_recent(tmp_path, monkeypatch):
    import os

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("app.database.migrate.BACKUP_DIR", backup_dir)

    # Create 7 fake backups with distinct modification times
    for i in range(7):
        p = backup_dir / f"resume_optimizer_{i:04d}.db"
        p.write_text(f"data_{i}")
        os.utime(p, (1000 + i, 1000 + i))

    _prune_backups(keep=5)

    remaining = sorted(backup_dir.glob("resume_optimizer_*.db"))
    assert len(remaining) == 5
    # The oldest two (0000, 0001) should be gone
    assert not (backup_dir / "resume_optimizer_0000.db").exists()
    assert not (backup_dir / "resume_optimizer_0001.db").exists()


def test_restore_overwrites_database(tmp_path):
    original = tmp_path / "original.db"
    backup = tmp_path / "backup.db"

    # Original has one table
    conn = sqlite3.connect(str(original))
    conn.execute("CREATE TABLE old_table (id INTEGER)")
    conn.close()

    # Backup has a different table
    conn = sqlite3.connect(str(backup))
    conn.execute("CREATE TABLE new_table (id INTEGER)")
    conn.close()

    _restore_backup(backup, original)

    conn = sqlite3.connect(str(original))
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    conn.close()
    assert "new_table" in tables
    assert "old_table" not in tables


# ── Scenario 1: Fresh install ───────────────────────────────────────────────


def test_fresh_install_creates_all_tables(tmp_path, monkeypatch):
    db = tmp_path / "fresh.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)

    run_migrations()

    columns = _get_columns(db, "resumes")
    assert "source_type" in columns
    assert "source_filename" in columns
    assert "source_hash" in columns
    assert "is_original" in columns

    assert _get_version(db) == "0004"


# ── Scenario 2: Pre-Alembic database (create_all schema) ───────────────────


def test_pre_alembic_full_schema_stamps_head(tmp_path, monkeypatch):
    db = tmp_path / "pre_alembic.db"
    _create_schema_full(db)

    monkeypatch.setattr("app.database.migrate.DB_PATH", db)

    assert _has_tables(db) is True
    assert _has_alembic_version(db) is False

    run_migrations()

    # Should be stamped at head without running any migrations
    assert _get_version(db) == "0004"
    # Columns should still be present
    columns = _get_columns(db, "resumes")
    assert "source_type" in columns


# ── Scenario 3: Database at migration 0001 (missing tracking columns) ──────


def test_database_at_0001_gets_0002_applied(tmp_path, monkeypatch):
    db = tmp_path / "at_0001.db"
    _create_schema_0001(db)

    # Stamp at 0001
    config = _alembic_config(db)
    command.stamp(config, "0001")
    assert _get_version(db) == "0001"

    monkeypatch.setattr("app.database.migrate.DB_PATH", db)

    run_migrations()

    assert _get_version(db) == "0004"
    columns = _get_columns(db, "resumes")
    assert "source_type" in columns
    assert "source_filename" in columns
    assert "source_hash" in columns
    assert "is_original" in columns


# ── Scenario 4: create_all schema + Alembic at 0001 (idempotent 0002) ──────


def test_idempotent_0002_on_create_all_schema(tmp_path, monkeypatch):
    db = tmp_path / "drift.db"
    _create_schema_full(db)

    # Stamp at 0001 even though the schema has all columns
    config = _alembic_config(db)
    command.stamp(config, "0001")
    assert _get_version(db) == "0001"

    monkeypatch.setattr("app.database.migrate.DB_PATH", db)

    # Should NOT fail — 0002 checks for column existence
    run_migrations()

    assert _get_version(db) == "0004"
    columns = _get_columns(db, "resumes")
    assert "source_type" in columns


# ── Recovery on migration failure ───────────────────────────────────────────


def test_backup_restored_on_failure(tmp_path, monkeypatch):
    db = tmp_path / "will_fail.db"
    _create_schema_0001(db)

    # Stamp at 0001
    config = _alembic_config(db)
    command.stamp(config, "0001")

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    monkeypatch.setattr("app.database.migrate.BACKUP_DIR", backup_dir)

    # Patch alembic command.upgrade to raise on the second call (0002)
    original_upgrade = command.upgrade

    call_count = 0

    def _failing_upgrade(cfg, rev):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call is upgrade("head") — let it inspect, then fail
            raise RuntimeError("Simulated migration failure")
        return original_upgrade(cfg, rev)

    with patch("app.database.migrate.command.upgrade", side_effect=_failing_upgrade):
        with pytest.raises(RuntimeError, match="Simulated migration failure"):
            run_migrations()

    # Database should have been restored from backup
    assert _has_alembic_version(db) is True
    assert _get_version(db) == "0001"


# ── Already at head ─────────────────────────────────────────────────────────


def test_already_at_head_no_op(tmp_path, monkeypatch):
    db = tmp_path / "current.db"
    _create_schema_full(db)

    config = _alembic_config(db)
    command.stamp(config, "head")
    assert _get_version(db) == "0004"

    monkeypatch.setattr("app.database.migrate.DB_PATH", db)

    # Should succeed without error — upgrade("head") on an up-to-date DB is a no-op
    run_migrations()
    assert _get_version(db) == "0004"


# ── User data preserved through migration ───────────────────────────────────


def test_data_preserved_through_0001_to_0002(tmp_path, monkeypatch):
    db = tmp_path / "with_data.db"
    _create_schema_0001(db)

    # Insert a resume row
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO resumes (name, data_json) VALUES (?, ?)",
        ("Test Resume", "{}"),
    )
    conn.commit()
    conn.close()

    # Stamp at 0001
    config = _alembic_config(db)
    command.stamp(config, "0001")

    monkeypatch.setattr("app.database.migrate.DB_PATH", db)

    run_migrations()

    # Data should still be there
    conn = sqlite3.connect(str(db))
    row = conn.execute("SELECT name, data_json FROM resumes").fetchone()
    conn.close()
    assert row == ("Test Resume", "{}")


# ── PRAGMA foreign_keys = ON ────────────────────────────────────────────────


def test_foreign_keys_enabled_on_connect(tmp_path, monkeypatch):
    """The engine PRAGMA listener must enable foreign_keys for every connection."""
    db = tmp_path / "pragma.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    run_migrations()

    eng = _test_engine(db)
    with eng.connect() as conn:
        row = conn.execute(sa.text("PRAGMA foreign_keys")).fetchone()
        assert row[0] == 1  # 1 = ON


def test_wal_mode_enabled(tmp_path, monkeypatch):
    """The engine PRAGMA listener must set journal_mode=WAL."""
    db = tmp_path / "wal.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    run_migrations()

    eng = _test_engine(db)
    with eng.connect() as conn:
        row = conn.execute(sa.text("PRAGMA journal_mode")).fetchone()
        assert row[0] == "wal"


def test_engine_enforces_foreign_keys(tmp_path):
    from app.database.engine import create_sqlite_engine

    engine = create_sqlite_engine(tmp_path / "application.db")

    with engine.connect() as connection:
        enabled = connection.exec_driver_sql(
            "PRAGMA foreign_keys"
        ).scalar_one()

    assert enabled == 1


# ── Cascade delete via ORM ─────────────────────────────────────────────────


def test_cascade_delete_resume_removes_analyses(tmp_path, monkeypatch):
    """Deleting a Resume via ORM must cascade to its Analyses."""
    db = tmp_path / "cascade.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    run_migrations()

    from app.database.models import Analysis, JobDescription, Resume
    from sqlalchemy.orm import Session

    eng = _test_engine(db)
    with Session(eng) as session:
        resume = Resume(name="R", data_json="{}")
        job = JobDescription(title="J", content="body")
        session.add_all([resume, job])
        session.flush()

        analysis = Analysis(
            resume_id=resume.id, job_id=job.id, ats_score=50,
        )
        session.add(analysis)
        session.commit()

    with Session(eng) as session:
        resume = session.query(Resume).one()
        session.delete(resume)
        session.commit()

    with Session(eng) as session:
        assert session.query(Analysis).count() == 0
        assert session.query(Resume).count() == 0


def test_cascade_delete_job_removes_analyses(tmp_path, monkeypatch):
    """Deleting a JobDescription via ORM must cascade to its Analyses."""
    db = tmp_path / "cascade2.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    run_migrations()

    from app.database.models import Analysis, JobDescription, Resume
    from sqlalchemy.orm import Session

    eng = _test_engine(db)
    with Session(eng) as session:
        resume = Resume(name="R", data_json="{}")
        job = JobDescription(title="J", content="body")
        session.add_all([resume, job])
        session.flush()

        analysis = Analysis(
            resume_id=resume.id, job_id=job.id, ats_score=75,
        )
        session.add(analysis)
        session.commit()

    with Session(eng) as session:
        job = session.query(JobDescription).one()
        session.delete(job)
        session.commit()

    with Session(eng) as session:
        assert session.query(Analysis).count() == 0
        assert session.query(JobDescription).count() == 0
        # Resume should still exist
        assert session.query(Resume).count() == 1


# ── Cascade delete via raw SQL (PRAGMA enforcement) ────────────────────────


def test_cascade_delete_raw_sql(tmp_path, monkeypatch):
    """ON DELETE CASCADE must work at the SQLite level even without the ORM."""
    db = tmp_path / "raw_cascade.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    run_migrations()

    eng = _test_engine(db)
    with eng.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO resumes (name, data_json) VALUES ('R', '{}')"
        ))
        conn.execute(sa.text(
            "INSERT INTO job_descriptions (title, content) VALUES ('J', 'body')"
        ))
        conn.execute(sa.text(
            "INSERT INTO analyses (resume_id, job_id, ats_score) VALUES (1, 1, 50)"
        ))

    with eng.begin() as conn:
        conn.execute(sa.text("DELETE FROM resumes WHERE id = 1"))

    with eng.connect() as conn:
        count = conn.execute(sa.text("SELECT COUNT(*) FROM analyses")).scalar()
        assert count == 0


def test_foreign_key_violation_rejected(tmp_path, monkeypatch):
    """With foreign_keys=ON, inserting an FK that doesn't match must fail."""
    db = tmp_path / "fk_violation.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    run_migrations()

    eng = _test_engine(db)
    with pytest.raises(Exception):
        with eng.begin() as conn:
            conn.execute(sa.text(
                "INSERT INTO analyses (resume_id, job_id, ats_score) "
                "VALUES (9999, 9999, 100)"
            ))
