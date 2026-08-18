"""Server-side workflow session management for the FastAPI interface."""
from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request
from fastapi.responses import Response

logger = logging.getLogger(__name__)

SESSION_COOKIE = "resume_optimizer_sid"
SESSION_MAX_AGE = 60 * 60 * 12
MAX_SESSIONS = 250

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self' http://localhost:* http://127.0.0.1:*"
    ),
}


class WorkflowSessionStore:
    """Bounded in-memory workflow sessions backed by SQLite snapshots."""

    def __init__(
        self,
        *,
        cookie_name: str = SESSION_COOKIE,
        max_age_seconds: int = SESSION_MAX_AGE,
        max_sessions: int = MAX_SESSIONS,
    ) -> None:
        self.cookie_name = cookie_name
        self.max_age_seconds = max_age_seconds
        self.max_sessions = max_sessions
        self._sessions: dict[str, dict[str, Any]] = {}
        self._session_seen: dict[str, float] = {}

    def new_session_id(self) -> str:
        return uuid.uuid4().hex

    def prune(self) -> None:
        """Bound the local in-memory session store and discard stale entries."""
        now = time.time()
        stale = [
            sid
            for sid, seen in self._session_seen.items()
            if now - seen > self.max_age_seconds
        ]
        for sid in stale:
            self._sessions.pop(sid, None)
            self._session_seen.pop(sid, None)

        if len(self._sessions) <= self.max_sessions:
            return
        overflow = len(self._sessions) - self.max_sessions
        for sid, _ in sorted(self._session_seen.items(), key=lambda item: item[1])[:overflow]:
            self._sessions.pop(sid, None)
            self._session_seen.pop(sid, None)

    def serialize(self, session: dict[str, Any]) -> dict[str, Any]:
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

    def deserialize(self, payload: dict[str, Any]) -> dict[str, Any]:
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

    def load_persisted(self, sid: str) -> dict[str, Any]:
        try:
            from app.database.repositories.web_repository import WebSessionRepository
            from app.database.session import get_session

            with get_session() as db_session:
                return self.deserialize(WebSessionRepository(db_session).load(sid))
        except Exception:
            logger.warning("Could not restore web session", exc_info=True)
            return {}

    def save_persisted(self, sid: str, session: dict[str, Any]) -> None:
        try:
            from app.database.repositories.web_repository import WebSessionRepository
            from app.database.session import get_session

            with get_session() as db_session:
                repo = WebSessionRepository(db_session)
                repo.save(sid, self.serialize(session))
                repo.prune(self.max_age_seconds)
        except Exception:
            logger.warning("Could not persist web session", exc_info=True)

    async def attach_local_session(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Restore and persist a bounded local workflow session for one request."""
        self.prune()
        sid = request.cookies.get(self.cookie_name, "")
        is_new = not sid
        if not sid:
            sid = self.new_session_id()
        if sid not in self._sessions:
            self._sessions[sid] = self.load_persisted(sid)
        self._session_seen[sid] = time.time()
        request.state.resume_optimizer_sid = sid

        try:
            response = await call_next(request)
        finally:
            self.save_persisted(sid, self._sessions.get(sid, {}))

        if is_new:
            response.set_cookie(
                self.cookie_name,
                sid,
                max_age=self.max_age_seconds,
                httponly=True,
                samesite="lax",
                secure=False,  # localhost HTTP by default
            )
        for name, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    def get(self, request: Request) -> dict[str, Any]:
        sid = getattr(request.state, "resume_optimizer_sid", None)
        if not sid:
            sid = request.cookies.get(self.cookie_name) or self.new_session_id()
            request.state.resume_optimizer_sid = sid
        if sid not in self._sessions:
            self._sessions[sid] = self.load_persisted(sid)
        session = self._sessions.setdefault(sid, {})
        self._ensure_workflow_objects(session)
        self._session_seen[sid] = time.time()
        return session

    def _ensure_workflow_objects(self, session: dict[str, Any]) -> None:
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
                        if row is not None and row.data_json is not None:
                            session["resume"] = ResumeData.model_validate_json(row.data_json)
                            session["resume_name"] = row.name or "Untitled"
                            session["resume_text"] = row.raw_text or ""
                    if job_id and not session.get("job_text"):
                        job_row = JobRepository(db_session).get_by_id(int(job_id))
                        if job_row is not None:
                            session.update({
                                "job_title": job_row.title or "",
                                "job_text": job_row.content or "",
                                "job_company": job_row.company or "",
                                "job_location": job_row.location or "",
                                "job_source_url": job_row.source_url or "",
                                "job_employment_type": job_row.employment_type or "",
                                "job_salary": job_row.salary or "",
                                "job_date_posted": job_row.date_posted or "",
                                "job_status": job_row.status or "saved",
                            })
            except Exception:
                logger.warning("Could not hydrate selected workflow records", exc_info=True)
