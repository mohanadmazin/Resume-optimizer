"""Persistence helpers for the FastAPI web experience."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from app.database.models import GeneratedDocument, WebSession
from app.database.repositories.base import BaseRepository


class WebSessionRepository(BaseRepository):
    def load(self, sid: str) -> dict:
        row = self.session.query(WebSession).filter(WebSession.sid == sid).first()
        if row is None:
            return {}
        try:
            value = json.loads(row.data_json or "{}")
            return value if isinstance(value, dict) else {}
        except (TypeError, ValueError):
            return {}

    def save(self, sid: str, data: dict) -> None:
        row = self.session.query(WebSession).filter(WebSession.sid == sid).first()
        payload = json.dumps(data, ensure_ascii=False, default=str)
        if row is None:
            row = WebSession(sid=sid, data_json=payload)
            self.add(row)
        else:
            row.data_json = payload
            row.updated_at = datetime.utcnow()
        self.flush()

    def prune(self, max_age_seconds: int) -> int:
        cutoff = datetime.utcnow() - timedelta(seconds=max_age_seconds)
        count = self.session.query(WebSession).filter(WebSession.updated_at < cutoff).delete()
        return int(count or 0)


class GeneratedDocumentRepository(BaseRepository):
    def save(
        self,
        document_type: str,
        title: str,
        content: str,
        *,
        resume_id: int | None = None,
        job_id: int | None = None,
        metadata: dict | None = None,
        document_id: int | None = None,
    ) -> int:
        row = None
        if document_id:
            row = self.session.query(GeneratedDocument).filter(GeneratedDocument.id == document_id).first()
        if row is None:
            row = GeneratedDocument(document_type=document_type, title=title, content=content)
            self.add(row)
        row.document_type = document_type
        row.title = title
        row.content = content
        row.resume_id = resume_id
        row.job_id = job_id
        row.metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
        row.updated_at = datetime.utcnow()
        self.flush()
        return int(row.id)

    def get(self, document_id: int) -> GeneratedDocument | None:
        return self.session.query(GeneratedDocument).filter(GeneratedDocument.id == document_id).first()

    def list_recent(self, document_type: str | None = None, limit: int = 10) -> list[dict]:
        query = self.session.query(GeneratedDocument)
        if document_type:
            query = query.filter(GeneratedDocument.document_type == document_type)
        rows = query.order_by(GeneratedDocument.updated_at.desc()).limit(limit).all()
        return [
            {
                "id": row.id,
                "document_type": row.document_type,
                "title": row.title,
                "content": row.content,
                "resume_id": row.resume_id,
                "job_id": row.job_id,
                "updated_at": row.updated_at.strftime("%Y-%m-%d %H:%M") if row.updated_at else "",
            }
            for row in rows
        ]

    def delete(self, document_id: int) -> bool:
        row = self.get(document_id)
        if row is None:
            return False
        self.session.delete(row)
        return True
