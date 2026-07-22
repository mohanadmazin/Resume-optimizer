"""ResumeAI — FastAPI web interface.

Run with either::

    python web_main.py
    uvicorn web_main:app --reload --port 8000

The web interface shares the same local SQLite database and service layer as the
PySide desktop application.  Session state is intentionally kept server-side so
resume data is not placed in browser cookies.
"""
from __future__ import annotations

import json
import logging
import re
import tempfile
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database.migrate import run_migrations
from app.logging_config import setup_logging

setup_logging()
run_migrations()

logger = logging.getLogger(__name__)

app = FastAPI(title="ResumeAI Local Resume Optimizer", docs_url=None, redoc_url=None, openapi_url=None)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "web" / "static")), name="static")
_BUILDER_DIR = BASE_DIR / "web" / "resume_dashboard"
app.mount("/builder", StaticFiles(directory=str(_BUILDER_DIR), html=True), name="builder")

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
ALLOWED_RESUME_SUFFIXES = {".pdf", ".docx", ".doc", ".txt"}
SESSION_COOKIE = "resume_optimizer_sid"
SESSION_MAX_AGE = 60 * 60 * 12
MAX_SESSIONS = 250

# In-memory workflow state. Persistent resume/job records remain in SQLite.
_sessions: dict[str, dict[str, Any]] = {}
_session_seen: dict[str, float] = {}


def _new_session_id() -> str:
    return uuid.uuid4().hex


def _prune_sessions() -> None:
    """Bound the local in-memory session store and discard stale entries."""
    now = time.time()
    stale = [sid for sid, seen in _session_seen.items() if now - seen > SESSION_MAX_AGE]
    for sid in stale:
        _sessions.pop(sid, None)
        _session_seen.pop(sid, None)

    if len(_sessions) <= MAX_SESSIONS:
        return
    overflow = len(_sessions) - MAX_SESSIONS
    for sid, _ in sorted(_session_seen.items(), key=lambda item: item[1])[:overflow]:
        _sessions.pop(sid, None)
        _session_seen.pop(sid, None)


def _serialize_session(session: dict[str, Any]) -> dict[str, Any]:
    """Convert runtime objects into a JSON-safe workflow snapshot."""
    from app.domain.analysis import ATSResult
    from app.domain.fact_guard import FactGuardResult
    from app.domain.resume import ResumeData

    output: dict[str, Any] = {}
    for key, value in session.items():
        if key == "resume" and isinstance(value, ResumeData):
            output["resume_json"] = value.model_dump(mode="json")
        elif key == "optimized_resume" and isinstance(value, ResumeData):
            output["optimized_resume_json"] = value.model_dump(mode="json")
        elif key == "fact_guard" and isinstance(value, FactGuardResult):
            output["fact_guard_json"] = value.model_dump(mode="json")
        elif key == "ats_result" and isinstance(value, ATSResult):
            output["ats_result_json"] = value.to_dict()
        elif key not in {"resume_json", "optimized_resume_json", "fact_guard_json", "ats_result_json"}:
            try:
                json.dumps(value, default=str)
            except (TypeError, ValueError):
                continue
            output[key] = value
    return output


def _deserialize_session(payload: dict[str, Any]) -> dict[str, Any]:
    """Rebuild Pydantic/dataclass objects from a stored workflow snapshot."""
    from app.domain.analysis import ATSResult
    from app.domain.fact_guard import FactGuardResult
    from app.domain.resume import ResumeData
    from app.domain.scoring import ResumeScoreReport

    data = dict(payload or {})
    resume_json = data.pop("resume_json", None)
    optimized_json = data.pop("optimized_resume_json", None)
    fact_json = data.pop("fact_guard_json", None)
    ats_json = data.pop("ats_result_json", None)
    try:
        if resume_json:
            data["resume"] = ResumeData.model_validate(resume_json)
        if optimized_json:
            data["optimized_resume"] = ResumeData.model_validate(optimized_json)
        if fact_json:
            data["fact_guard"] = FactGuardResult.model_validate(fact_json)
        if ats_json:
            ats_data = dict(ats_json)
            report = ats_data.get("score_report")
            if isinstance(report, dict):
                ats_data["score_report"] = ResumeScoreReport.model_validate(report)
            data["ats_result"] = ATSResult(**ats_data)
    except Exception:
        logger.warning("A persisted web workflow could not be fully restored", exc_info=True)
    return data


def _load_persisted_session(sid: str) -> dict[str, Any]:
    try:
        from app.database.repositories.web_repository import WebSessionRepository
        from app.database.session import get_session
        with get_session() as db_session:
            return _deserialize_session(WebSessionRepository(db_session).load(sid))
    except Exception:
        logger.warning("Could not restore web session", exc_info=True)
        return {}


def _save_persisted_session(sid: str, session: dict[str, Any]) -> None:
    try:
        from app.database.repositories.web_repository import WebSessionRepository
        from app.database.session import get_session
        with get_session() as db_session:
            repo = WebSessionRepository(db_session)
            repo.save(sid, _serialize_session(session))
            repo.prune(SESSION_MAX_AGE)
    except Exception:
        logger.warning("Could not persist web session", exc_info=True)


@app.middleware("http")
async def attach_local_session(request: Request, call_next):
    """Restore and persist a bounded local workflow session.

    Only a random session identifier is stored in the browser. Resume content,
    job descriptions and generated documents remain in the local SQLite file.
    """
    _prune_sessions()
    sid = request.cookies.get(SESSION_COOKIE, "")
    is_new = not sid
    if not sid:
        sid = _new_session_id()
    if sid not in _sessions:
        _sessions[sid] = _load_persisted_session(sid)
    _session_seen[sid] = time.time()
    request.state.resume_optimizer_sid = sid

    try:
        response = await call_next(request)
    finally:
        _save_persisted_session(sid, _sessions.get(sid, {}))

    if is_new:
        response.set_cookie(
            SESSION_COOKIE,
            sid,
            max_age=SESSION_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=False,  # localhost HTTP by default
        )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' http://localhost:* http://127.0.0.1:*",
    )
    return response


@app.get("/builder")
async def builder_root() -> RedirectResponse:
    return RedirectResponse("/builder/", status_code=308)


def _ensure_workflow_objects(session: dict[str, Any]) -> None:
    """Hydrate selected records after process restarts or session restoration."""
    from app.database.repositories.job_repository import JobRepository
    from app.database.repositories.resume_repository import ResumeRepository
    from app.database.session import get_session
    from app.domain.resume import ResumeData

    resume_id = session.get("resume_id")
    job_id = session.get("job_id")
    if (resume_id and session.get("resume") is None) or (job_id and not session.get("job_text")):
        try:
            with get_session() as db_session:
                if resume_id and session.get("resume") is None:
                    row = ResumeRepository(db_session).get_by_id(int(resume_id))
                    if row is not None:
                        session["resume"] = ResumeData.model_validate_json(row.data_json)
                        session["resume_name"] = row.name or "Untitled"
                        session["resume_text"] = row.raw_text or ""
                if job_id and not session.get("job_text"):
                    row = JobRepository(db_session).get_by_id(int(job_id))
                    if row is not None:
                        session.update({
                            "job_title": row.title or "",
                            "job_text": row.content or "",
                            "job_company": row.company or "",
                            "job_location": row.location or "",
                            "job_source_url": row.source_url or "",
                            "job_employment_type": row.employment_type or "",
                            "job_salary": row.salary or "",
                            "job_date_posted": row.date_posted or "",
                            "job_status": row.status or "saved",
                        })
        except Exception:
            logger.warning("Could not hydrate selected workflow records", exc_info=True)


