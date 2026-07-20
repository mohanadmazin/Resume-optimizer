"""Repository package for database access."""
from app.database.repositories.agent_repository import AgentRepository
from app.database.repositories.application_repository import ApplicationRepository
from app.database.repositories.cover_letter_repository import CoverLetterRepository
from app.database.repositories.resume_repository import ResumeRepository
from app.database.repositories.job_repository import JobRepository
from app.database.repositories.analysis_repository import AnalysisRepository
from app.database.repositories.versioning_repository import VersioningRepository

__all__ = [
    "AgentRepository",
    "ApplicationRepository",
    "CoverLetterRepository",
    "ResumeRepository",
    "JobRepository",
    "AnalysisRepository",
    "VersioningRepository",
]
