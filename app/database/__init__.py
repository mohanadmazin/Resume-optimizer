"""Database package — public API."""
from app.database.engine import engine
from app.database.session import SessionLocal, get_session
from app.database.repositories import (
    ResumeRepository,
    JobRepository,
    AnalysisRepository,
    VersioningRepository,
)
from app.database.models import (
    Base,
    Resume,
    JobDescription,
    Analysis,
    Optimization,
    ResumeVersion,
    TargetingSession,
    SuggestionRecord,
    TemplatePreference,
    CoverLetter,
    AgentConversation,
    AgentMessage,
    JobApplication,
    InterviewSession,
    ScoreSnapshot,
)

__all__ = [
    "engine",
    "SessionLocal",
    "get_session",
    "ResumeRepository",
    "JobRepository",
    "AnalysisRepository",
    "VersioningRepository",
    "Base",
    "Resume",
    "JobDescription",
    "Analysis",
    "Optimization",
    "ResumeVersion",
    "TargetingSession",
    "SuggestionRecord",
    "TemplatePreference",
    "CoverLetter",
    "AgentConversation",
    "AgentMessage",
    "JobApplication",
    "InterviewSession",
    "ScoreSnapshot",
]
