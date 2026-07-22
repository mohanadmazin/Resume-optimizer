"""Resume Optimizer — FastAPI web interface.

Run with either::

    python web_main.py
    uvicorn web_main:app --reload --port 8000

The web interface shares the same local SQLite database and service layer as the
PySide desktop application.  Session state is intentionally kept server-side so
resume data is not placed in browser cookies.
"""
from __future__ import annotations

import logging
import re
import tempfile
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database.migrate import run_migrations
from app.logging_config import setup_logging

setup_logging()
run_migrations()

logger = logging.getLogger(__name__)

app = FastAPI(title="Resume Optimizer", docs_url="/docs")

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


@app.middleware("http")
async def attach_local_session(request: Request, call_next):
    """Attach a stable server-side workflow session and persist its cookie."""
    _prune_sessions()
    sid = request.cookies.get(SESSION_COOKIE, "")
    is_new = not sid or sid not in _sessions
    if is_new:
        sid = _new_session_id()
        _sessions[sid] = {}
    _session_seen[sid] = time.time()
    request.state.resume_optimizer_sid = sid

    response = await call_next(request)
    if is_new:
        response.set_cookie(
            SESSION_COOKIE,
            sid,
            max_age=SESSION_MAX_AGE,
            httponly=True,
            samesite="lax",
        )
    return response


@app.get("/builder")
async def builder_root() -> RedirectResponse:
    return RedirectResponse("/builder/", status_code=308)


def _get_session(request: Request) -> dict[str, Any]:
    sid = getattr(request.state, "resume_optimizer_sid", None)
    if not sid:
        # Defensive fallback for direct function calls in tests.
        sid = request.cookies.get(SESSION_COOKIE) or _new_session_id()
        request.state.resume_optimizer_sid = sid
    session = _sessions.setdefault(sid, {})
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
    from app.database.repositories.job_repository import JobRepository
    from app.database.repositories.resume_repository import ResumeRepository
    from app.database.session import get_session

    with get_session() as db_session:
        resumes = ResumeRepository(db_session).get_all()
        jobs = JobRepository(db_session).get_all()
    session = _get_session(request)
    return _render(
        request,
        "dashboard.html",
        {
            "page": "dashboard",
            "resumes": resumes,
            "jobs": jobs,
            "active_resume_id": session.get("resume_id"),
            "active_job_id": session.get("job_id"),
            "error_message": _pop_error(session),
        },
    )


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    session = _get_session(request)
    return _render(
        request,
        "upload.html",
        {
            "page": "upload",
            "error_message": _pop_error(session),
            "resume_name": session.get("resume_name", ""),
            "resume_text": session.get("resume_text", ""),
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
        for key in ("ats_result", "fact_guard", "opt_changes", "optimized_resume", "cover_letter", "cover_warnings"):
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
    for key in ("ats_result", "fact_guard", "opt_changes", "optimized_resume", "cover_letter", "cover_warnings"):
        session.pop(key, None)
    return _redirect("/?resume_loaded=1")


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
            "resume", "resume_id", "resume_name", "resume_text", "ats_result", "fact_guard",
            "opt_changes", "optimized_resume", "cover_letter", "cover_warnings",
        ):
            session.pop(key, None)
    return _redirect("/?resume_deleted=1")


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
):
    session = _get_session(request)
    job_text = job_text.strip()
    if not job_text:
        _set_error(session, "Paste a job description before saving.")
        return _redirect("/jobs?error=1")

    session.update(
        {
            "job_text": job_text,
            "job_title": job_title.strip(),
            "job_company": job_company.strip(),
            "job_location": job_location.strip(),
        }
    )

    from app.database.repositories.job_repository import JobRepository
    from app.database.session import get_session

    with get_session() as db_session:
        job_id = JobRepository(db_session).save(title=job_title.strip(), content=job_text)
        session["job_id"] = job_id

    for key in ("ats_result", "fact_guard", "opt_changes", "optimized_resume", "cover_letter", "cover_warnings"):
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
                "job_company": "",
                "job_location": "",
            }
        )
    for key in ("ats_result", "fact_guard", "opt_changes", "optimized_resume", "cover_letter", "cover_warnings"):
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
            "job_id", "job_text", "job_title", "job_company", "job_location", "ats_result",
            "fact_guard", "opt_changes", "optimized_resume", "cover_letter", "cover_warnings",
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
    if not resume or not job_text:
        return _redirect("/ats?error=missing_input")
    try:
        from app.services.ats_engine import analyze

        session["ats_result"] = analyze(resume, job_text)
        for key in ("fact_guard", "opt_changes", "optimized_resume"):
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
    if not resume or not job_text or not ats:
        return _redirect("/optimize?error=missing_input")

    try:
        from app.ai.ollama_client import OllamaClient
        from app.core.settings import settings_service
        from app.services.optimizer import optimize_resume

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

        session["optimized_resume"] = base_resume
        session["fact_guard"] = fact_guard
        session["opt_changes"] = changes
        return _redirect("/optimize?done=1")
    except Exception as exc:
        logger.exception("Resume optimization failed")
        message = str(exc).lower()
        if "connection" in message or "ollama" in message:
            _set_error(session, "Ollama is unavailable. Start Ollama, verify the model in Settings, and try again.")
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
    if fact_guard is None or resume is None:
        return _redirect("/optimize?error=no_changes")

    accepted = set(accepted_indexes)
    for index, change in enumerate(fact_guard.all_changes):
        change.accepted = index in accepted

    from app.services.optimizer import apply_accepted_changes

    optimized = apply_accepted_changes(resume, fact_guard)
    session["optimized_resume"] = optimized
    session["fact_guard"] = fact_guard
    for item in session.get("opt_changes", []):
        item["accepted"] = item.get("index") in accepted
    return _redirect("/optimize?applied=1")