def _get_session(request: Request) -> dict[str, Any]:
    sid = getattr(request.state, "resume_optimizer_sid", None)
    if not sid:
        sid = request.cookies.get(SESSION_COOKIE) or _new_session_id()
        request.state.resume_optimizer_sid = sid
    if sid not in _sessions:
        _sessions[sid] = _load_persisted_session(sid)
    session = _sessions.setdefault(sid, {})
    _ensure_workflow_objects(session)
    _session_seen[sid] = time.time()
    return session


def _workflow_context(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "workflow_has_resume": session.get("resume") is not None,
        "workflow_has_job": bool(session.get("job_text")),
        "workflow_has_ats": session.get("ats_result") is not None,
        "workflow_has_optimized": session.get("optimized_resume") is not None,
        "workflow_resume_name": session.get("resume_name", ""),
        "workflow_job_title": session.get("job_title", ""),
        "workflow_has_resignation": bool(session.get("resignation_letter")),
    }


def _render(
    request: Request,
    name: str,
    context: dict[str, Any] | None = None,
    *,
    status_code: int = 200,
) -> HTMLResponse:
    session = _get_session(request)
    ctx: dict[str, Any] = {"request": request}
    ctx.update(_workflow_context(session))
    if context:
        ctx.update(context)
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


def _redirect(path: str, status_code: int = 303) -> RedirectResponse:
    return RedirectResponse(path, status_code=status_code)


def _set_error(session: dict[str, Any], message: str) -> None:
    session["error_message"] = message


def _pop_error(session: dict[str, Any]) -> str:
    return str(session.pop("error_message", ""))


def _safe_filename(value: str, fallback: str = "resume") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return cleaned or fallback


def _bounded_text(value: str, limit: int) -> str:
    return (value or "").strip()[:limit]


def _safe_external_url(value: str) -> str:
    """Keep optional job links limited to normal HTTP(S) URLs."""
    from urllib.parse import urlparse

    cleaned = _bounded_text(value, 2_000)
    if not cleaned:
        return ""
    try:
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""
    except ValueError:
        return ""
    return cleaned


def _default_resignation_form(session: dict[str, Any]) -> dict[str, Any]:
    """Build a safe default form, using selected resume contact details when available."""
    saved = session.get("resignation_form")
    if isinstance(saved, dict):
        return dict(saved)

    contact = None
    resume = session.get("resume")
    if resume is not None:
        contact = getattr(resume, "contact", None)
    return {
        "employee_name": getattr(contact, "name", "") if contact else "",
        "employee_address": getattr(contact, "location", "") if contact else "",
        "employee_email": getattr(contact, "email", "") if contact else "",
        "employee_phone": getattr(contact, "phone", "") if contact else "",
        "letter_date": date.today().isoformat(),
        "manager_name": "",
        "manager_title": "",
        "company_name": "",
        "company_address": "",
        "position": "",
        "last_working_day": "",
        "notice_period": "",
        "tone": "formal",
        "reason": "none",
        "reason_details": "",
        "transition_support": True,
        "appreciation_note": "",
        "language": "en",
        "resignation_type": "standard",
        "include_leave_balance": False,
        "include_property_return": False,
    }


def _text_export_response(text: str, filename_stem: str, file_format: str) -> Response:
    """Return an in-memory TXT, DOCX, or PDF download for editable letter text."""
    file_format = file_format.lower()
    safe_stem = _safe_filename(filename_stem, "resignation-letter")
    if file_format == "txt":
        return PlainTextResponse(
            text.rstrip() + "\n",
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_stem}.txt"'},
        )
    if file_format not in {"docx", "pdf"}:
        return PlainTextResponse("Unsupported export format.", status_code=400)

    from app.exports.exporter import export_text_docx, export_text_pdf

    suffix = f".{file_format}"
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
        if file_format == "docx":
            export_text_docx(text, tmp_path)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            export_text_pdf(text, tmp_path)
            media_type = "application/pdf"
        content = Path(tmp_path).read_bytes()
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{safe_stem}{suffix}"'},
        )
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


def _resume_to_markdown(resume: Any) -> str:
    """Render ResumeData into a readable, exportable Markdown document."""
    lines: list[str] = []
    contact = resume.contact
    lines.append(f"# {contact.name or 'Untitled Resume'}")
    if resume.headline:
        lines.append(resume.headline)
    contact_line = " | ".join(
        value for value in [contact.email, contact.phone, contact.location, contact.linkedin, contact.website] if value
    )
    if contact_line:
        lines.extend(["", contact_line])
    if resume.summary:
        lines.extend(["", "## Professional Summary", resume.summary])
    if resume.skills:
        lines.extend(["", "## Skills", ", ".join(resume.skills)])
    if resume.experience:
        lines.extend(["", "## Experience"])
        for item in resume.experience:
            title = " — ".join(value for value in [item.title, item.company] if value) or "Experience"
            dates = " – ".join(value for value in [item.start_date, item.end_date] if value)
            meta = " | ".join(value for value in [dates, item.location] if value)
            lines.extend(["", f"### {title}"])
            if meta:
                lines.append(meta)
            lines.extend(f"- {bullet}" for bullet in item.bullets if bullet)
    if resume.projects:
        lines.extend(["", "## Projects"])
        for item in resume.projects:
            lines.extend(["", f"### {item.title or 'Project'}"])
            meta = " | ".join(value for value in [item.meta, item.start_date, item.end_date] if value)
            if meta:
                lines.append(meta)
            if item.description:
                lines.append(item.description)
            lines.extend(f"- {bullet}" for bullet in item.bullets if bullet)
    if resume.education:
        lines.extend(["", "## Education"])
        for item in resume.education:
            heading = " — ".join(value for value in [item.degree, item.institution] if value) or "Education"
            meta = " | ".join(value for value in [item.year, item.location, item.cgpa] if value)
            lines.extend(["", f"### {heading}"])
            if meta:
                lines.append(meta)
    if resume.certifications:
        lines.extend(["", "## Certifications"])
        lines.extend(f"- {item}" for item in resume.certifications if item)
    if resume.languages:
        lines.extend(["", "## Languages", ", ".join(resume.languages)])
    return "\n".join(lines).strip() + "\n"


