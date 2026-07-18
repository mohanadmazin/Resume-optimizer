"""Keyword targeting domain models and helpers."""
from typing import List
from enum import Enum
from pydantic import BaseModel, Field

class KeywordStatus(str, Enum):
    PRESENT = "present"
    MISSING = "missing"
    PARTIAL = "partial"
    IRRELEVANT = "irrelevant"

class KeywordTarget(BaseModel):
    canonical_name: str
    source_phrases: List[str]
    importance: float = Field(ge=0, le=1)
    frequency_in_job: int = Field(ge=0)
    status: KeywordStatus
    evidence_paths: List[str] = Field(default_factory=list)
    suggested_paths: List[str] = Field(default_factory=list)
    requires_user_confirmation: bool = True

class JobRequirement(BaseModel):
    name: str
    aliases: List[str] = Field(default_factory=list)
    importance: float = 1.0
    frequency: int = 1
    source_phrases: List[str] = Field(default_factory=list)

class ResumeTextIndex(BaseModel):
    """
    Searchable index of normalized resume text, paths → text.
    For MVP, field: [(path, norm_text)] list for fast lookup.
    """
    path_text: List[tuple[str, str]]

    def find_any(self, terms: set[str]) -> List["ResumeTextMatch"]:
        return [ResumeTextMatch(path=path, text=text) for path, text in self.path_text if any(t in text for t in terms)]

    def find_semantic_overlap(self, term: str) -> bool:
        # MVP: partial substring or token overlap
        norm_term = normalize(term)
        for _, text in self.path_text:
            if norm_term in text or any(t in text for t in norm_term.split()):
                return True
            # Check if any word in the text is a substring of the term or vice versa
            for word in text.split():
                if len(word) >= 3 and (word in norm_term or norm_term in word):
                    return True
        return False

class ResumeTextMatch(BaseModel):
    path: str
    text: str

# Normalization helper
import re
def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9#+.]", "", s.lower())