@app.get("/optimize/download")
async def download_optimized_resume(request: Request):
    session = _get_session(request)
    resume = session.get("optimized_resume")
    if resume is None:
        return _redirect("/optimize?error=no_optimized_resume", status_code=302)
    filename = _safe_filename(session.get("resume_name", "resume"), "resume")
    filename = str(Path(filename).with_suffix("")) + "-optimized.md"
    return PlainTextResponse(
        _resume_to_markdown(resume),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/cover-letter", response_class=HTMLResponse)
async def cover_letter_page(request: Request):
    session = _get_session(request)
    return _render(
        request,
        "cover_letter.html",
        {
            "page": "cover_letter",
            "has_resume": session.get("resume") is not None,
            "has_job": bool(session.get("job_text")),
            "letter": session.get("cover_letter", ""),
            "warnings": session.get("cover_warnings", []),
            "error_message": _pop_error(session),
        },
    )


@app.post("/cover-letter/run")
async def run_cover_letter(request: Request):
    session = _get_session(request)
    resume = session.get("resume")
    job_text = session.get("job_text", "")
    if not resume or not job_text:
        return _redirect("/cover-letter?error=missing_input")

    try:
        from app.ai.ollama_client import OllamaClient
        from app.core.settings import settings_service
        from app.services.cover_letter import generate_cover_letter

        client = OllamaClient(base_url=settings_service.ollama_url, model=settings_service.model)
        result = generate_cover_letter(
            resume,
            job_text,
            client,
            target_company=session.get("job_company"),
            job_title=session.get("job_title"),
        )
        session["cover_letter"] = result.text
        session["cover_warnings"] = list(result.warnings)
        return _redirect("/cover-letter?done=1")
    except Exception as exc:
        logger.exception("Cover letter generation failed")
        message = str(exc).lower()
        if "connection" in message or "ollama" in message:
            _set_error(session, "Ollama is unavailable. Start Ollama, verify the model in Settings, and try again.")
        else:
            _set_error(session, "Cover letter generation failed. Check the AI model and try again.")
        return _redirect("/cover-letter?error=run_failed")


@app.get("/cover-letter/download")
async def download_cover_letter(request: Request):
    session = _get_session(request)
    letter = str(session.get("cover_letter", "")).strip()
    if not letter:
        return _redirect("/cover-letter?error=no_letter", status_code=302)
    company = _safe_filename(session.get("job_company", "company"), "company")
    return PlainTextResponse(
        letter + "\n",
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="cover-letter-{company}.txt"'},
    )


@app.get("/resignation-letter", response_class=HTMLResponse)
async def resignation_letter_page(request: Request):
    session = _get_session(request)
    return _render(
        request,
        "resignation_letter.html",
        {
            "page": "resignation_letter",
            "form_data": _default_resignation_form(session),
            "letter": session.get("resignation_letter", ""),
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
):
    from app.services.resignation_letter import (
        ResignationLetterInput,
        generate_resignation_letter,
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
    }
    session["resignation_form"] = form_data
    payload = ResignationLetterInput(**form_data)
    errors = validate_resignation_input(payload)
    if errors:
        _set_error(session, " ".join(errors))
        return _redirect("/resignation-letter?error=validation")

    session["resignation_letter"] = generate_resignation_letter(payload)
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


@app.post("/resignation-letter/clear")
async def clear_resignation_letter(request: Request):
    session = _get_session(request)
    session.pop("resignation_letter", None)
    session.pop("resignation_form", None)
    return _redirect("/resignation-letter?cleared=1")


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
    if not ollama_url.startswith(("http://", "https://")):
        _set_error(session, "Ollama URL must start with http:// or https://.")
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


async def _ollama_status_payload() -> dict[str, Any]:
    from app.core.settings import settings_service
    import requests as requests_module

    try:
        response = requests_module.get(f"{settings_service.ollama_url}/api/tags", timeout=3)
        response.raise_for_status()
        models = [item.get("name", "") for item in response.json().get("models", []) if item.get("name")]
        return {"connected": True, "models": models, "url": settings_service.ollama_url}
    except Exception:
        return {"connected": False, "models": [], "url": settings_service.ollama_url}


@app.get("/api/ollama/status")
async def ollama_status():
    return await _ollama_status_payload()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_main:app", host="127.0.0.1", port=8000, reload=True)
