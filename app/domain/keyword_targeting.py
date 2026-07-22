"""Keyword targeting domain models and helpers."""
import re
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
        normalized_terms = {normalize(term) for term in terms if normalize(term)}
        matches: List[ResumeTextMatch] = []
        for path, text in self.path_text:
            normalized_text = normalize(text)
            if any(term in normalized_text for term in normalized_terms):
                matches.append(ResumeTextMatch(path=path, text=text))
        return matches

    def find_semantic_overlap(self, term: str) -> bool:
        # Compare normalized values so punctuation variants such as SD-WAN,
        # TCP/IP and Palo Alto are handled consistently.
        norm_term = normalize(term)
        term_tokens = {normalize(token) for token in re.findall(r"[a-z0-9#+.]+", term.lower()) if len(normalize(token)) >= 3}
        for _, text in self.path_text:
            normalized_text = normalize(text)
            if norm_term and norm_term in normalized_text:
                return True
            text_tokens = {normalize(token) for token in re.findall(r"[a-z0-9#+.]+", text.lower()) if len(normalize(token)) >= 3}
            if term_tokens and term_tokens & text_tokens:
                return True
            if any(
                left.startswith(right) or right.startswith(left)
                for left in term_tokens
                for right in text_tokens
                if min(len(left), len(right)) >= 3
            ):
                return True
        return False

class ResumeTextMatch(BaseModel):
    path: str
    text: str

# Normalization helper
def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9#+.]", "", s.lower())

