"""Resume Optimizer — Web UI (FastAPI + Jinja2).

Run with: python web_main.py
Or:       uvicorn web_main:app --reload --port 8000
"""
from __future__ import annotations

import io
import json
import logging
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database.migrate import run_migrations
from app.logging_config import setup_logging

# ── Bootstrap ────────────────────────────────────────────────────────
setup_logging()
run_migrations()

logger = logging.getLogger(__name__)

app = FastAPI(title="Resume Optimizer", docs_url="/docs")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "web" / "static")), name="static")

# ── In-memory session store (per-tab) ────────────────────────────────
_sessions: dict[str, dict] = {}


def _get_session(request: Request) -> dict:
    sid = request.cookies.get("sid", "")
    if sid not in _sessions:
        sid = uuid.uuid4().hex
        _sessions[sid] = {}
    return _sessions.setdefault(sid, {"_sid": sid})


# ── Page routes ──────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    from app.database import db
    with db._session_factory() as session:
        from app.database.repositories.resume_repository import ResumeRepository
        from app.database.repositories.analysis_repository import AnalysisRepository
        resumes = ResumeRepository(session).get_all()
        analyses = AnalysisRepository(session).get_recent(10) if hasattr(AnalysisRepository(session), 'get_recent') else []
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "page": "dashboard",
        "resumes": resumes, "analyses": analyses,
    })


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request, "page": "upload"})


@app.post("/upload")
async def upload_resume(request: Request, file: UploadFile = File(...)):
    from app.services.document_reader import extract_text
    from app.services.resume_parser import parse_resume_text
    from app.schemas import ResumeData
    from app.database import db

    content = await file.read()
    suffix = Path(file.filename or "resume.txt").suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        raw_text = extract_text(tmp_path)
        resume = parse_resume_text(raw_text)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # Save to DB
    import json as _json
    with db._session_factory() as session:
        from app.database.repositories.resume_repository import ResumeRepository
        repo = ResumeRepository(session)
        row = repo.create(name=file.filename or "Untitled", data_json=resume.model_dump_json())
        resume_id = row["id"]

    session = _get_session(request)
    session["resume"] = resume
    session["resume_id"] = resume_id
    session["resume_text"] = raw_text

    return RedirectResponse("/upload?imported=1", status_code=303)


@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request):
    session = _get_session(request)
    return templates.TemplateResponse("jobs.html", {
        "request": request, "page": "jobs",
        "job_text": session.get("job_text", ""),
        "job_title": session.get("job_title", ""),
    })


@app.post("/jobs")
async def save_job(
    request: Request,
    job_text: str = Form(...),
    job_title: str = Form(""),
    job_company: str = Form(""),
    job_location: str = Form(""),
):
    from app.database import db
    session = _get_session(request)
    session["job_text"] = job_text
    session["job_title"] = job_title
    session["job_company"] = job_company
    session["job_location"] = job_location

    with db._session_factory() as db_sess:
        from app.database.repositories.job_repository import JobRepository
        repo = JobRepository(db_sess)
        row = repo.create(title=job_title, company=job_company, location=job_location, content=job_text)
        session["job_id"] = row["id"]

    return RedirectResponse("/jobs?saved=1", status_code=303)


@app.get("/ats", response_class=HTMLResponse)
async def ats_page(request: Request):
    session = _get_session(request)
    return templates.TemplateResponse("ats.html", {
        "request": request, "page": "ats",
        "has_resume": session.get("resume") is not None,
        "has_job": bool(session.get("job_text")),
        "result": session.get("ats_result"),
    })


@app.post("/ats/run")
async def run_ats(request: Request):
    session = _get_session(request)
    resume = session.get("resume")
    job_text = session.get("job_text", "")

    if not resume or not job_text:
        return RedirectResponse("/ats?error=missing_input", status_code=303)

    from app.services.ats_engine import analyze
    result = analyze(resume, job_text)
    session["ats_result"] = result
    return RedirectResponse("/ats?done=1", status_code=303)


@app.get("/optimize", response_class=HTMLResponse)
async def optimize_page(request: Request):
    session = _get_session(request)
    ats = session.get("ats_result")
    return templates.TemplateResponse("optimize.html", {
        "request": request, "page": "optimize",
        "has_resume": session.get("resume") is not None,
        "has_job": bool(session.get("job_text")),
        "has_ats": ats is not None,
        "changes": session.get("opt_changes"),
        "optimized": session.get("optimized_resume"),
    })


