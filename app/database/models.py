"""SQLAlchemy database schema."""
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    data_json = Column(Text, nullable=False)
    raw_text = Column(Text, default="")
    source_type = Column(String(50), default="import")
    source_filename = Column(String(500), default="")
    source_hash = Column(String(64), default="")
    is_original = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    analyses = relationship("Analysis", cascade="all, delete-orphan", passive_deletes=True)
    optimizations = relationship("Optimization", cascade="all, delete-orphan", passive_deletes=True)


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    company = Column(String(255), default="")
    location = Column(String(255), default="")
    source_url = Column(Text, default="")
    employment_type = Column(String(100), default="")
    salary = Column(String(150), default="")
    date_posted = Column(String(40), default="")
    status = Column(String(50), default="saved")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    analyses = relationship("Analysis", cascade="all, delete-orphan", passive_deletes=True)
    optimizations = relationship("Optimization", cascade="all, delete-orphan", passive_deletes=True)


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    ats_score = Column(Integer, nullable=False)
    keyword_match = Column(Float, default=0.0)
    skills_match = Column(Float, default=0.0)
    missing_keywords = Column(Text, default="[]")
    suggestions = Column(Text, default="[]")
    result_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)


class Optimization(Base):
    __tablename__ = "optimizations"

    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    model = Column(String(100), default="")
    optimized_json = Column(Text, nullable=False)
    fact_guard_json = Column(Text, default="{}")
    accepted_changes_json = Column(Text, default="[]")
    original_score = Column(Integer, default=0)
    optimized_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Versioning & targeting ─────────────────────────────────────────────────


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True)
    resume_id = Column(
        Integer,
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)
    data_json = Column(Text, nullable=False)
    change_summary = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("resume_id", "version_number", name="uq_resume_version"),
    )


class TargetingSession(Base):
    __tablename__ = "targeting_sessions"

    id = Column(Integer, primary_key=True)
    resume_version_id = Column(
        Integer,
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id = Column(
        Integer,
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    requirements_json = Column(Text, nullable=False)
    score_report_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class SuggestionRecord(Base):
    __tablename__ = "suggestions"

    id = Column(Integer, primary_key=True)
    targeting_session_id = Column(
        Integer,
        ForeignKey("targeting_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_path = Column(String(500), nullable=False)
    original_text = Column(Text, nullable=False)
    suggested_text = Column(Text, nullable=False)
    evidence_json = Column(Text, nullable=False)
    status = Column(String(30), default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Preferences & generated content ────────────────────────────────────────


class TemplatePreference(Base):
    __tablename__ = "template_preferences"

    id = Column(Integer, primary_key=True)
    resume_id = Column(
        Integer,
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("resume_id", name="uq_template_preference"),
    )


class CoverLetter(Base):
    __tablename__ = "cover_letters"

    id = Column(Integer, primary_key=True)
    resume_id = Column(
        Integer,
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id = Column(
        Integer,
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    model = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WebSession(Base):
    __tablename__ = "web_sessions"

    sid = Column(String(64), primary_key=True)
    data_json = Column(Text, nullable=False, default="{}")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id = Column(Integer, primary_key=True)
    document_type = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="Untitled document")
    content = Column(Text, nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Agent conversations ────────────────────────────────────────────────────


class AgentConversation(Base):
    __tablename__ = "agent_conversations"

    id = Column(Integer, primary_key=True)
    resume_id = Column(
        Integer,
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_id = Column(
        Integer,
        ForeignKey("job_descriptions.id", ondelete="SET NULL"),
        nullable=True,
    )
    title = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(
        Integer,
        ForeignKey("agent_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(30), nullable=False)
    content = Column(Text, nullable=False)
    model = Column(String(100), default="")
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Job applications & interview prep ──────────────────────────────────────


class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True)
    resume_id = Column(
        Integer,
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id = Column(
        Integer,
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String(50), default="draft", nullable=False)
    notes = Column(Text, default="")
    applied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True)
    resume_id = Column(
        Integer,
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_id = Column(
        Integer,
        ForeignKey("job_descriptions.id", ondelete="SET NULL"),
        nullable=True,
    )
    company = Column(String(255), default="")
    role = Column(String(255), default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Score snapshots (historical tracking) ──────────────────────────────────


class ScoreSnapshot(Base):
    __tablename__ = "score_snapshots"

    id = Column(Integer, primary_key=True)
    resume_id = Column(
        Integer,
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id = Column(
        Integer,
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=True,
    )
    ats_score = Column(Integer, nullable=False)
    keyword_match = Column(Float, default=0.0)
    skills_match = Column(Float, default=0.0)
    score_report_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Career Evidence Vault ───────────────────────────────────────────────────


class CareerFact(Base):
    __tablename__ = "career_facts"

    id = Column(Integer, primary_key=True)
    statement = Column(Text, nullable=False)
    fact_type = Column(String(50), default="other", nullable=False, index=True)
    confidence = Column(String(50), default="user_estimate", nullable=False, index=True)
    employer = Column(String(255), default="", index=True)
    project = Column(String(255), default="")
    date_from = Column(String(20), default="")
    date_to = Column(String(20), default="")
    sensitive = Column(Boolean, default=False)
    metrics_json = Column(Text, default="{}")
    tags_json = Column(Text, default="[]")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sources = relationship(
        "EvidenceSource",
        secondary="career_fact_sources",
        back_populates="facts",
        passive_deletes=True,
    )


class EvidenceSource(Base):
    __tablename__ = "evidence_sources"

    id = Column(Integer, primary_key=True)
    source_type = Column(String(50), default="document", nullable=False, index=True)
    name = Column(String(500), nullable=False)
    file_path = Column(Text, default="")
    excerpt = Column(Text, default="")
    page_reference = Column(String(100), default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    facts = relationship(
        "CareerFact",
        secondary="career_fact_sources",
        back_populates="sources",
        passive_deletes=True,
    )


class CareerFactSource(Base):
    __tablename__ = "career_fact_sources"

    id = Column(Integer, primary_key=True)
    fact_id = Column(
        Integer,
        ForeignKey("career_facts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id = Column(
        Integer,
        ForeignKey("evidence_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("fact_id", "source_id", name="uq_fact_source"),
    )


class ContentFactLink(Base):
    __tablename__ = "content_fact_links"

    id = Column(Integer, primary_key=True)
    content_type = Column(String(50), nullable=False, index=True)
    content_id = Column(Integer, nullable=False, index=True)
    fact_id = Column(
        Integer,
        ForeignKey("career_facts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relevance = Column(String(50), default="direct")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("content_type", "content_id", "fact_id", name="uq_content_fact"),
    )


class FactVerificationEvent(Base):
    __tablename__ = "fact_verification_events"

    id = Column(Integer, primary_key=True)
    fact_id = Column(
        Integer,
        ForeignKey("career_facts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_confidence = Column(String(50), default="unsupported")
    new_confidence = Column(String(50), default="unsupported")
    reason = Column(Text, default="")
    verified_by = Column(String(100), default="user")
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Master Career Profile ────────────────────────────────────────────────────


class MasterProfile(Base):
    __tablename__ = "master_profiles"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, default="Default Profile")
    profile_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
