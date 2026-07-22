"""Tests for Phase 6 features: application tracker, cover letter library, variants, LinkedIn import, interview prep."""
from __future__ import annotations

import json
import sys
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.database.models import (
    JobDescription,
    Resume,
)

# Ensure QApplication exists for widget tests
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication(sys.argv)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _test_engine(db_path):
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


def _setup_db(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.database.migrate.DB_PATH", db)
    from app.database.migrate import run_migrations
    run_migrations()
    return db


def _seed_resume(session) -> int:
    resume = Resume(name="Test Resume", data_json='{"contact": {"name": "Alice"}}')
    session.add(resume)
    session.flush()
    return resume.id


def _seed_job(session) -> int:
    job = JobDescription(title="Software Engineer", content="Build things")
    session.add(job)
    session.flush()
    return job.id


# ── Application Repository Tests ────────────────────────────────────────────


class TestApplicationRepository:
    def test_create_and_get(self, tmp_path, monkeypatch):
        db = _setup_db(tmp_path, monkeypatch)
        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.application_repository import ApplicationRepository
            repo = ApplicationRepository(session)
            rid = _seed_resume(session)
            jid = _seed_job(session)

            app_id = repo.create(rid, jid, status="draft", notes="Interested")
            assert app_id > 0

            app = repo.get(app_id)
            assert app is not None
            assert app.status == "draft"
            assert app.notes == "Interested"

    def test_list_all(self, tmp_path, monkeypatch):
        db = _setup_db(tmp_path, monkeypatch)
        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.application_repository import ApplicationRepository
            repo = ApplicationRepository(session)
            rid = _seed_resume(session)
            jid = _seed_job(session)
            jid2 = _seed_job(session)
            repo.create(rid, jid)
            repo.create(rid, jid2)
            apps = repo.list_all()
            assert len(apps) == 2

    def test_update_status(self, tmp_path, monkeypatch):
        db = _setup_db(tmp_path, monkeypatch)
        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.application_repository import ApplicationRepository
            repo = ApplicationRepository(session)
            rid = _seed_resume(session)
            jid = _seed_job(session)
            app_id = repo.create(rid, jid, status="draft")

            assert repo.update_status(app_id, "applied")
            assert repo.get(app_id).status == "applied"
            assert repo.get(app_id).applied_at is not None

    def test_update_status_invalid(self, tmp_path, monkeypatch):
        db = _setup_db(tmp_path, monkeypatch)
        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.application_repository import ApplicationRepository
            repo = ApplicationRepository(session)
            rid = _seed_resume(session)
            jid = _seed_job(session)
            app_id = repo.create(rid, jid)

            with pytest.raises(ValueError, match="Invalid status"):
                repo.update_status(app_id, "invalid_status")

    def test_status_workflow(self, tmp_path, monkeypatch):
        db = _setup_db(tmp_path, monkeypatch)
        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.application_repository import ApplicationRepository
            repo = ApplicationRepository(session)
            rid = _seed_resume(session)
            jid = _seed_job(session)
            app_id = repo.create(rid, jid, status="wishlist")

            for status in ["applied", "interview", "offer"]:
                assert repo.update_status(app_id, status)
                assert repo.get(app_id).status == status

    def test_delete(self, tmp_path, monkeypatch):
        db = _setup_db(tmp_path, monkeypatch)
        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.application_repository import ApplicationRepository
            repo = ApplicationRepository(session)
            rid = _seed_resume(session)
            jid = _seed_job(session)
            app_id = repo.create(rid, jid)

            assert repo.delete(app_id)
            assert repo.get(app_id) is None

    def test_update_notes(self, tmp_path, monkeypatch):
        db = _setup_db(tmp_path, monkeypatch)
        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.application_repository import ApplicationRepository
            repo = ApplicationRepository(session)
            rid = _seed_resume(session)
            jid = _seed_job(session)
            app_id = repo.create(rid, jid, notes="old")

            assert repo.update_notes(app_id, "new notes")
            assert repo.get(app_id).notes == "new notes"


# ── Cover Letter Repository Tests ───────────────────────────────────────────


class TestCoverLetterRepository:
    def test_create_and_get(self, tmp_path, monkeypatch):
        db = _setup_db(tmp_path, monkeypatch)
        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.cover_letter_repository import CoverLetterRepository
            repo = CoverLetterRepository(session)
            rid = _seed_resume(session)
            jid = _seed_job(session)

            cl_id = repo.create(rid, jid, content="Dear Hiring Manager...")
            assert cl_id > 0

            cl = repo.get(cl_id)
            assert cl is not None
            assert cl.content == "Dear Hiring Manager..."

    def test_list_all(self, tmp_path, monkeypatch):
        db = _setup_db(tmp_path, monkeypatch)
        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.cover_letter_repository import CoverLetterRepository
            repo = CoverLetterRepository(session)
            rid = _seed_resume(session)
            jid = _seed_job(session)
            repo.create(rid, jid, content="Letter 1")
            repo.create(rid, jid, content="Letter 2")
            assert len(repo.list_all()) == 2

    def test_search(self, tmp_path, monkeypatch):
        db = _setup_db(tmp_path, monkeypatch)
        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.cover_letter_repository import CoverLetterRepository
            repo = CoverLetterRepository(session)
            rid = _seed_resume(session)
            jid = _seed_job(session)
            repo.create(rid, jid, content="Dear Google team")
            repo.create(rid, jid, content="Dear Amazon team")

            results = repo.search(query="Google")
            assert len(results) == 1
            assert "Google" in results[0].content

    def test_delete(self, tmp_path, monkeypatch):
        db = _setup_db(tmp_path, monkeypatch)
        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.cover_letter_repository import CoverLetterRepository
            repo = CoverLetterRepository(session)
            rid = _seed_resume(session)
            jid = _seed_job(session)
            cl_id = repo.create(rid, jid, content="Test")

            assert repo.delete(cl_id)
            assert repo.get(cl_id) is None


# ── Resume Variant Tests ────────────────────────────────────────────────────


class TestResumeVariants:
    def test_create_variant(self, tmp_path, monkeypatch):
        db = _setup_db(tmp_path, monkeypatch)
        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.resume_repository import ResumeRepository
            repo = ResumeRepository(session)
            original_id = repo.save(
                name="Base Resume",
                data_json='{"contact": {"name": "Alice"}}',
            )

            variant_id = repo.create_variant(original_id, "Google")
            assert variant_id is not None
            assert variant_id != original_id

            variant = repo.get_by_id(variant_id)
            assert variant.name == "Base Resume (Google)"
            assert variant.source_type == "variant"
            assert variant.source_filename == str(original_id)

    def test_list_variants(self, tmp_path, monkeypatch):
        db = _setup_db(tmp_path, monkeypatch)
        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.resume_repository import ResumeRepository
            repo = ResumeRepository(session)
            original_id = repo.save(
                name="Base Resume",
                data_json='{"contact": {"name": "Alice"}}',
            )
            repo.create_variant(original_id, "Google")
            repo.create_variant(original_id, "Amazon")

            variants = repo.list_variants(original_id)
            assert len(variants) == 2
            names = {v["name"] for v in variants}
            assert "Base Resume (Google)" in names
            assert "Base Resume (Amazon)" in names

    def test_variant_independent_copy(self, tmp_path, monkeypatch):
        db = _setup_db(tmp_path, monkeypatch)
        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.resume_repository import ResumeRepository
            repo = ResumeRepository(session)
            original_id = repo.save(
                name="Base Resume",
                data_json='{"summary": "original"}',
            )
            variant_id = repo.create_variant(original_id, "V1")

            repo.update(variant_id, '{"summary": "modified"}')

            original = repo.get_by_id(original_id)
            variant = repo.get_by_id(variant_id)
            assert '"summary": "original"' in original.data_json
            assert '"summary": "modified"' in variant.data_json

    def test_create_variant_nonexistent(self, tmp_path, monkeypatch):
        db = _setup_db(tmp_path, monkeypatch)
        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.resume_repository import ResumeRepository
            repo = ResumeRepository(session)
            result = repo.create_variant(9999, "V1")
            assert result is None


# ── LinkedIn Import Tests ───────────────────────────────────────────────────


class TestLinkedInImport:
    def test_import_json(self, tmp_path):
        from app.services.linkedin_import import import_linkedin

        data = {
            "firstName": "John",
            "lastName": "Doe",
            "emailAddress": "john@example.com",
            "headline": "Software Engineer",
            "summary": "Experienced developer",
            "skills": [{"name": "Python"}, {"name": "JavaScript"}],
            "positions": [
                {
                    "companyName": "Acme",
                    "title": "Engineer",
                    "timePeriod": {
                        "startDate": {"month": 1, "year": 2020},
                        "endDate": {"month": 12, "year": 2023},
                    },
                    "description": "Built things\nLed team",
                }
            ],
            "educations": [
                {
                    "schoolName": "MIT",
                    "degree": "BS CS",
                    "timePeriod": {
                        "startDate": {"year": 2016},
                        "endDate": {"year": 2020},
                    },
                }
            ],
        }
        json_path = tmp_path / "linkedin.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")

        result = import_linkedin(json_path)
        assert result.contact.name == "John Doe"
        assert result.contact.email == "john@example.com"
        assert result.headline == "Software Engineer"
        assert result.summary == "Experienced developer"
        assert len(result.skills) == 2
        assert "Python" in result.skills
        assert len(result.experience) == 1
        assert result.experience[0].company == "Acme"
        assert len(result.education) == 1
        assert result.education[0].institution == "MIT"

    def test_import_csv(self, tmp_path):
        from app.services.linkedin_import import import_linkedin

        csv_content = (
            "First Name,Last Name,Email Address,Company,Position,Skills\n"
            "Jane,Smith,jane@test.com,Google,Engineer,Python;Go\n"
        )
        csv_path = tmp_path / "connections.csv"
        csv_path.write_text(csv_content, encoding="utf-8-sig")

        result = import_linkedin(csv_path)
        assert result.contact.name == "Jane Smith"
        assert result.contact.email == "jane@test.com"
        assert len(result.experience) == 1
        assert result.experience[0].company == "Google"
        assert "Python" in result.skills

    def test_import_unsupported_format(self, tmp_path):
        from app.services.linkedin_import import import_linkedin

        txt_path = tmp_path / "data.txt"
        txt_path.write_text("not linkedin data")

        with pytest.raises(ValueError, match="Unsupported file format"):
            import_linkedin(txt_path)


