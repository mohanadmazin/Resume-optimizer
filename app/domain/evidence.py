"""Career Evidence Vault — domain models for verified career facts."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FactType(str, Enum):
    """Classification of career facts."""

    ACHIEVEMENT = "achievement"
    RESPONSIBILITY = "responsibility"
    PROJECT = "project"
    METRIC = "metric"
    TECHNOLOGY = "technology"
    TEAM = "team"
    BUDGET = "budget"
    CUSTOMER = "customer"
    AWARD = "award"
    CERTIFICATION = "certification"
    PUBLICATION = "publication"
    TESTIMONIAL = "testimonial"
    PORTFOLIO = "portfolio"
    EMPLOYMENT = "employment"
    OTHER = "other"


class FactConfidence(str, Enum):
    """How confident we are that a fact is accurate."""

    VERIFIED = "verified"
    USER_CONFIRMED = "user_confirmed"
    REASONABLE_PARAPHRASE = "reasonable_paraphrase"
    USER_ESTIMATE = "user_estimate"
    UNSUPPORTED = "unsupported"
    CONTRADICTORY = "contradictory"


class SourceType(str, Enum):
    """Where evidence came from."""

    DOCUMENT = "document"
    MEMORY = "memory"
    WORKFLOW_LOG = "workflow_log"
    TESTIMONIAL = "testimonial"
    INTERVIEW = "interview"
    RESUME_IMPORT = "resume_import"


class ContentLinkType(str, Enum):
    """What type of content links to a fact."""

    RESUME_BULLET = "resume_bullet"
    COVER_LETTER = "cover_letter"
    INTERVIEW_ANSWER = "interview_answer"
    APPLICATION_ANSWER = "application_answer"


class CareerFact(BaseModel):
    """A single verified career fact with source attribution."""

    id: int | None = None
    statement: str = ""
    fact_type: FactType = FactType.OTHER
    confidence: FactConfidence = FactConfidence.USER_ESTIMATE
    employer: str = ""
    project: str = ""
    date_from: str = ""
    date_to: str = ""
    sensitive: bool = False
    metrics_json: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""


class EvidenceSource(BaseModel):
    """A source document or reference that supports career facts."""

    id: int | None = None
    source_type: SourceType = SourceType.DOCUMENT
    name: str = ""
    file_path: str = ""
    excerpt: str = ""
    page_reference: str = ""
    notes: str = ""
    created_at: str = ""


class FactVerificationEvent(BaseModel):
    """Record of a fact being verified or rejected."""

    id: int | None = None
    fact_id: int = 0
    previous_confidence: FactConfidence = FactConfidence.UNSUPPORTED
    new_confidence: FactConfidence = FactConfidence.UNSUPPORTED
    reason: str = ""
    verified_by: str = "user"
    created_at: str = ""


class ContentFactLink(BaseModel):
    """Links a content item (bullet, cover letter, etc.) to a career fact."""

    id: int | None = None
    content_type: ContentLinkType = ContentLinkType.RESUME_BULLET
    content_id: int = 0
    fact_id: int = 0
    relevance: str = "direct"
    created_at: str = ""


class FactWithSources(BaseModel):
    """A career fact enriched with its linked sources."""

    fact: CareerFact
    sources: list[EvidenceSource] = Field(default_factory=list)
    linked_content_count: int = 0