async def _read_uploaded_resume(file: UploadFile):
    from app.services.document_reader import extract_text
    from app.services.resume_parser import parse_resume

    filename = file.filename or "resume.txt"
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_RESUME_SUFFIXES:
        raise ValueError("Unsupported file type. Upload a PDF, DOCX, DOC, or TXT file.")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise ValueError("The selected file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("The file is larger than the 15 MB upload limit.")

    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        raw_text = extract_text(tmp_path)
        if not raw_text.strip():
            raise ValueError("No readable resume text was found in the file.")
        resume = parse_resume(raw_text)
        return resume, raw_text
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


# ── Page routes ──────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    from app.database.repositories.analysis_repository import AnalysisRepository
    from app.database.repositories.application_repository import ApplicationRepository
    from app.database.repositories.job_repository import JobRepository
    from app.database.repositories.resume_repository import ResumeRepository
    from app.database.repositories.web_repository import GeneratedDocumentRepository
    from app.database.session import get_session

    session = _get_session(request)
    with get_session() as db_session:
        resumes = ResumeRepository(db_session).get_all()
        jobs = JobRepository(db_session).get_all()
        recent_analyses = AnalysisRepository(db_session).get_recent(limit=6)
        recent_documents = GeneratedDocumentRepository(db_session).list_recent(limit=6)
        recent_applications = ApplicationRepository(db_session).list_detailed()[:6]

    active_result = session.get("ats_result")
    active_score = active_result.ats_score if active_result is not None else None
    optimized_score = session.get("optimized_score")
    if session.get("resume") is None:
        next_action = {"title": "Create or import your resume", "text": "Start with a structured resume employers can read.", "href": "/builder/", "label": "Open Resume Builder"}
    elif not session.get("job_text"):
        next_action = {"title": "Add your target job", "text": "Save the exact vacancy description for accurate matching.", "href": "/jobs", "label": "Add Job Description"}
    elif active_result is None:
        next_action = {"title": "Measure your ATS match", "text": "Run the deterministic analysis before using AI suggestions.", "href": "/ats", "label": "Run ATS Analysis"}
    elif session.get("optimized_resume") is None:
        next_action = {"title": "Review targeted improvements", "text": f"Your current ATS score is {active_score}/100.", "href": "/optimize", "label": "Open Optimization"}
    else:
        next_action = {"title": "Export and apply", "text": "Your optimized resume is ready for final review and export.", "href": "/optimize", "label": "Review Export"}

    return _render(
        request,
        "dashboard.html",
        {
            "page": "dashboard",
            "resumes": resumes,
            "jobs": jobs,
            "active_resume_id": session.get("resume_id"),
            "active_job_id": session.get("job_id"),
            "active_score": active_score,
            "optimized_score": optimized_score,
            "score_gain": (optimized_score - active_score) if isinstance(optimized_score, int) and isinstance(active_score, int) else None,
            "recent_analyses": recent_analyses,
            "recent_documents": recent_documents,
            "recent_applications": recent_applications,
            "next_action": next_action,
            "error_message": _pop_error(session),
        },
    )


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    from app.database.repositories.resume_repository import ResumeRepository
    from app.database.repositories.versioning_repository import VersioningRepository
    from app.database.session import get_session
    session = _get_session(request)
    with get_session() as db_session:
        resumes = ResumeRepository(db_session).get_all()
        versions = VersioningRepository(db_session).list_version_summaries(int(session["resume_id"])) if session.get("resume_id") else []
    return _render(
        request,
        "upload.html",
        {
            "page": "upload",
            "error_message": _pop_error(session),
            "resume_name": session.get("resume_name", ""),
            "resume_text": session.get("resume_text", ""),
            "resumes": resumes,
            "active_resume_id": session.get("resume_id"),
            "versions": versions,
        },
    )


@app.post("/upload")
async def upload_resume(request: Request, file: UploadFile = File(...)):
    session = _get_session(request)
    try:
        resume, raw_text = await _read_uploaded_resume(file)
        from app.database.repositories.resume_repository import ResumeRepository
        from app.database.session import get_session

        with get_session() as db_session:
            resume_id = ResumeRepository(db_session).save(
                name=file.filename or "Untitled",
                data_json=resume.model_dump_json(),
                raw_text=raw_text,
                source_type="import",
                source_filename=file.filename or "",
            )

        session.update(
            {
                "resume": resume,
                "resume_id": resume_id,
                "resume_name": file.filename or "Untitled",
                "resume_text": raw_text,
            }
        )
        # A new resume invalidates downstream workflow output.
        for key in (
            "ats_result", "analysis_id", "fact_guard", "opt_changes", "optimized_resume",
            "optimization_id", "optimized_score", "estimated_score", "cover_letter",
            "cover_warnings", "cover_letter_id",
        ):
            session.pop(key, None)
        return _redirect("/upload?imported=1")
    except ValueError as exc:
        _set_error(session, str(exc))
    except Exception:
        logger.exception("Resume upload failed")
        _set_error(session, "The resume could not be imported. Check the file and try again.")
    return _redirect("/upload?error=1")


@app.post("/resumes/{resume_id}/use")
async def use_resume(request: Request, resume_id: int):
    from app.database.repositories.resume_repository import ResumeRepository
    from app.database.session import get_session
    from app.schemas import ResumeData

    session = _get_session(request)
    with get_session() as db_session:
        row = ResumeRepository(db_session).get_by_id(resume_id)
        if row is None:
            _set_error(session, "The selected resume no longer exists.")
            return _redirect("/")
        try:
            resume = ResumeData.model_validate_json(row.data_json)
        except Exception:
            logger.exception("Stored resume %s could not be parsed", resume_id)
            _set_error(session, "The selected resume record is invalid and could not be loaded.")
            return _redirect("/")
        session.update(
            {
                "resume": resume,
                "resume_id": row.id,
                "resume_name": row.name or "Untitled",
                "resume_text": row.raw_text or "",
            }
        )
    for key in (
        "ats_result", "analysis_id", "fact_guard", "opt_changes", "optimized_resume",
        "optimization_id", "optimized_score", "estimated_score", "cover_letter",
        "cover_warnings", "cover_letter_id",
    ):
        session.pop(key, None)
    return _redirect("/?resume_loaded=1")


@app.get("/resumes/{resume_id}/edit")
async def edit_resume(resume_id: int):
    return _redirect(f"/builder/?resume_id={resume_id}", status_code=302)


@app.post("/resumes/{resume_id}/delete")
async def delete_resume(request: Request, resume_id: int):
    from app.database.repositories.resume_repository import ResumeRepository
    from app.database.session import get_session

    session = _get_session(request)
    with get_session() as db_session:
        deleted = ResumeRepository(db_session).delete(resume_id)
    if not deleted:
        _set_error(session, "The selected resume was already removed.")
    elif session.get("resume_id") == resume_id:
        for key in (
            "resume", "resume_id", "resume_name", "resume_text", "ats_result", "analysis_id",
            "fact_guard", "opt_changes", "optimized_resume", "optimization_id",
            "optimized_score", "estimated_score", "cover_letter", "cover_warnings", "cover_letter_id",
        ):
            session.pop(key, None)
    return _redirect("/?resume_deleted=1")


@app.post("/resumes/{resume_id}/versions/{version_id}/restore")
async def restore_resume_version(request: Request, resume_id: int, version_id: int):
    from app.database.repositories.resume_repository import ResumeRepository
    from app.database.repositories.versioning_repository import VersioningRepository
    from app.database.session import get_session
    from app.domain.resume import ResumeData

    session = _get_session(request)
    with get_session() as db_session:
        versions = VersioningRepository(db_session)
        version = versions.get_version(version_id)
        row = ResumeRepository(db_session).get_by_id(resume_id)
        if version is None or row is None or int(version.resume_id) != resume_id:
            _set_error(session, "The selected resume version could not be found.")
            return _redirect("/upload")
        restored = ResumeData.model_validate_json(version.data_json)
        ResumeRepository(db_session).update(
            resume_id,
            restored.model_dump_json(),
            name=row.name,
            raw_text=_resume_to_markdown(restored),
            source_type="restored",
        )
        versions.create_version(
            resume_id,
            restored.model_dump_json(),
            f"Restored version {version.version_number}",
        )
        resume_name = row.name
    session.update({
        "resume": restored,
        "resume_id": resume_id,
        "resume_name": resume_name,
        "resume_text": _resume_to_markdown(restored),
    })
    for key in (
        "ats_result", "analysis_id", "fact_guard", "opt_changes", "optimized_resume",
        "optimization_id", "optimized_score", "estimated_score",
    ):
        session.pop(key, None)
    return _redirect("/upload?restored=1")


@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request):
    from app.database.repositories.job_repository import JobRepository
    from app.database.session import get_session

    session = _get_session(request)
    with get_session() as db_session:
        jobs = JobRepository(db_session).get_all()
    return _render(
        request,
        "jobs.html",
        {
            "page": "jobs",
            "job_text": session.get("job_text", ""),
            "job_title": session.get("job_title", ""),
            "job_company": session.get("job_company", ""),
            "job_location": session.get("job_location", ""),
            "job_source_url": session.get("job_source_url", ""),
            "job_employment_type": session.get("job_employment_type", ""),
            "job_salary": session.get("job_salary", ""),
            "job_date_posted": session.get("job_date_posted", ""),
            "job_status": session.get("job_status", "saved"),
            "jobs": jobs,
            "active_job_id": session.get("job_id"),
            "error_message": _pop_error(session),
        },
    )