# ── Interview Prep Service Tests ────────────────────────────────────────────


class TestInterviewPrepService:
    @patch("app.services.interview_prep.OllamaClient")
    def test_generate_questions(self, MockClient):
        from app.services.interview_prep import InterviewPrepService
        from app.domain.resume import ResumeData, ContactInfo, ExperienceItem

        mock_client = MockClient.return_value
        mock_client.generate.return_value = json.dumps({
            "questions": [
                {
                    "category": "behavioral",
                    "question": "Tell me about a time you led a team.",
                    "star": {
                        "situation": "Team of 5 engineers",
                        "task": "Deliver project",
                        "action": "Organized sprints",
                        "result": "Shipped on time",
                    },
                },
                {
                    "category": "technical",
                    "question": "How would you design a distributed system?",
                    "star": {
                        "situation": "High traffic app",
                        "task": "Scale to 1M users",
                        "action": "Implemented caching",
                        "result": "99.9% uptime",
                    },
                },
            ],
        })

        resume = ResumeData(
            contact=ContactInfo(name="Alice"),
            experience=[ExperienceItem(title="Engineer", company="Acme", bullets=["Led team"])],
        )

        svc = InterviewPrepService(client=mock_client)
        result = svc.generate_questions(resume, "Senior Engineer", "Google")

        assert len(result.questions) == 2
        assert result.questions[0].category == "behavioral"
        assert result.questions[0].star.situation == "Team of 5 engineers"
        assert result.questions[1].category == "technical"

    @patch("app.services.interview_prep.OllamaClient")
    def test_generate_questions_invalid_json(self, MockClient):
        from app.services.interview_prep import InterviewPrepService
        from app.domain.resume import ResumeData

        mock_client = MockClient.return_value
        mock_client.generate.return_value = "not json"

        svc = InterviewPrepService(client=mock_client)
        result = svc.generate_questions(ResumeData(), "Engineer", "Acme")
        assert len(result.questions) == 0

    def test_to_markdown(self):
        from app.services.interview_prep import (
            InterviewPrepService,
            InterviewQuestionsResult,
            InterviewQuestion,
            STAROutline,
        )

        result = InterviewQuestionsResult(
            questions=[
                InterviewQuestion(
                    category="behavioral",
                    question="Tell me about a leadership moment",
                    star=STAROutline(
                        situation="Team conflict",
                        task="Resolve it",
                        action="Mediated",
                        result="Unified team",
                    ),
                ),
                InterviewQuestion(
                    category="technical",
                    question="Design a cache",
                    star=STAROutline(),
                ),
            ]
        )

        svc = InterviewPrepService.__new__(InterviewPrepService)
        md = svc.to_markdown(result)
        assert "Behavioral Questions" in md
        assert "Technical Questions" in md
        assert "Tell me about a leadership moment" in md
        assert "**Situation:** Team conflict" in md
