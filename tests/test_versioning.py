"""Tests for versioning models, migration 0004, and VersioningRepository."""
import json
import sqlite3
import textwrap
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from sqlalchemy.orm import Session

from app.database.models import (
    AgentConversation,
    AgentMessage,
    Base,
    CoverLetter,
    InterviewSession,
    JobApplication,
    JobDescription,
    Resume,
    ResumeVersion,
    ScoreSnapshot,
    SuggestionRecord,
    TargetingSession,
    TemplatePreference,
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _test_engine(db_path: Path):
    from sqlalchemy import event as sa_event, create_engine as _create_engine
    eng = _create_engine(f"sqlite:///{db_path}", echo=False)
    @sa_event.listens_for(eng, "connect")
    def _pragmas(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()
    return eng


def _alembic_config(db_path: Path):
    from alembic.config import Config
    project_root = Path(__file__).resolve().parent.parent
    migrations_dir = project_root / "migrations"
    config = Config()
    config.set_main_option("script_location", str(migrations_dir))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def _get_version(db_path: Path) -> str | None:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        return row[0] if row else None
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()


def _get_tables(db_path: Path) -> set[str]:
    conn = sqlite3.connect(str(db_path))
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    return tables


# ── Migration 0004 tests ───────────────────────────────────────────────────


def test_migration_0004_creates_all_new_tables(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()

    tables = _get_tables(db)
    expected = {
        "resume_versions",
        "targeting_sessions",
        "suggestions",
        "template_preferences",
        "cover_letters",
        "agent_conversations",
        "agent_messages",
        "job_applications",
        "interview_sessions",
        "score_snapshots",
    }
    assert expected.issubset(tables)
    assert _get_version(db) == "0004"


def test_migration_0004_is_idempotent(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()
    # Run again — should not fail
    run_migrations()
    assert _get_version(db) == "0004"


def test_migration_0004_preserves_existing_data(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()

    eng = _test_engine(db)
    with Session(eng) as session:
        resume = Resume(name="Existing", data_json="{}")
        session.add(resume)
        session.commit()

    # Re-run migration (upgrade is a no-op but verifies no data loss)
    command.upgrade(_alembic_config(db), "head")

    with Session(eng) as session:
        r = session.query(Resume).one()
        assert r.name == "Existing"


# ── ORM model tests ────────────────────────────────────────────────────────


def test_resume_version_unique_constraint(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()

    eng = _test_engine(db)
    with Session(eng) as session:
        resume = Resume(name="R", data_json="{}")
        session.add(resume)
        session.flush()

        v1 = ResumeVersion(
            resume_id=resume.id, version_number=1, data_json="{}",
        )
        session.add(v1)
        session.flush()

        # Duplicate version_number should fail
        v_dup = ResumeVersion(
            resume_id=resume.id, version_number=1, data_json="{}",
        )
        session.add(v_dup)
        with pytest.raises(Exception):
            session.flush()


def test_resume_version_cascade_delete(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()

    eng = _test_engine(db)
    with Session(eng) as session:
        resume = Resume(name="R", data_json="{}")
        session.add(resume)
        session.flush()
        v = ResumeVersion(
            resume_id=resume.id, version_number=1, data_json="{}",
        )
        session.add(v)
        session.commit()

    with Session(eng) as session:
        session.delete(session.query(Resume).one())
        session.commit()

    with Session(eng) as session:
        assert session.query(ResumeVersion).count() == 0


def test_targeting_session_cascade_delete_on_version(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()

    eng = _test_engine(db)
    with Session(eng) as session:
        resume = Resume(name="R", data_json="{}")
        job = JobDescription(title="J", content="body")
        session.add_all([resume, job])
        session.flush()

        v = ResumeVersion(
            resume_id=resume.id, version_number=1, data_json="{}",
        )
        session.add(v)
        session.flush()

        ts = TargetingSession(
            resume_version_id=v.id,
            job_id=job.id,
            requirements_json="{}",
            score_report_json="{}",
        )
        session.add(ts)
        session.commit()

    with Session(eng) as session:
        session.delete(session.query(ResumeVersion).one())
        session.commit()

    with Session(eng) as session:
        assert session.query(TargetingSession).count() == 0


def test_suggestion_cascade_delete_on_session(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()

    eng = _test_engine(db)
    with Session(eng) as session:
        resume = Resume(name="R", data_json="{}")
        job = JobDescription(title="J", content="body")
        session.add_all([resume, job])
        session.flush()
        v = ResumeVersion(
            resume_id=resume.id, version_number=1, data_json="{}",
        )
        session.add(v)
        session.flush()
        ts = TargetingSession(
            resume_version_id=v.id, job_id=job.id,
            requirements_json="{}", score_report_json="{}",
        )
        session.add(ts)
        session.flush()

        sug = SuggestionRecord(
            targeting_session_id=ts.id,
            document_path="experience[0].bullets[0]",
            original_text="Old bullet",
            suggested_text="New bullet",
            evidence_json="{}",
            status="pending",
        )
        session.add(sug)
        session.commit()

    with Session(eng) as session:
        session.delete(session.query(TargetingSession).one())
        session.commit()

    with Session(eng) as session:
        assert session.query(SuggestionRecord).count() == 0


def test_agent_message_cascade_delete_on_conversation(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()

    eng = _test_engine(db)
    with Session(eng) as session:
        conv = AgentConversation(title="Test")
        session.add(conv)
        session.flush()

        msg = AgentMessage(
            conversation_id=conv.id,
            role="user",
            content="Hello",
        )
        session.add(msg)
        session.commit()

    with Session(eng) as session:
        session.delete(session.query(AgentConversation).one())
        session.commit()

    with Session(eng) as session:
        assert session.query(AgentMessage).count() == 0


def test_template_preference_unique_constraint(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()

    eng = _test_engine(db)
    with Session(eng) as session:
        resume = Resume(name="R", data_json="{}")
        session.add(resume)
        session.flush()

        tp1 = TemplatePreference(resume_id=resume.id, template_id="standard")
        session.add(tp1)
        session.flush()

        tp2 = TemplatePreference(resume_id=resume.id, template_id="compact")
        session.add(tp2)
        with pytest.raises(Exception):
            session.flush()


def test_agent_conversation_set_null_on_resume_delete(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()

    eng = _test_engine(db)
    with Session(eng) as session:
        resume = Resume(name="R", data_json="{}")
        session.add(resume)
        session.flush()
        conv = AgentConversation(resume_id=resume.id, title="Chat")
        session.add(conv)
        session.commit()

    with Session(eng) as session:
        session.delete(session.query(Resume).one())
        session.commit()

    with Session(eng) as session:
        conv = session.query(AgentConversation).one()
        assert conv.resume_id is None


# ── VersioningRepository tests ─────────────────────────────────────────────


def test_versioning_repository_create_and_get(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()

    from app.database.repositories.versioning_repository import VersioningRepository

    eng = _test_engine(db)
    with Session(eng) as session:
        resume = Resume(name="R", data_json="{}")
        session.add(resume)
        session.flush()

        repo = VersioningRepository(session)
        vid = repo.create_version(resume.id, '{"v":1}', "Initial")
        session.commit()

    with Session(eng) as session:
        repo = VersioningRepository(session)
        v = repo.get_version(vid)
        assert v is not None
        assert v.version_number == 1
        assert v.change_summary == "Initial"


def test_versioning_repository_sequential_version_numbers(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()

    from app.database.repositories.versioning_repository import VersioningRepository

    eng = _test_engine(db)
    with Session(eng) as session:
        resume = Resume(name="R", data_json="{}")
        session.add(resume)
        session.flush()

        repo = VersioningRepository(session)
        v1 = repo.create_version(resume.id, '{"v":1}')
        v2 = repo.create_version(resume.id, '{"v":2}')
        v3 = repo.create_version(resume.id, '{"v":3}')
        resume_id = resume.id
        session.commit()

    with Session(eng) as session:
        repo = VersioningRepository(session)
        versions = repo.get_versions(resume_id)
        assert len(versions) == 3
        assert [v.version_number for v in versions] == [1, 2, 3]


def test_versioning_repository_get_latest(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()

    from app.database.repositories.versioning_repository import VersioningRepository

    eng = _test_engine(db)
    with Session(eng) as session:
        resume = Resume(name="R", data_json="{}")
        session.add(resume)
        session.flush()

        repo = VersioningRepository(session)
        repo.create_version(resume.id, '{"v":1}')
        repo.create_version(resume.id, '{"v":2}')
        resume_id = resume.id
        session.commit()

    with Session(eng) as session:
        repo = VersioningRepository(session)
        latest = repo.get_latest_version(resume_id)
        assert latest is not None
        assert latest.version_number == 2


def test_versioning_repository_targeting_session(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()

    from app.database.repositories.versioning_repository import VersioningRepository

    eng = _test_engine(db)
    with Session(eng) as session:
        resume = Resume(name="R", data_json="{}")
        job = JobDescription(title="J", content="body")
        session.add_all([resume, job])
        session.flush()

        repo = VersioningRepository(session)
        vid = repo.create_version(resume.id, '{}')
        ts_id = repo.create_targeting_session(
            vid, job.id, '{"reqs":"{}"}', '{"score":"{}"}',
        )
        session.commit()

    with Session(eng) as session:
        repo = VersioningRepository(session)
        ts = repo.get_targeting_session(ts_id)
        assert ts is not None
        assert ts.requirements_json == '{"reqs":"{}"}'


def test_versioning_repository_suggestions(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()

    from app.database.repositories.versioning_repository import VersioningRepository

    eng = _test_engine(db)
    with Session(eng) as session:
        resume = Resume(name="R", data_json="{}")
        job = JobDescription(title="J", content="body")
        session.add_all([resume, job])
        session.flush()

        repo = VersioningRepository(session)
        vid = repo.create_version(resume.id, '{}')
        ts_id = repo.create_targeting_session(vid, job.id, '{}', '{}')

        s1 = repo.add_suggestion(
            ts_id, "experience[0].bullets[0]",
            "Old", "New", '{"evidence":"..."}',
        )
        s2 = repo.add_suggestion(
            ts_id, "summary",
            "Old summary", "New summary", '{"evidence":"..."}',
        )
        session.commit()

    with Session(eng) as session:
        repo = VersioningRepository(session)
        suggestions = repo.get_suggestions(ts_id)
        assert len(suggestions) == 2
        assert suggestions[0].document_path == "experience[0].bullets[0]"

        repo.update_suggestion_status(s1, "accepted")
        session.commit()

        updated = repo.get_suggestions(ts_id)
        assert updated[0].status == "accepted"
        assert updated[1].status == "pending"


# ── Score snapshot tests ───────────────────────────────────────────────────


def test_score_snapshot_stores_and_cascades(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()

    eng = _test_engine(db)
    with Session(eng) as session:
        resume = Resume(name="R", data_json="{}")
        session.add(resume)
        session.flush()

        snap = ScoreSnapshot(
            resume_id=resume.id,
            ats_score=85,
            keyword_match=72.5,
            skills_match=60.0,
            score_report_json='{"v":"1"}',
        )
        session.add(snap)
        session.commit()

    with Session(eng) as session:
        s = session.query(ScoreSnapshot).one()
        assert s.ats_score == 85
        assert s.keyword_match == 72.5

    # Delete resume -> cascade
    with Session(eng) as session:
        session.delete(session.query(Resume).one())
        session.commit()

    with Session(eng) as session:
        assert session.query(ScoreSnapshot).count() == 0
