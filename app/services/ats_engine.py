"""ATS analysis engine: keyword extraction, scoring and suggestions."""
import logging
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import List

from app.schemas import ResumeData

logger = logging.getLogger(__name__)

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can", "could", "did", "do",
    "does", "for", "from", "had", "has", "have", "her", "his", "how", "i", "if", "in", "into",
    "is", "it", "its", "may", "more", "most", "not", "of", "on", "or", "our", "out", "over",
    "per", "so", "such", "than", "that", "the", "their", "them", "then", "there", "these",
    "they", "this", "through", "to", "under", "up", "us", "was", "we", "well", "were", "what",
    "when", "where", "which", "while", "who", "whom", "why", "will", "with", "would", "you",
    "your", "about", "across", "all", "also", "any", "both", "each", "other", "some",
    # Job-posting boilerplate
    "ability", "able", "applicant", "apply", "benefits", "candidate", "candidates", "company",
    "day", "daily", "description", "duties", "employee", "equal", "etc", "excellent",
    "experience", "experienced", "familiar", "familiarity", "good", "great", "help", "ideal",
    "including", "job", "join", "knowledge", "looking", "member", "must", "new", "opportunity",
    "plus", "position", "preferred", "proficiency", "proficient", "related", "required",
    "requirements", "responsibilities", "responsible", "role", "salary", "seeking", "skills",
    "strong", "team", "understanding", "work", "working", "years", "year", "using", "used",
    "use", "within", "like", "e.g", "eg", "ie",
}

SHORT_KEEP = {"c#", "go", "r", "ai", "ml", "qa", "ci", "cd", "ux", "ui", "c++", "aws", "sql", "api", "git"}


@dataclass
class ATSResult:
    ats_score: int
    keyword_match_pct: float
    skills_match_pct: float
    matched_keywords: List[str] = field(default_factory=list)
    missing_keywords: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def extract_keywords(text: str, top_n: int = 25) -> list[str]:
    tokens = [t.strip(".-/") for t in re.findall(r"[a-z][a-z0-9+#.\-/]*", text.lower())]
    words = [
        t for t in tokens
        if t and t not in STOPWORDS and (len(t) > 2 or t in SHORT_KEEP)
    ]
    counts = Counter(words)
    bigrams: Counter = Counter()
    for first, second in zip(words, words[1:]):
        bigrams[f"{first} {second}"] += 1
    top_bigrams = [b for b, c in bigrams.most_common(10) if c >= 2]
    singles = [w for w, _ in counts.most_common(top_n * 2) if w not in " ".join(top_bigrams)]
    return (top_bigrams + singles)[:top_n]


def _contains(text: str, keyword: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _resume_text(resume: ResumeData) -> str:
    parts = [resume.summary, " ".join(resume.skills)]
    for exp in resume.experience:
        parts += [exp.title, exp.company, " ".join(exp.bullets)]
    parts += [f"{edu.degree} {edu.institution}" for edu in resume.education]
    parts += resume.certifications
    return " ".join(p for p in parts if p)


def analyze(resume: ResumeData, jd_text: str) -> ATSResult:
    keywords = extract_keywords(jd_text)
    resume_text = f"{resume.raw_text} {_resume_text(resume)}".lower()
    jd_lower = jd_text.lower()

    matched = [k for k in keywords if _contains(resume_text, k)]
    missing = [k for k in keywords if k not in matched]
    keyword_pct = round(100 * len(matched) / len(keywords), 1) if keywords else 0.0

    skills = [s for s in resume.skills if s.strip()]
    matched_skills = [s for s in skills if _contains(jd_lower, s.lower())]
    skills_pct = round(100 * len(matched_skills) / len(skills), 1) if skills else 0.0
    missing_skills = [k for k in missing if len(k.split()) <= 3][:10]

    structure = 0
    structure += 4 if resume.contact.email else 0
    structure += 4 if resume.contact.phone else 0
    structure += 4 if resume.summary else 0
    structure += 4 if resume.skills else 0
    structure += 2 if resume.experience else 0
    structure += 2 if resume.education else 0

    formatting = 10
    word_count = len(resume_text.split())
    if word_count < 200 or word_count > 1200:
        formatting -= 5
    if not any(exp.bullets for exp in resume.experience):
        formatting -= 5

    score = int(round(keyword_pct * 0.5 + skills_pct * 0.2 + structure + formatting))
    score = max(0, min(100, score))

    logger.info(
        "ATS analysis: score=%d keyword_pct=%.1f skills_pct=%.1f missing=%d",
        score, keyword_pct, skills_pct, len(missing),
    )

    return ATSResult(
        ats_score=score,
        keyword_match_pct=keyword_pct,
        skills_match_pct=skills_pct,
        matched_keywords=matched,
        missing_keywords=missing,
        missing_skills=missing_skills,
        suggestions=_suggestions(resume, missing, keyword_pct, skills_pct),
    )


def _suggestions(resume: ResumeData, missing: list[str], keyword_pct: float, skills_pct: float) -> list[str]:
    tips: list[str] = []
    if missing:
        tips.append(f"Add these missing keywords where truthful: {', '.join(missing[:10])}.")
    if not resume.summary:
        tips.append("Add a professional summary tailored to the job (2-3 sentences).")
    if keyword_pct < 60:
        tips.append("Mirror the job description's terminology in your summary and experience bullets.")
    if not resume.skills:
        tips.append("Add a dedicated Skills section - ATS systems rely on it heavily.")
    elif skills_pct < 50:
        tips.append("Reorder your skills section so the most job-relevant skills appear first.")
    if resume.experience and not any(exp.bullets for exp in resume.experience):
        tips.append("Use bullet points in your experience section instead of paragraphs.")
    if not any(re.search(r"\d", b) for exp in resume.experience for b in exp.bullets):
        tips.append("Quantify achievements with numbers (%, $, team size) in your bullets.")
    if not resume.contact.linkedin:
        tips.append("Include your LinkedIn profile URL in the contact section.")
    if not tips:
        tips.append("Great coverage. Run AI optimization to polish wording and grammar.")
    return tips
