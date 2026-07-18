"""ATS analysis domain models — scoring, keywords, suggestions."""
from dataclasses import asdict, dataclass, field
from typing import List

from app.domain.scoring import ResumeScoreReport


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
    score_report: ResumeScoreReport | None = None
    keyword_targets: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        if d.get("score_report") is not None:
            d["score_report"] = self.score_report.model_dump()
        return d
