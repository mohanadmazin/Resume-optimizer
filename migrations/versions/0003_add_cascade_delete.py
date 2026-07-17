"""add ondelete CASCADE to foreign keys

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-17

SQLite does not support ALTER TABLE to modify foreign-key constraints.
This migration recreates the child tables with ``ON DELETE CASCADE`` while
preserving all existing data.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_has_fk(table: str, target: str) -> bool:
    """Return True if *table* already has a FK pointing at *target* with CASCADE."""
    bind = op.get_bind()
    # PRAGMAs don't accept bind parameters — use the raw DBAPI connection.
    dbapi = bind.connection.driver_connection  # type: ignore[union-attr]
    cursor = dbapi.execute(f"PRAGMA foreign_key_list({table})")  # noqa: S608
    for row in cursor.fetchall():
        # row: (id, seq, table, from, to, on_update, on_delete, match)
        if row[2] == target and row[6] == "CASCADE":
            return True
    return False


def upgrade() -> None:
    # If analyses.resume_id already has ON DELETE CASCADE, skip (idempotent).
    if _table_has_fk("analyses", "resumes"):
        return

    # Disable FK enforcement for the duration of the rebuild so we can
    # drop tables that still reference each other.
    op.execute(sa.text("PRAGMA foreign_keys=OFF"))

    # ── analyses ────────────────────────────────────────────────────────
    op.execute(sa.text("CREATE TABLE _analyses_new ("
        "id INTEGER PRIMARY KEY,"
        "resume_id INTEGER NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,"
        "job_id INTEGER NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,"
        "ats_score INTEGER NOT NULL,"
        "keyword_match FLOAT DEFAULT 0.0,"
        "skills_match FLOAT DEFAULT 0.0,"
        "missing_keywords TEXT DEFAULT '[]',"
        "suggestions TEXT DEFAULT '[]',"
        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
    ")"))
    op.execute(sa.text(
        "INSERT INTO _analyses_new "
        "SELECT id, resume_id, job_id, ats_score, keyword_match, "
        "skills_match, missing_keywords, suggestions, created_at "
        "FROM analyses"
    ))
    op.execute(sa.text("DROP TABLE analyses"))
    op.execute(sa.text("ALTER TABLE _analyses_new RENAME TO analyses"))

    # ── optimizations ───────────────────────────────────────────────────
    op.execute(sa.text("CREATE TABLE _optimizations_new ("
        "id INTEGER PRIMARY KEY,"
        "resume_id INTEGER NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,"
        "job_id INTEGER NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,"
        "model VARCHAR(100) DEFAULT '',"
        "optimized_json TEXT NOT NULL,"
        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
    ")"))
    op.execute(sa.text(
        "INSERT INTO _optimizations_new "
        "SELECT id, resume_id, job_id, model, optimized_json, created_at "
        "FROM optimizations"
    ))
    op.execute(sa.text("DROP TABLE optimizations"))
    op.execute(sa.text("ALTER TABLE _optimizations_new RENAME TO optimizations"))

    op.execute(sa.text("PRAGMA foreign_keys=ON"))


def downgrade() -> None:
    op.execute(sa.text("PRAGMA foreign_keys=OFF"))

    # Rebuild without CASCADE (original schema).
    op.execute(sa.text("CREATE TABLE _analyses_old ("
        "id INTEGER PRIMARY KEY,"
        "resume_id INTEGER NOT NULL REFERENCES resumes(id),"
        "job_id INTEGER NOT NULL REFERENCES job_descriptions(id),"
        "ats_score INTEGER NOT NULL,"
        "keyword_match FLOAT DEFAULT 0.0,"
        "skills_match FLOAT DEFAULT 0.0,"
        "missing_keywords TEXT DEFAULT '[]',"
        "suggestions TEXT DEFAULT '[]',"
        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
    ")"))
    op.execute(sa.text(
        "INSERT INTO _analyses_old "
        "SELECT id, resume_id, job_id, ats_score, keyword_match, "
        "skills_match, missing_keywords, suggestions, created_at "
        "FROM analyses"
    ))
    op.execute(sa.text("DROP TABLE analyses"))
    op.execute(sa.text("ALTER TABLE _analyses_old RENAME TO analyses"))

    op.execute(sa.text("CREATE TABLE _optimizations_old ("
        "id INTEGER PRIMARY KEY,"
        "resume_id INTEGER NOT NULL REFERENCES resumes(id),"
        "job_id INTEGER NOT NULL REFERENCES job_descriptions(id),"
        "model VARCHAR(100) DEFAULT '',"
        "optimized_json TEXT NOT NULL,"
        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
    ")"))
    op.execute(sa.text(
        "INSERT INTO _optimizations_old "
        "SELECT id, resume_id, job_id, model, optimized_json, created_at "
        "FROM optimizations"
    ))
    op.execute(sa.text("DROP TABLE optimizations"))
    op.execute(sa.text("ALTER TABLE _optimizations_old RENAME TO optimizations"))

    op.execute(sa.text("PRAGMA foreign_keys=ON"))
