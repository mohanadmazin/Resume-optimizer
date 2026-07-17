"""ATS analysis domain models — scoring, keywords, suggestions."""
from dataclasses import asdict, dataclass, field
from typing import List


@dataclass
class ATSResult:
    ats_score: int
    keyword_match_pct: float
    skills_match_pct: float
    matched_keywords: List[str] = field(default_factory=list)
    missing_keywords: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    keyword_weights: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)