@app.post("/optimize/run")
async def run_optimize(request: Request):
    session = _get_session(request)
    resume = session.get("resume")
    job_text = session.get("job_text", "")
    ats = session.get("ats_result")

    if not resume or not job_text or not ats:
        return RedirectResponse("/optimize?error=missing_input", status_code=303)

    from app.ai.ollama_client import OllamaClient
    from app.services.optimizer import optimize_resume
    from app.core.settings import settings_service

    client = OllamaClient(base_url=settings_service.ollama_url, model=settings_service.model)
    optimized, fact_guard = optimize_resume(resume, job_text, ats, client)
    session["optimized_resume"] = optimized
    session["fact_guard"] = fact_guard
    session["opt_changes"] = [c.model_dump() for c in fact_guard.changes] if fact_guard else []
    return RedirectResponse("/optimize?done=1", status_code=303)


@app.get("/cover-letter", response_class=HTMLResponse)
async def cover_letter_page(request: Request):
    session = _get_session(request)
    return templates.TemplateResponse("cover_letter.html", {
        "request": request, "page": "cover_letter",
        "has_resume": session.get("resume") is not None,
        "has_job": bool(session.get("job_text")),
        "letter": session.get("cover_letter"),
        "warnings": session.get("cover_warnings", []),
    })


@app.post("/cover-letter/run")
async def run_cover_letter(request: Request):
    session = _get_session(request)
    resume = session.get("resume")
    job_text = session.get("job_text", "")

    if not resume or not job_text:
        return RedirectResponse("/cover-letter?error=missing_input", status_code=303)

    from app.ai.ollama_client import OllamaClient
    from app.services.cover_letter import generate_cover_letter
    from app.core.settings import settings_service

    client = OllamaClient(base_url=settings_service.ollama_url, model=settings_service.model)
    result = generate_cover_letter(resume, job_text, client,
                                   target_company=session.get("job_company"))
    session["cover_letter"] = result.text
    session["cover_warnings"] = list(result.warnings)
    return RedirectResponse("/cover-letter?done=1", status_code=303)


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    from app.core.settings import settings_service
    return templates.TemplateResponse("settings.html", {
        "request": request, "page": "settings",
        "ollama_url": settings_service.ollama_url,
        "model": settings_service.model,
        "temperature": settings_service.temperature,
        "available_models": settings_service.available_models,
    })


@app.post("/settings")
async def save_settings(
    request: Request,
    ollama_url: str = Form("http://localhost:11434"),
    model: str = Form("qwen3"),
    temperature: float = Form(0.3),
):
    from app.core.settings import settings_service
    patched = settings_service.settings.model_copy(deep=True)
    patched.ai.ollama_url = ollama_url
    patched.ai.model = model
    patched.ai.temperature = temperature
    settings_service.save(patched)
    return RedirectResponse("/settings?saved=1", status_code=303)


# ── API routes (for async operations) ────────────────────────────────

@app.get("/api/resumes")
async def api_resumes():
    from app.database import db
    with db._session_factory() as session:
        from app.database.repositories.resume_repository import ResumeRepository
        return ResumeRepository(session).get_all()


@app.get("/api/jobs")
async def api_jobs():
    from app.database import db
    with db._session_factory() as session:
        from app.database.repositories.job_repository import JobRepository
        return JobRepository(session).get_all()


@app.get("/api/session")
async def api_session(request: Request):
    session = _get_session(request)
    return {
        "has_resume": session.get("resume") is not None,
        "has_job": bool(session.get("job_text")),
        "has_ats": session.get("ats_result") is not None,
        "resume_name": session.get("resume_name", ""),
        "job_title": session.get("job_title", ""),
    }


@app.get("/api/ollama/status")
async def ollama_status():
    from app.core.settings import settings_service
    import requests as _req
    try:
        r = _req.get(f"{settings_service.ollama_url}/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        return {"connected": True, "models": models}
    except Exception:
        return {"connected": False, "models": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_main:app", host="127.0.0.1", port=8000, reload=True)