@app.post("/jobs")
async def save_job(
    request: Request,
    job_text: str = Form(...),
    job_title: str = Form(""),
    job_company: str = Form(""),
    job_location: str = Form(""),
    job_source_url: str = Form(""),
    job_employment_type: str = Form(""),
    job_salary: str = Form(""),
    job_date_posted: str = Form(""),
    job_status: str = Form("saved"),
):
    session = _get_session(request)
    job_text = _bounded_text(job_text, 80_000)
    if not job_text:
        _set_error(session, "Paste a job description before saving.")
        return _redirect("/jobs?error=1")

    metadata = {
        "job_title": _bounded_text(job_title, 255),
        "job_company": _bounded_text(job_company, 255),
        "job_location": _bounded_text(job_location, 255),
        "job_source_url": _safe_external_url(job_source_url),
        "job_employment_type": _bounded_text(job_employment_type, 100),
        "job_salary": _bounded_text(job_salary, 150),
        "job_date_posted": _bounded_text(job_date_posted, 40),
        "job_status": _bounded_text(job_status, 50) or "saved",
    }
    session.update({"job_text": job_text, **metadata})

    from app.database.repositories.job_repository import JobRepository
    from app.database.session import get_session

    with get_session() as db_session:
        job_id = JobRepository(db_session).save(
            title=metadata["job_title"] or "Untitled role",
            content=job_text,
            company=metadata["job_company"],
            location=metadata["job_location"],
            source_url=metadata["job_source_url"],
            employment_type=metadata["job_employment_type"],
            salary=metadata["job_salary"],
            date_posted=metadata["job_date_posted"],
            status=metadata["job_status"],
        )
        session["job_id"] = job_id

    for key in ("ats_result", "analysis_id", "fact_guard", "opt_changes", "optimized_resume", "optimization_id", "optimized_score", "cover_letter", "cover_warnings", "cover_letter_id"):
        session.pop(key, None)
    return _redirect("/jobs?saved=1")


@app.post("/jobs/{job_id}/use")
async def use_job(request: Request, job_id: int):
    from app.database.repositories.job_repository import JobRepository
    from app.database.session import get_session

    session = _get_session(request)
    with get_session() as db_session:
        row = JobRepository(db_session).get_by_id(job_id)
        if row is None:
            _set_error(session, "The selected job description no longer exists.")
            return _redirect("/jobs")
        session.update(
            {
                "job_id": row.id,
                "job_title": row.title or "",
                "job_text": row.content or "",
                "job_company": row.company or "",
                "job_location": row.location or "",
                "job_source_url": row.source_url or "",
                "job_employment_type": row.employment_type or "",
                "job_salary": row.salary or "",
                "job_date_posted": row.date_posted or "",
                "job_status": row.status or "saved",
            }
        )
    for key in ("ats_result", "analysis_id", "fact_guard", "opt_changes", "optimized_resume", "optimization_id", "optimized_score", "cover_letter", "cover_warnings", "cover_letter_id"):
        session.pop(key, None)
    return _redirect("/jobs?loaded=1")


@app.post("/jobs/{job_id}/delete")
async def delete_job(request: Request, job_id: int):
    from app.database.repositories.job_repository import JobRepository
    from app.database.session import get_session

    session = _get_session(request)
    with get_session() as db_session:
        deleted = JobRepository(db_session).delete(job_id)
    if not deleted:
        _set_error(session, "The selected job description was already removed.")
    elif session.get("job_id") == job_id:
        for key in (
            "job_id", "job_text", "job_title", "job_company", "job_location",
            "job_source_url", "job_employment_type", "job_salary", "job_date_posted",
            "job_status", "ats_result", "analysis_id", "fact_guard", "opt_changes",
            "optimized_resume", "optimization_id", "optimized_score", "estimated_score",
            "cover_letter", "cover_warnings", "cover_letter_id",
        ):
            session.pop(key, None)
    return _redirect("/jobs?deleted=1")


@app.get("/ats", response_class=HTMLResponse)
async def ats_page(request: Request):
    session = _get_session(request)
    return _render(
        request,
        "ats.html",
        {
            "page": "ats",
            "has_resume": session.get("resume") is not None,
            "has_job": bool(session.get("job_text")),
            "result": session.get("ats_result"),
            "error_message": _pop_error(session),
        },
    )


@app.post("/ats/run")
async def run_ats(request: Request):
    session = _get_session(request)
    resume = session.get("resume")
    job_text = session.get("job_text", "")
    resume_id = session.get("resume_id")
    job_id = session.get("job_id")
    if not resume or not job_text or not resume_id or not job_id:
        return _redirect("/ats?error=missing_input")
    try:
        from app.database.repositories.analysis_repository import AnalysisRepository
        from app.database.repositories.versioning_repository import VersioningRepository
        from app.database.session import get_session
        from app.services.ats_engine import analyze

        result = analyze(resume, job_text)
        with get_session() as db_session:
            analysis_id = AnalysisRepository(db_session).save(int(resume_id), int(job_id), result.to_dict())
            versions = VersioningRepository(db_session)
            latest = versions.get_latest_version(int(resume_id))
            if latest is None:
                version_id = versions.create_version(int(resume_id), resume.model_dump_json(), "ATS baseline")
            else:
                version_id = latest.id
            versions.create_targeting_session(
                version_id,
                int(job_id),
                json.dumps(result.keyword_weights, ensure_ascii=False),
                json.dumps(result.to_dict(), ensure_ascii=False, default=str),
            )
        session["ats_result"] = result
        session["analysis_id"] = analysis_id
        session["original_score"] = result.ats_score
        for key in ("fact_guard", "opt_changes", "optimized_resume", "optimization_id", "optimized_score"):
            session.pop(key, None)
        return _redirect("/ats?done=1")
    except Exception:
        logger.exception("ATS analysis failed")
        _set_error(session, "ATS analysis failed. Review the resume and job description, then try again.")
        return _redirect("/ats?error=run_failed")


@app.get("/optimize", response_class=HTMLResponse)
async def optimize_page(request: Request):
    session = _get_session(request)
    return _render(
        request,
        "optimize.html",
        {
            "page": "optimize",
            "has_resume": session.get("resume") is not None,
            "has_job": bool(session.get("job_text")),
            "has_ats": session.get("ats_result") is not None,
            "changes": session.get("opt_changes", []),
            "original_score": session.get("original_score") or (session.get("ats_result").ats_score if session.get("ats_result") else None),
            "estimated_score": session.get("estimated_score"),
            "optimized_score": session.get("optimized_score"),
            "optimized_markdown": (
                _resume_to_markdown(session["optimized_resume"])
                if session.get("optimized_resume") is not None
                else ""
            ),
            "error_message": _pop_error(session),
        },
    )


