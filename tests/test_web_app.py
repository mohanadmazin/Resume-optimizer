"""Integration coverage for the unified FastAPI web workflow."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from app.database.models import Base
import app.database.session as database_session
import web_main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'web-test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(database_session, "SessionLocal", sessionmaker(bind=engine))
    web_main._sessions.clear()
    web_main._session_seen.clear()
    with TestClient(web_main.app) as test_client:
        yield test_client
    web_main._sessions.clear()
    web_main._session_seen.clear()
    engine.dispose()


def _builder_payload() -> dict:
    return {
        "resumeId": None,
        "year": "2026",
        "contact": {
            "fullName": "Fifi Test",
            "email": "fifi@example.com",
            "phone": "0123456789",
            "linkedin": "",
            "website": "",
            "country": "Malaysia",
            "state": "Selangor",
            "city": "Shah Alam",
            "visibility": {"country": True, "state": True, "city": True},
        },
        "experience": [{
            "title": "Sales Manager",
            "company": "Example Travel",
            "location": "Kuala Lumpur",
            "type": "Full-time",
            "start": "2023",
            "end": "Present",
            "description": "Led a team of five.\nIncreased sales by 20%.",
        }],
        "project": [],
        "education": [],
        "certifications": [],
        "coursework": {
            "courseworkTitle": "Relevant Coursework",
            "courseworkInstitution": "",
            "courseworkItems": "",
        },
        "skills": [
            {"name": "Sales Operations", "level": "Advanced"},
            {"name": "Leadership", "level": "Advanced"},
        ],
        "summary": {
            "professionalTitle": "Sales & Operations Manager",
            "summaryText": "Experienced sales operations manager.",
        },
        "coverLetter": {
            "coverJobTitle": "",
            "coverCompany": "",
            "coverHiringManager": "",
            "coverTone": "Professional",
            "jobDescription": "",
            "output": "",
        },
        "_createVersion": True,
    }


def test_all_web_pages_render(client):
    for path in (
        "/", "/upload", "/jobs", "/ats", "/optimize",
        "/cover-letter", "/resignation-letter", "/applications", "/settings", "/builder/",
    ):
        response = client.get(path)
        assert response.status_code == 200, path
    assert client.get("/openapi.json").status_code == 404


def test_builder_and_ats_share_the_same_resume(client):
    saved = client.put("/api/builder/state", json=_builder_payload())
    assert saved.status_code == 200
    resume_id = saved.json()["id"]

    loaded = client.get("/api/builder/state")
    assert loaded.status_code == 200
    assert loaded.json()["resumeId"] == resume_id
    assert loaded.json()["contact"]["fullName"] == "Fifi Test"

    job = client.post(
        "/jobs",
        data={
            "job_title": "Sales Operations Manager",
            "job_company": "Target Sdn Bhd",
            "job_location": "Kuala Lumpur",
            "job_source_url": "https://example.com/job",
            "job_employment_type": "Full-time",
            "job_salary": "RM 8,000",
            "job_date_posted": "2026-07-22",
            "job_status": "target",
            "job_text": (
                "Sales Operations Manager with leadership, CRM, forecasting, "
                "stakeholder management and sales operations experience."
            ),
        },
        follow_redirects=False,
    )
    assert job.status_code == 303

    result = client.post("/ats/run", follow_redirects=False)
    assert result.status_code == 303
    page = client.get("/ats")
    assert page.status_code == 200
    assert "stakeholder management" in page.text.lower()

    jobs = client.get("/api/jobs").json()
    assert jobs[0]["company"] == "Target Sdn Bhd"
    assert jobs[0]["location"] == "Kuala Lumpur"


def test_resignation_letter_is_editable_and_exportable(client):
    generated = client.post(
        "/resignation-letter/generate",
        data={
            "employee_name": "Fifi Test",
            "employee_address": "Shah Alam",
            "employee_email": "fifi@example.com",
            "employee_phone": "0123456789",
            "letter_date": "2026-07-22",
            "manager_name": "Manager",
            "manager_title": "Director",
            "company_name": "Target Sdn Bhd",
            "company_address": "Kuala Lumpur",
            "position": "Sales Manager",
            "last_working_day": "2026-09-22",
            "notice_period": "2 months",
            "tone": "formal",
            "reason": "none",
            "reason_details": "",
            "transition_support": "on",
            "appreciation_note": "Thank you for the opportunities.",
            "language": "en",
            "resignation_type": "standard",
            "include_leave_balance": "on",
            "include_property_return": "on",
        },
        follow_redirects=False,
    )
    assert generated.status_code == 303

    edited = "Edited resignation letter\nWith confirmed handover details."
    saved = client.post(
        "/resignation-letter/save",
        data={"letter_text": edited},
        follow_redirects=False,
    )
    assert saved.status_code == 303
    assert edited in client.get("/resignation-letter").text

    txt = client.post("/resignation-letter/download/txt", data={"letter_text": edited})
    assert txt.status_code == 200
    assert edited in txt.text

    pdf = client.post("/resignation-letter/download/pdf", data={"letter_text": edited})
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")

    docx = client.post("/resignation-letter/download/docx", data={"letter_text": edited})
    assert docx.status_code == 200
    assert docx.content.startswith(b"PK")


def test_ollama_test_uses_current_form_values(client, monkeypatch):
    observed = {}

    async def fake_test(url: str, model: str = ""):
        observed.update(url=url, model=model)
        return {
            "connected": True,
            "model_available": True,
            "models": [model],
            "url": url,
            "error": "",
        }

    monkeypatch.setattr(web_main, "_test_ollama_payload", fake_test)
    response = client.post(
        "/api/ollama/test",
        json={"ollama_url": "http://192.168.1.20:11434", "model": "qwen3:latest"},
    )
    assert response.status_code == 200
    assert observed == {
        "url": "http://192.168.1.20:11434",
        "model": "qwen3:latest",
    }


def test_application_tracker_create_update_delete(client):
    saved = client.put("/api/builder/state", json=_builder_payload())
    assert saved.status_code == 200
    client.post(
        "/jobs",
        data={
            "job_title": "Operations Lead",
            "job_company": "Tracker Sdn Bhd",
            "job_location": "Selangor",
            "job_text": "Operations leadership, planning, reporting and stakeholder coordination.",
        },
        follow_redirects=False,
    )
    created = client.post(
        "/applications/create",
        data={"status": "wishlist", "notes": "Contact recruiter on Friday"},
        follow_redirects=False,
    )
    assert created.status_code == 303
    page = client.get("/applications")
    assert "Tracker Sdn Bhd" in page.text
    assert "Contact recruiter on Friday" in page.text

    from app.database.repositories.application_repository import ApplicationRepository
    with database_session.get_session() as session:
        application_id = ApplicationRepository(session).list_detailed()[0]["id"]

    updated = client.post(
        f"/applications/{application_id}/update",
        data={"status": "interview", "notes": "Interview booked"},
        follow_redirects=False,
    )
    assert updated.status_code == 303
    page = client.get("/applications")
    assert "Interview booked" in page.text
    assert "Interview" in page.text

    deleted = client.post(f"/applications/{application_id}/delete", follow_redirects=False)
    assert deleted.status_code == 303
    assert "Tracker Sdn Bhd" not in client.get("/applications").text


def test_resume_version_can_be_restored(client):
    initial = _builder_payload()
    saved = client.put("/api/builder/state", json=initial)
    resume_id = saved.json()["id"]

    changed = _builder_payload()
    changed["resumeId"] = resume_id
    changed["summary"]["summaryText"] = "Updated summary that should later be replaced."
    changed["_createVersion"] = True
    assert client.put("/api/builder/state", json=changed).status_code == 200

    from app.database.repositories.versioning_repository import VersioningRepository
    with database_session.get_session() as session:
        versions = VersioningRepository(session).list_version_summaries(resume_id)
    original_version_id = min(versions, key=lambda item: item["version_number"])["id"]

    restored = client.post(
        f"/resumes/{resume_id}/versions/{original_version_id}/restore",
        follow_redirects=False,
    )
    assert restored.status_code == 303
    builder = client.get("/api/builder/state").json()
    assert builder["summary"]["summaryText"] == "Experienced sales operations manager."


def _prepare_resume_job_and_ats(client):
    saved = client.put("/api/builder/state", json=_builder_payload())
    assert saved.status_code == 200
    job = client.post(
        "/jobs",
        data={
            "job_title": "Sales Operations Manager",
            "job_company": "Export Test Sdn Bhd",
            "job_location": "Kuala Lumpur",
            "job_text": "Sales operations leadership CRM forecasting and reporting.",
        },
        follow_redirects=False,
    )
    assert job.status_code == 303
    assert client.post("/ats/run", follow_redirects=False).status_code == 303


def test_optimization_apply_and_every_export_format(client, monkeypatch):
    from app.domain.fact_guard import ChangeType, FactGuardResult, ProposedChange
    import app.services.optimizer as optimizer_module

    _prepare_resume_job_and_ats(client)

    def fake_optimize(resume, _job_text, _ats, _client):
        change = ProposedChange(
            change_type=ChangeType.SUMMARY,
            section="summary",
            original=resume.summary,
            rewritten="Targeted and verified sales operations summary.",
            is_factually_supported=True,
            requires_review=False,
            review_reason="Supported by existing experience.",
        )
        return resume.model_copy(deep=True), FactGuardResult(safe_changes=[change])

    monkeypatch.setattr(optimizer_module, "optimize_resume", fake_optimize)
    generated = client.post("/optimize/run", follow_redirects=False)
    assert generated.status_code == 303
    assert "Targeted and verified" in client.get("/optimize").text

    applied = client.post(
        "/optimize/apply",
        data={"accepted_indexes": "0"},
        follow_redirects=False,
    )
    assert applied.status_code == 303

    markdown = client.get("/optimize/download/md")
    assert markdown.status_code == 200
    assert "Targeted and verified" in markdown.text

    text = client.get("/optimize/download/txt")
    assert text.status_code == 200
    assert "Targeted and verified" in text.text

    json_export = client.get("/optimize/download/json")
    assert json_export.status_code == 200
    assert json_export.headers["content-type"].startswith("application/json")
    assert json_export.json()["summary"] == "Targeted and verified sales operations summary."

    docx = client.get("/optimize/download/docx")
    assert docx.status_code == 200
    assert docx.content.startswith(b"PK")

    pdf = client.get("/optimize/download/pdf")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")


def test_cover_letter_generation_edit_and_exports(client, monkeypatch):
    from app.services.cover_letter import CoverLetterResult
    import app.services.cover_letter as cover_module

    _prepare_resume_job_and_ats(client)

    monkeypatch.setattr(
        cover_module,
        "generate_cover_letter",
        lambda *_args, **_kwargs: CoverLetterResult(
            text="Dear Hiring Manager,\n\nGenerated draft.\n\nSincerely,\nFifi Test",
            warnings=("Review this draft before sending.",),
        ),
    )
    generated = client.post("/cover-letter/run", follow_redirects=False)
    assert generated.status_code == 303
    assert "Generated draft" in client.get("/cover-letter").text

    edited = "Dear Hiring Manager,\n\nEdited and approved draft.\n\nSincerely,\nFifi Test"
    saved = client.post(
        "/cover-letter/save",
        data={"letter_text": edited},
        follow_redirects=False,
    )
    assert saved.status_code == 303

    for file_format in ("txt", "docx", "pdf"):
        exported = client.post(
            f"/cover-letter/download/{file_format}",
            data={"letter_text": edited},
        )
        assert exported.status_code == 200
        if file_format == "txt":
            assert "Edited and approved" in exported.text
        elif file_format == "docx":
            assert exported.content.startswith(b"PK")
        else:
            assert exported.content.startswith(b"%PDF")


def test_web_session_restores_selected_resume_after_memory_reset(client):
    saved = client.put("/api/builder/state", json=_builder_payload())
    assert saved.status_code == 200
    resume_id = saved.json()["id"]

    # Simulate a server process losing only its in-memory workflow cache.
    web_main._sessions.clear()
    web_main._session_seen.clear()

    restored = client.get("/api/builder/state")
    assert restored.status_code == 200
    assert restored.json()["resumeId"] == resume_id
    assert restored.json()["contact"]["fullName"] == "Fifi Test"


def test_unsafe_job_source_url_is_not_persisted(client):
    client.post(
        "/jobs",
        data={
            "job_title": "Safe Link Test",
            "job_company": "Example",
            "job_source_url": "javascript:alert(1)",
            "job_text": "A valid job description with enough details for the record.",
        },
        follow_redirects=False,
    )
    jobs = client.get("/api/jobs").json()
    assert jobs[0]["source_url"] == ""
