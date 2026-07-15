"""Database engine, session and CRUD helpers."""
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import APP_DIR, DB_PATH
from app.database.models import Analysis, Base, JobDescription, Optimization, Resume

APP_DIR.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    Base.metadata.create_all(engine)


def save_resume(name: str, data_json: str, raw_text: str = "") -> int:
    with SessionLocal() as session:
        row = Resume(name=name, data_json=data_json, raw_text=raw_text)
        session.add(row)
        session.commit()
        return row.id


def save_job(title: str, content: str) -> int:
    with SessionLocal() as session:
        row = JobDescription(title=title, content=content)
        session.add(row)
        session.commit()
        return row.id


def save_analysis(resume_id: int, job_id: int, result: dict) -> int:
    with SessionLocal() as session:
        row = Analysis(
            resume_id=resume_id,
            job_id=job_id,
            ats_score=result["ats_score"],
            keyword_match=result["keyword_match_pct"],
            skills_match=result["skills_match_pct"],
            missing_keywords=json.dumps(result["missing_keywords"]),
            suggestions=json.dumps(result["suggestions"]),
        )
        session.add(row)
        session.commit()
        return row.id


def save_optimization(resume_id: int, job_id: int, model: str, optimized_json: str) -> int:
    with SessionLocal() as session:
        row = Optimization(resume_id=resume_id, job_id=job_id, model=model, optimized_json=optimized_json)
        session.add(row)
        session.commit()
        return row.id


def latest_resume() -> dict | None:
    with SessionLocal() as session:
        row = session.query(Resume).order_by(Resume.id.desc()).first()
        if row is None:
            return None
        return {"id": row.id, "name": row.name, "data_json": row.data_json, "raw_text": row.raw_text}


def latest_job() -> dict | None:
    with SessionLocal() as session:
        row = session.query(JobDescription).order_by(JobDescription.id.desc()).first()
        if row is None:
            return None
        return {"id": row.id, "title": row.title, "content": row.content}


def recent_analyses(limit: int = 10) -> list[dict]:
    with SessionLocal() as session:
        rows = (
            session.query(Analysis, Resume.name, JobDescription.title)
            .join(Resume, Analysis.resume_id == Resume.id)
            .join(JobDescription, Analysis.job_id == JobDescription.id)
            .order_by(Analysis.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "created_at": analysis.created_at.strftime("%Y-%m-%d %H:%M"),
                "resume_name": resume_name,
                "job_title": job_title,
                "ats_score": analysis.ats_score,
                "keyword_match": analysis.keyword_match,
                "skills_match": analysis.skills_match,
            }
            for analysis, resume_name, job_title in rows
        ]