@app.post("/optimize/run")
async def run_optimize(request: Request):
    session = _get_session(request)
    resume = session.get("resume")
    job_text = session.get("job_text", "")
    ats = session.get("ats_result")
    resume_id = session.get("resume_id")
    job_id = session.get("job_id")
    if not resume or not job_text or not ats or not resume_id or not job_id:
        return _redirect("/optimize?error=missing_input")

    try:
        from app.ai.ollama_client import OllamaClient
        from app.core.settings import settings_service
        from app.database.repositories.optimization_repository import OptimizationRepository
        from app.database.session import get_session
        from app.services.ats_engine import analyze
        from app.services.optimizer import apply_accepted_changes, optimize_resume

        client = OllamaClient(base_url=settings_service.ollama_url, model=settings_service.model)
        base_resume, fact_guard = optimize_resume(resume, job_text, ats, client)
        changes: list[dict[str, Any]] = []
        for index, change in enumerate(fact_guard.safe_changes):
            item = change.model_dump(mode="json")
            item.update({"index": index, "flagged": False})
            changes.append(item)
        offset = len(changes)
        for local_index, change in enumerate(fact_guard.flagged_changes):
            item = change.model_dump(mode="json")
            item.update({"index": offset + local_index, "flagged": True})
            changes.append(item)

        estimate_guard = fact_guard.model_copy(deep=True)
        for change in estimate_guard.safe_changes:
            change.accepted = True
        for change in estimate_guard.flagged_changes:
            change.accepted = False
        estimated_resume = apply_accepted_changes(resume, estimate_guard)
        estimated_score = analyze(estimated_resume, job_text).ats_score

        with get_session() as db_session:
            optimization_id = OptimizationRepository(db_session).save(
                int(resume_id),
                int(job_id),
                settings_service.model,
                base_resume.model_dump_json(),
                fact_guard_json=fact_guard.model_dump_json(),
                original_score=ats.ats_score,
                optimized_score=estimated_score,
            )

        session["optimized_resume"] = base_resume
        session["fact_guard"] = fact_guard
        session["opt_changes"] = changes
        session["optimization_id"] = optimization_id
        session["estimated_score"] = estimated_score
        return _redirect("/optimize?done=1")
    except Exception as exc:
        logger.exception("Resume optimization failed")
        message = str(exc).lower()
        if "connection" in message or "ollama" in message or "timed out" in message:
            _set_error(session, "Ollama is unavailable or timed out. Verify the URL and model in Settings, then try again.")
        else:
            _set_error(session, "Optimization failed. Check the AI model and try again.")
        return _redirect("/optimize?error=run_failed")


@app.post("/optimize/apply")
async def apply_optimization_changes(
    request: Request,
    accepted_indexes: list[int] = Form(default=[]),
):
    session = _get_session(request)
    fact_guard = session.get("fact_guard")
    resume = session.get("resume")
    resume_id = session.get("resume_id")
    optimization_id = session.get("optimization_id")
    if fact_guard is None or resume is None or not resume_id:
        return _redirect("/optimize?error=no_changes")

    accepted = set(accepted_indexes)
    for index, change in enumerate(fact_guard.all_changes):
        change.accepted = index in accepted

    from app.database.repositories.optimization_repository import OptimizationRepository
    from app.database.repositories.resume_repository import ResumeRepository
    from app.database.repositories.versioning_repository import VersioningRepository
    from app.database.session import get_session
    from app.services.ats_engine import analyze
    from app.services.optimizer import apply_accepted_changes

    optimized = apply_accepted_changes(resume, fact_guard)
    optimized_score = analyze(optimized, session.get("job_text", "")).ats_score
    with get_session() as db_session:
        versions = VersioningRepository(db_session)
        versions.create_version(int(resume_id), optimized.model_dump_json(), f"Applied {len(accepted)} optimization change(s)")
        ResumeRepository(db_session).update(
            int(resume_id),
            optimized.model_dump_json(),
            name=session.get("resume_name") or optimized.contact.name or "Resume",
            source_type="builder",
        )
        if optimization_id:
            OptimizationRepository(db_session).update_review(
                int(optimization_id),
                optimized_json=optimized.model_dump_json(),
                fact_guard_json=fact_guard.model_dump_json(),
                accepted_changes=sorted(accepted),
                optimized_score=optimized_score,
            )

    session["optimized_resume"] = optimized
    session["resume"] = optimized
    session["fact_guard"] = fact_guard
    session["optimized_score"] = optimized_score
    for item in session.get("opt_changes", []):
        item["accepted"] = item.get("index") in accepted
    return _redirect("/optimize?applied=1")


@app.get("/optimize/download")
async def download_optimized_resume_legacy(request: Request):
    return await download_optimized_resume(request, "md")


