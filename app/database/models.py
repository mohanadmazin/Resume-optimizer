"""SQLAlchemy database schema."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base

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


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False)
    ats_score = Column(Integer, nullable=False)
    keyword_match = Column(Float, default=0.0)
    skills_match = Column(Float, default=0.0)
    missing_keywords = Column(Text, default="[]")
    suggestions = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)


class Optimization(Base):
    __tablename__ = "optimizations"

    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False)
    model = Column(String(100), default="")
    optimized_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