@app.get("/optimize/download/{file_format}")
async def download_optimized_resume(request: Request, file_format: str):
    session = _get_session(request)
    resume = session.get("optimized_resume") or session.get("resume")
    if resume is None:
        return _redirect("/optimize?error=no_optimized_resume", status_code=302)
    file_format = file_format.lower()
    if file_format not in {"md", "txt", "docx", "pdf", "json"}:
        raise HTTPException(status_code=404, detail="Unsupported export format")
    stem = str(Path(_safe_filename(session.get("resume_name", "resume"), "resume")).with_suffix("")) + "-optimized"
    if file_format == "md":
        return PlainTextResponse(_resume_to_markdown(resume), media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{stem}.md"'})
    if file_format == "txt":
        return PlainTextResponse(_resume_to_markdown(resume).replace("#", "").strip() + "\n", media_type="text/plain; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{stem}.txt"'})
    if file_format == "json":
        return Response(resume.model_dump_json(indent=2), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{stem}.json"'})

    from app.exports.exporter import export_docx, export_pdf
    suffix = f".{file_format}"
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
        if file_format == "docx":
            export_docx(resume, tmp_path)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            export_pdf(resume, tmp_path)
            media_type = "application/pdf"
        return Response(Path(tmp_path).read_bytes(), media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{stem}{suffix}"'})
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


@app.get("/cover-letter", response_class=HTMLResponse)
async def cover_letter_page(request: Request):
    from app.database.repositories.web_repository import GeneratedDocumentRepository
    from app.database.session import get_session

    session = _get_session(request)
    with get_session() as db_session:
        history = GeneratedDocumentRepository(db_session).list_recent("cover_letter", limit=8)
    return _render(
        request,
        "cover_letter.html",
        {
            "page": "cover_letter",
            "has_resume": session.get("resume") is not None,
            "has_job": bool(session.get("job_text")),
            "letter": session.get("cover_letter", ""),
            "warnings": session.get("cover_warnings", []),
            "history": history,
            "error_message": _pop_error(session),
        },
    )


@app.post("/cover-letter/run")
async def run_cover_letter(request: Request):
    session = _get_session(request)
    resume = session.get("resume")
    job_text = session.get("job_text", "")
    resume_id = session.get("resume_id")
    job_id = session.get("job_id")
    if not resume or not job_text or not resume_id or not job_id:
        return _redirect("/cover-letter?error=missing_input")

    try:
        from app.ai.ollama_client import OllamaClient
        from app.core.settings import settings_service
        from app.database.repositories.cover_letter_repository import CoverLetterRepository
        from app.database.repositories.web_repository import GeneratedDocumentRepository
        from app.database.session import get_session
        from app.services.cover_letter import generate_cover_letter

        client = OllamaClient(base_url=settings_service.ollama_url, model=settings_service.model)
        result = generate_cover_letter(
            resume,
            job_text,
            client,
            target_company=session.get("job_company"),
            job_title=session.get("job_title"),
        )
        title = f"Cover Letter — {session.get('job_title') or 'Target Role'}"
        with get_session() as db_session:
            cover_letter_id = CoverLetterRepository(db_session).create(int(resume_id), int(job_id), result.text, settings_service.model)
            document_id = GeneratedDocumentRepository(db_session).save(
                "cover_letter",
                title,
                result.text,
                resume_id=int(resume_id),
                job_id=int(job_id),
                metadata={"company": session.get("job_company", ""), "job_title": session.get("job_title", ""), "model": settings_service.model},
            )
        session["cover_letter"] = result.text
        session["cover_warnings"] = list(result.warnings)
        session["cover_letter_id"] = cover_letter_id
        session["cover_document_id"] = document_id
        return _redirect("/cover-letter?done=1")
    except Exception as exc:
        logger.exception("Cover letter generation failed")
        message = str(exc).lower()
        if "connection" in message or "ollama" in message or "timed out" in message:
            _set_error(session, "Ollama is unavailable or timed out. Verify the URL and model in Settings, then try again.")
        else:
            _set_error(session, "Cover letter generation failed. Check the AI model and try again.")
        return _redirect("/cover-letter?error=run_failed")


@app.post("/cover-letter/save")
async def save_cover_letter(request: Request, letter_text: str = Form("")):
    session = _get_session(request)
    text = _bounded_text(letter_text, 30_000)
    if not text:
        _set_error(session, "The cover letter is empty.")
        return _redirect("/cover-letter?error=empty")

    from app.database.repositories.cover_letter_repository import CoverLetterRepository
    from app.database.repositories.web_repository import GeneratedDocumentRepository
    from app.database.session import get_session

    with get_session() as db_session:
        cover_id = session.get("cover_letter_id")
        if cover_id:
            CoverLetterRepository(db_session).update(int(cover_id), text)
        document_id = GeneratedDocumentRepository(db_session).save(
            "cover_letter",
            f"Cover Letter — {session.get('job_title') or 'Target Role'}",
            text,
            resume_id=session.get("resume_id"),
            job_id=session.get("job_id"),
            metadata={"company": session.get("job_company", ""), "job_title": session.get("job_title", "")},
            document_id=session.get("cover_document_id"),
        )
        session["cover_document_id"] = document_id
    session["cover_letter"] = text
    return _redirect("/cover-letter?saved=1")


@app.get("/cover-letter/download")
async def download_cover_letter_legacy(request: Request):
    session = _get_session(request)
    text = str(session.get("cover_letter", "")).strip()
    if not text:
        return _redirect("/cover-letter?error=no_letter", status_code=302)
    company = _safe_filename(session.get("job_company", "company"), "company")
    return _text_export_response(text, f"cover-letter-{company}", "txt")


@app.post("/cover-letter/download/{file_format}")
async def download_cover_letter(request: Request, file_format: str, letter_text: str = Form("")):
    session = _get_session(request)
    text = _bounded_text(letter_text, 30_000)
    if not text:
        _set_error(session, "The cover letter is empty.")
        return _redirect("/cover-letter?error=no_letter")
    session["cover_letter"] = text
    company = _safe_filename(session.get("job_company", "company"), "company")
    return _text_export_response(text, f"cover-letter-{company}", file_format)


@app.post("/cover-letter/load/{document_id}")
async def load_cover_letter(request: Request, document_id: int):
    from app.database.repositories.web_repository import GeneratedDocumentRepository
    from app.database.session import get_session
    session = _get_session(request)
    with get_session() as db_session:
        row = GeneratedDocumentRepository(db_session).get(document_id)
        if row is None or row.document_type != "cover_letter":
            _set_error(session, "The saved cover letter could not be found.")
            return _redirect("/cover-letter")
        session["cover_letter"] = row.content
        session["cover_document_id"] = row.id
    return _redirect("/cover-letter?loaded=1")


@app.post("/cover-letter/clear")
async def clear_cover_letter(request: Request):
    session = _get_session(request)
    for key in ("cover_letter", "cover_warnings", "cover_letter_id", "cover_document_id"):
        session.pop(key, None)
    return _redirect("/cover-letter?cleared=1")


@app.get("/resignation-letter", response_class=HTMLResponse)
async def resignation_letter_page(request: Request):
    from app.database.repositories.web_repository import GeneratedDocumentRepository
    from app.database.session import get_session
    session = _get_session(request)
    with get_session() as db_session:
        history = GeneratedDocumentRepository(db_session).list_recent("resignation_letter", limit=8)
    return _render(
        request,
        "resignation_letter.html",
        {
            "page": "resignation_letter",
            "form_data": _default_resignation_form(session),
            "letter": session.get("resignation_letter", ""),
            "notice_warning": session.get("resignation_notice_warning", ""),
            "history": history,
            "error_message": _pop_error(session),
        },
    )


@app.post("/resignation-letter/generate")
async def generate_resignation_letter_page(
    request: Request,
    employee_name: str = Form(""),
    employee_address: str = Form(""),
    employee_email: str = Form(""),
    employee_phone: str = Form(""),
    letter_date: str = Form(""),
    manager_name: str = Form(""),
    manager_title: str = Form(""),
    company_name: str = Form(""),
    company_address: str = Form(""),
    position: str = Form(""),
    last_working_day: str = Form(""),
    notice_period: str = Form(""),
    tone: str = Form("formal"),
    reason: str = Form("none"),
    reason_details: str = Form(""),
    transition_support: bool = Form(False),
    appreciation_note: str = Form(""),
    language: str = Form("en"),
    resignation_type: str = Form("standard"),
    include_leave_balance: bool = Form(False),
    include_property_return: bool = Form(False),
):
    from app.database.repositories.web_repository import GeneratedDocumentRepository
    from app.database.session import get_session
    from app.services.resignation_letter import (
        ResignationLetterInput,
        generate_resignation_letter,
        notice_period_warning,
        validate_resignation_input,
    )

    session = _get_session(request)
    form_data = {
        "employee_name": _bounded_text(employee_name, 160),
        "employee_address": _bounded_text(employee_address, 800),
        "employee_email": _bounded_text(employee_email, 200),
        "employee_phone": _bounded_text(employee_phone, 80),
        "letter_date": _bounded_text(letter_date, 40),
        "manager_name": _bounded_text(manager_name, 160),
        "manager_title": _bounded_text(manager_title, 160),
        "company_name": _bounded_text(company_name, 200),
        "company_address": _bounded_text(company_address, 800),
        "position": _bounded_text(position, 200),
        "last_working_day": _bounded_text(last_working_day, 40),
        "notice_period": _bounded_text(notice_period, 100),
        "tone": _bounded_text(tone, 40),
        "reason": _bounded_text(reason, 40),
        "reason_details": _bounded_text(reason_details, 500),
        "transition_support": bool(transition_support),
        "appreciation_note": _bounded_text(appreciation_note, 700),
        "language": _bounded_text(language, 10),
        "resignation_type": _bounded_text(resignation_type, 40),
        "include_leave_balance": bool(include_leave_balance),
        "include_property_return": bool(include_property_return),
    }
    session["resignation_form"] = form_data
    payload = ResignationLetterInput(**form_data)
    errors = validate_resignation_input(payload)
    if errors:
        _set_error(session, " ".join(errors))
        return _redirect("/resignation-letter?error=validation")

    letter = generate_resignation_letter(payload)
    warning = notice_period_warning(payload)
    title = f"Resignation Letter — {form_data['company_name']}"
    with get_session() as db_session:
        document_id = GeneratedDocumentRepository(db_session).save(
            "resignation_letter",
            title,
            letter,
            resume_id=session.get("resume_id"),
            metadata=form_data,
        )
    session["resignation_letter"] = letter
    session["resignation_document_id"] = document_id
    session["resignation_notice_warning"] = warning
    return _redirect("/resignation-letter?generated=1")


@app.post("/resignation-letter/save")
async def save_resignation_letter(request: Request, letter_text: str = Form("")):
    session = _get_session(request)
    letter_text = letter_text.strip()
    if len(letter_text) > 20_000:
        _set_error(session, "The resignation letter is too long. Keep it under 20,000 characters.")
        return _redirect("/resignation-letter?error=too_long")
    if not letter_text:
        _set_error(session, "The resignation letter is empty. Generate or enter text before saving.")
        return _redirect("/resignation-letter?error=empty")
    session["resignation_letter"] = letter_text + "\n"
    return _redirect("/resignation-letter?saved=1")


@app.post("/resignation-letter/download/{file_format}")
async def download_resignation_letter(
    request: Request,
    file_format: str,
    letter_text: str = Form(""),
):
    session = _get_session(request)
    letter_text = letter_text.strip()
    if len(letter_text) > 20_000:
        _set_error(session, "The resignation letter is too long. Keep it under 20,000 characters.")
        return _redirect("/resignation-letter?error=too_long")
    if not letter_text:
        _set_error(session, "The resignation letter is empty. Generate a draft before downloading.")
        return _redirect("/resignation-letter?error=empty")
    session["resignation_letter"] = letter_text + "\n"
    employee = str(_default_resignation_form(session).get("employee_name", "")).strip()
    stem = f"resignation-letter-{employee}" if employee else "resignation-letter"
    return _text_export_response(letter_text, stem, file_format)


@app.post("/resignation-letter/load/{document_id}")
async def load_resignation_letter(request: Request, document_id: int):
    from app.database.repositories.web_repository import GeneratedDocumentRepository
    from app.database.session import get_session
    session = _get_session(request)
    with get_session() as db_session:
        row = GeneratedDocumentRepository(db_session).get(document_id)
        if row is None or row.document_type != "resignation_letter":
            _set_error(session, "The saved resignation letter could not be found.")
            return _redirect("/resignation-letter")
        session["resignation_letter"] = row.content
        session["resignation_document_id"] = row.id
        try:
            metadata = json.loads(row.metadata_json or "{}")
            if isinstance(metadata, dict):
                session["resignation_form"] = metadata
        except ValueError:
            pass
    return _redirect("/resignation-letter?loaded=1")


@app.post("/resignation-letter/clear")
async def clear_resignation_letter(request: Request):
    session = _get_session(request)
    session.pop("resignation_letter", None)
    session.pop("resignation_form", None)
    session.pop("resignation_document_id", None)
    session.pop("resignation_notice_warning", None)
    return _redirect("/resignation-letter?cleared=1")


@app.get("/applications", response_class=HTMLResponse)
async def applications_page(request: Request):
    from app.database.repositories.application_repository import ApplicationRepository, VALID_STATUSES
    from app.database.session import get_session

    session = _get_session(request)
    with get_session() as db_session:
        applications = ApplicationRepository(db_session).list_detailed()
    return _render(
        request,
        "applications.html",
        {
            "page": "applications",
            "applications": applications,
            "statuses": VALID_STATUSES,
            "error_message": _pop_error(session),
        },
    )


@app.post("/applications/create")
async def create_application(request: Request, status: str = Form("draft"), notes: str = Form("")):
    from app.database.repositories.application_repository import ApplicationRepository, VALID_STATUSES
    from app.database.session import get_session

    session = _get_session(request)
    resume_id = session.get("resume_id")
    job_id = session.get("job_id")
    if not resume_id or not job_id:
        _set_error(session, "Select both a resume and target job before adding an application.")
        return _redirect("/applications?error=selection")
    if status not in VALID_STATUSES:
        _set_error(session, "Select a valid application status.")
        return _redirect("/applications?error=status")
    with get_session() as db_session:
        ApplicationRepository(db_session).create(
            int(resume_id), int(job_id), status=status, notes=_bounded_text(notes, 4_000)
        )
    return _redirect("/applications?created=1")


@app.post("/applications/{application_id}/update")
async def update_application(
    request: Request,
    application_id: int,
    status: str = Form("draft"),
    notes: str = Form(""),
):
    from app.database.repositories.application_repository import ApplicationRepository, VALID_STATUSES
    from app.database.session import get_session

    session = _get_session(request)
    if status not in VALID_STATUSES:
        _set_error(session, "Select a valid application status.")
        return _redirect("/applications?error=status")
    with get_session() as db_session:
        if not ApplicationRepository(db_session).update(
            application_id, status=status, notes=_bounded_text(notes, 4_000)
        ):
            _set_error(session, "The selected application no longer exists.")
    return _redirect("/applications?updated=1")


@app.post("/applications/{application_id}/delete")
async def delete_application(request: Request, application_id: int):
    from app.database.repositories.application_repository import ApplicationRepository
    from app.database.session import get_session

    session = _get_session(request)
    with get_session() as db_session:
        if not ApplicationRepository(db_session).delete(application_id):
            _set_error(session, "The selected application was already removed.")
    return _redirect("/applications?deleted=1")


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    from app.core.settings import settings_service

    status = await _ollama_status_payload()
    available_models = list(status["models"])
    if settings_service.model and settings_service.model not in available_models:
        available_models.insert(0, settings_service.model)
    session = _get_session(request)
    return _render(
        request,
        "settings.html",
        {
            "page": "settings",
            "ollama_url": settings_service.ollama_url,
            "model": settings_service.model,
            "temperature": settings_service.temperature,
            "available_models": available_models,
            "ollama_connected": status["connected"],
            "error_message": _pop_error(session),
        },
    )


@app.post("/settings")
async def save_settings(
    request: Request,
    ollama_url: str = Form("http://localhost:11434"),
    model: str = Form("qwen3"),
    temperature: float = Form(0.3),
):
    from app.core.settings import settings_service

    session = _get_session(request)
    ollama_url = ollama_url.strip().rstrip("/")
    model = model.strip()
    if not _is_allowed_ollama_url(ollama_url):
        _set_error(session, "Use a localhost or private-network Ollama URL beginning with http:// or https://.")
        return _redirect("/settings?error=1")
    if not model:
        _set_error(session, "Enter an Ollama model name.")
        return _redirect("/settings?error=1")
    temperature = max(0.0, min(1.0, temperature))

    patched = settings_service.settings.model_copy(deep=True)
    patched.ai.ollama_url = ollama_url
    patched.ai.model = model
    patched.ai.temperature = temperature
    settings_service.save(patched)
    return _redirect("/settings?saved=1")


# ── API routes ───────────────────────────────────────────────────────────────


@app.get("/api/resumes")
async def api_resumes():
    from app.database.repositories.resume_repository import ResumeRepository
    from app.database.session import get_session

    with get_session() as session:
        return ResumeRepository(session).get_all()


@app.get("/api/jobs")
async def api_jobs():
    from app.database.repositories.job_repository import JobRepository
    from app.database.session import get_session

    with get_session() as session:
        return JobRepository(session).get_all()


@app.get("/api/session")
async def api_session(request: Request):
    session = _get_session(request)
    return {
        "has_resume": session.get("resume") is not None,
        "has_job": bool(session.get("job_text")),
        "has_ats": session.get("ats_result") is not None,
        "has_optimized": session.get("optimized_resume") is not None,
        "has_resignation_letter": bool(session.get("resignation_letter")),
        "resume_name": session.get("resume_name", ""),
        "job_title": session.get("job_title", ""),
    }


@app.post("/api/upload-resume")
async def api_upload_resume(file: UploadFile = File(...)):
    try:
        resume, _ = await _read_uploaded_resume(file)
        data = resume.model_dump(mode="json")
        data["source_filename"] = file.filename or ""
        return JSONResponse(data)
    except ValueError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)
    except Exception:
        logger.exception("Builder resume upload failed")
        return JSONResponse(
            {"detail": "The resume could not be imported. Check the file and try again."},
            status_code=500,
        )


def _is_allowed_ollama_url(value: str) -> bool:
    """Permit loopback and private-network Ollama endpoints only."""
    import ipaddress
    import socket
    from urllib.parse import urlparse

    try:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        host = parsed.hostname.casefold()
        if host in {"localhost", "127.0.0.1", "::1"}:
            return True
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or 11434, type=socket.SOCK_STREAM)}
        return bool(addresses) and all(ipaddress.ip_address(address).is_private or ipaddress.ip_address(address).is_loopback for address in addresses)
    except Exception:
        return False


async def _test_ollama_payload(url: str, model: str = "") -> dict[str, Any]:
    import requests as requests_module

    clean_url = url.strip().rstrip("/")
    if not _is_allowed_ollama_url(clean_url):
        return {"connected": False, "model_available": False, "models": [], "url": clean_url, "error": "Only localhost or private-network Ollama endpoints are allowed."}
    try:
        response = requests_module.get(f"{clean_url}/api/tags", timeout=4)
        response.raise_for_status()
        models = [item.get("name", "") for item in response.json().get("models", []) if item.get("name")]
        normalized = {item.split(":", 1)[0] for item in models} | set(models)
        model_available = not model or model in normalized or model.split(":", 1)[0] in normalized
        return {
            "connected": True,
            "model_available": model_available,
            "models": models,
            "url": clean_url,
            "error": "" if model_available else f"Ollama is reachable, but model '{model}' was not found.",
        }
    except requests_module.Timeout:
        return {"connected": False, "model_available": False, "models": [], "url": clean_url, "error": "The Ollama connection timed out."}
    except Exception as exc:
        return {"connected": False, "model_available": False, "models": [], "url": clean_url, "error": f"Ollama is not reachable: {type(exc).__name__}."}


@app.get("/api/resumes/{resume_id}")
async def api_resume_detail(resume_id: int):
    from app.database.repositories.resume_repository import ResumeRepository
    from app.database.session import get_session
    with get_session() as db_session:
        row = ResumeRepository(db_session).get_by_id(resume_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Resume not found")
        return JSONResponse({"id": row.id, "name": row.name, "data": json.loads(row.data_json), "source_type": row.source_type, "source_filename": row.source_filename})


@app.put("/api/resumes/{resume_id}")
async def api_update_resume(request: Request, resume_id: int):
    from app.database.repositories.resume_repository import ResumeRepository
    from app.database.repositories.versioning_repository import VersioningRepository
    from app.database.session import get_session
    from app.domain.resume import ResumeData
    payload = await request.json()
    resume = ResumeData.model_validate(payload.get("data", payload))
    name = _bounded_text(str(payload.get("name") or resume.contact.name or "Resume"), 255)
    with get_session() as db_session:
        repo = ResumeRepository(db_session)
        if not repo.update(resume_id, resume.model_dump_json(), name=name, source_type="builder"):
            raise HTTPException(status_code=404, detail="Resume not found")
        VersioningRepository(db_session).create_version(resume_id, resume.model_dump_json(), "Edited in web builder")
    session = _get_session(request)
    session.update({"resume": resume, "resume_id": resume_id, "resume_name": name, "resume_text": _resume_to_markdown(resume)})
    return {"id": resume_id, "name": name, "saved": True}


@app.get("/api/builder/state")
async def api_builder_state(request: Request, resume_id: int | None = None):
    from app.database.repositories.resume_repository import ResumeRepository
    from app.database.session import get_session
    from app.domain.resume import ResumeData
    from app.services.web_resume_adapter import resume_to_builder

    session = _get_session(request)
    target_id = resume_id or session.get("resume_id")
    if not target_id:
        return {"resumeId": None}
    with get_session() as db_session:
        row = ResumeRepository(db_session).get_by_id(int(target_id))
        if row is None:
            raise HTTPException(status_code=404, detail="Resume not found")
        resume_id_value = int(row.id)
        resume_name = row.name or "Untitled"
        resume_raw_text = row.raw_text or ""
        resume = ResumeData.model_validate_json(row.data_json)
    session.update({"resume": resume, "resume_id": resume_id_value, "resume_name": resume_name, "resume_text": resume_raw_text or _resume_to_markdown(resume)})
    return resume_to_builder(resume, resume_id=resume_id_value)


@app.put("/api/builder/state")
async def api_save_builder_state(request: Request):
    from app.database.repositories.resume_repository import ResumeRepository
    from app.database.repositories.versioning_repository import VersioningRepository
    from app.database.session import get_session
    from app.services.web_resume_adapter import builder_to_resume

    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid builder data")
    create_version = bool(payload.pop("_createVersion", False))
    resume = builder_to_resume(payload)
    if not resume.contact.name and not resume.summary and not resume.experience and not resume.education:
        raise HTTPException(status_code=400, detail="Add at least a name, summary, experience, or education before saving.")
    year = _bounded_text(str(payload.get("year", "")), 10)
    name = _bounded_text(resume.contact.name or f"Resume {year}" or "Resume", 255)
    requested_id = payload.get("resumeId")
    session = _get_session(request)
    with get_session() as db_session:
        repo = ResumeRepository(db_session)
        row = repo.get_by_id(int(requested_id)) if requested_id else None
        if row is not None:
            resume_id = int(row.id)
            changed = row.data_json != resume.model_dump_json() or row.name != name
            if changed:
                repo.update(resume_id, resume.model_dump_json(), name=name, raw_text=_resume_to_markdown(resume), source_type="builder")
        else:
            changed = True
            resume_id = repo.save(name=name, data_json=resume.model_dump_json(), raw_text=_resume_to_markdown(resume), source_type="builder", source_filename="web-builder")
        if create_version or row is None:
            VersioningRepository(db_session).create_version(resume_id, resume.model_dump_json(), "Saved from web builder")
    session.update({"resume": resume, "resume_id": resume_id, "resume_name": name, "resume_text": _resume_to_markdown(resume)})
    for key in ("ats_result", "analysis_id", "fact_guard", "opt_changes", "optimized_resume", "optimization_id", "optimized_score", "estimated_score"):
        session.pop(key, None)
    return {"id": resume_id, "name": name, "saved": True, "changed": changed, "next": "/jobs"}


@app.post("/api/builder/new")
async def api_new_builder_resume(request: Request):
    session = _get_session(request)
    for key in ("resume", "resume_id", "resume_name", "resume_text", "ats_result", "analysis_id", "fact_guard", "opt_changes", "optimized_resume", "optimization_id", "optimized_score", "estimated_score"):
        session.pop(key, None)
    return {"cleared": True}


async def _ollama_status_payload() -> dict[str, Any]:
    from app.core.settings import settings_service
    return await _test_ollama_payload(settings_service.ollama_url, settings_service.model)


@app.get("/api/ollama/status")
async def ollama_status():
    return await _ollama_status_payload()


@app.post("/api/ollama/test")
async def ollama_test(request: Request):
    payload = await request.json()
    url = str(payload.get("ollama_url", "")).strip()
    model = str(payload.get("model", "")).strip()
    if not url:
        return JSONResponse({"connected": False, "model_available": False, "models": [], "error": "Enter an Ollama URL."}, status_code=400)
    result = await _test_ollama_payload(url, model)
    return JSONResponse(result, status_code=200 if result["connected"] else 503)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_main:app", host="127.0.0.1", port=8000, reload=True)
