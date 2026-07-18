"""Versioned rule engine — individual findings instead of one opaque formula.

Every penalty links to a specific section or bullet.  The score changes
because visible findings were fixed—not because of a hidden formula.
"""
import logging
import re
from datetime import datetime, timezone

from app.domain.resume import ResumeData
from app.domain.scoring import (
    CATEGORY_WEIGHTS,
    CategoryScore,
    IssueSeverity,
    LayoutMetrics,
    ResumeIssue,
    ResumeScoreReport,
    ScoreCategory,
)

logger = logging.getLogger(__name__)

_RULESET_VERSION = "2026.1"

# ── Helpers ────────────────────────────────────────────────────────────────

_NUMBER_RE = re.compile(r"\d+")


def _has_numbers(text: str) -> bool:
    return bool(_NUMBER_RE.search(text))


def _bullet_text(exp_bullets: list[str]) -> str:
    return " ".join(exp_bullets)


# ── Content rules ──────────────────────────────────────────────────────────


def run_content_rules(resume: ResumeData) -> list[ResumeIssue]:
    issues: list[ResumeIssue] = []

    if not resume.summary or len(resume.summary.strip()) < 20:
        issues.append(ResumeIssue(
            code="CONTENT-001",
            category=ScoreCategory.CONTENT,
            severity=IssueSeverity.WARNING,
            path="summary",
            message="Summary is missing or too short.",
            recommendation="Add a 2–3 sentence professional summary tailored to the target role.",
            penalty=8,
        ))

    if not resume.skills:
        issues.append(ResumeIssue(
            code="CONTENT-002",
            category=ScoreCategory.CONTENT,
            severity=IssueSeverity.ERROR,
            path="skills",
            message="No skills section found.",
            recommendation="Add a dedicated Skills section listing relevant technical and soft skills.",
            penalty=12,
        ))
    elif len(resume.skills) < 3:
        issues.append(ResumeIssue(
            code="CONTENT-003",
            category=ScoreCategory.CONTENT,
            severity=IssueSeverity.WARNING,
            path="skills",
            message=f"Only {len(resume.skills)} skill(s) listed.",
            recommendation="Add more relevant skills to improve ATS keyword matching.",
            penalty=4,
        ))

    total_bullets = sum(len(exp.bullets) for exp in resume.experience)
    if total_bullets == 0 and resume.experience:
        issues.append(ResumeIssue(
            code="CONTENT-004",
            category=ScoreCategory.CONTENT,
            severity=IssueSeverity.ERROR,
            path="experience",
            message="Experience entries have no bullet points.",
            recommendation="Add bullet points describing achievements in each role.",
            penalty=15,
        ))

    quantified = sum(
        1 for exp in resume.experience
        for b in exp.bullets if _has_numbers(b)
    )
    if total_bullets > 0 and quantified == 0:
        issues.append(ResumeIssue(
            code="CONTENT-005",
            category=ScoreCategory.CONTENT,
            severity=IssueSeverity.WARNING,
            path="experience",
            message="No bullet points contain quantified achievements.",
            recommendation="Add metrics (%, $, team size, user count) to at least 3 bullets.",
            penalty=6,
        ))

    return issues


# ── Format rules ───────────────────────────────────────────────────────────


def run_format_rules(
    resume: ResumeData,
    layout: LayoutMetrics,
) -> list[ResumeIssue]:
    issues: list[ResumeIssue] = []

    if not resume.contact.email:
        issues.append(ResumeIssue(
            code="FORMAT-001",
            category=ScoreCategory.FORMAT,
            severity=IssueSeverity.ERROR,
            path="contact.email",
            message="Email address is missing.",
            recommendation="Add a professional email address to the contact section.",
            penalty=10,
        ))

    if not resume.contact.phone:
        issues.append(ResumeIssue(
            code="FORMAT-002",
            category=ScoreCategory.FORMAT,
            severity=IssueSeverity.WARNING,
            path="contact.phone",
            message="Phone number is missing.",
            recommendation="Add a phone number for recruiter follow-up.",
            penalty=5,
        ))

    if not resume.contact.linkedin:
        issues.append(ResumeIssue(
            code="FORMAT-003",
            category=ScoreCategory.FORMAT,
            severity=IssueSeverity.INFO,
            path="contact.linkedin",
            message="LinkedIn profile is missing.",
            recommendation="Add your LinkedIn profile URL.",
            penalty=2,
        ))

    if layout.word_count < 150:
        issues.append(ResumeIssue(
            code="FORMAT-004",
            category=ScoreCategory.FORMAT,
            severity=IssueSeverity.WARNING,
            path="document",
            message=f"Resume is very short ({layout.word_count} words).",
            recommendation="Aim for 300–800 words to provide sufficient detail.",
            penalty=6,
        ))
    elif layout.word_count > 1200:
        issues.append(ResumeIssue(
            code="FORMAT-005",
            category=ScoreCategory.FORMAT,
            severity=IssueSeverity.WARNING,
            path="document",
            message=f"Resume is very long ({layout.word_count} words).",
            recommendation="Trim to under 1000 words for a focused, readable resume.",
            penalty=4,
        ))

    if not layout.has_bullets:
        issues.append(ResumeIssue(
            code="FORMAT-006",
            category=ScoreCategory.FORMAT,
            severity=IssueSeverity.WARNING,
            path="experience",
            message="No bullet points detected in the document.",
            recommendation="Use bullet points instead of paragraphs for better readability.",
            penalty=5,
        ))

    return issues


# ── Optimization rules ────────────────────────────────────────────────────


def run_optimization_rules(
    resume: ResumeData,
    jd_text: str | None,
) -> list[ResumeIssue]:
    issues: list[ResumeIssue] = []

    if not jd_text or not jd_text.strip():
        return issues

    jd_lower = jd_text.lower()
    resume_text = _resume_lower(resume)

    # Check for high-weight JD keywords missing from resume
    jd_words = [
        w for w in re.findall(r"[a-z][a-z0-9+#.]{1,30}", jd_lower)
        if len(w) > 3
    ]
    from collections import Counter
    freq = Counter(jd_words)
    top_keywords = [w for w, _ in freq.most_common(20)]

    missing = [kw for kw in top_keywords if kw not in resume_text]
    if len(missing) >= 5:
        issues.append(ResumeIssue(
            code="OPT-001",
            category=ScoreCategory.OPTIMIZATION,
            severity=IssueSeverity.WARNING,
            path="document",
            message=f"Resume is missing {len(missing)} frequent job-description keywords.",
            recommendation=f"Consider incorporating: {', '.join(missing[:8])}.",
            penalty=10,
        ))
    elif len(missing) >= 2:
        issues.append(ResumeIssue(
            code="OPT-002",
            category=ScoreCategory.OPTIMIZATION,
            severity=IssueSeverity.INFO,
            path="document",
            message=f"Resume is missing {len(missing)} job-description keywords.",
            recommendation=f"Consider incorporating: {', '.join(missing[:5])}.",
            penalty=4,
        ))

    # Check headline relevance
    if resume.headline:
        headline_lower = resume.headline.lower()
        headline_words = set(re.findall(r"[a-z]{3,}", headline_lower))
        jd_skill_words = set(top_keywords[:10])
        overlap = headline_words & jd_skill_words
        if not overlap and jd_skill_words:
            issues.append(ResumeIssue(
                code="OPT-003",
                category=ScoreCategory.OPTIMIZATION,
                severity=IssueSeverity.INFO,
                path="headline",
                message="Headline does not reference any job-description keywords.",
                recommendation="Tailor your headline to mirror the target role's key terms.",
                penalty=3,
            ))

    return issues


# ── Best-practice rules ───────────────────────────────────────────────────


def run_best_practice_rules(resume: ResumeData) -> list[ResumeIssue]:
    issues: list[ResumeIssue] = []

    if resume.experience:
        empty_titles = [
            i for i, exp in enumerate(resume.experience)
            if not exp.title.strip()
        ]
        if empty_titles:
            issues.append(ResumeIssue(
                code="BP-001",
                category=ScoreCategory.BEST_PRACTICES,
                severity=IssueSeverity.WARNING,
                path=f"experience[{empty_titles[0]}].title",
                message=f"{len(empty_titles)} experience entry/entries missing a job title.",
                recommendation="Every experience entry should have a clear job title.",
                penalty=6,
            ))

        empty_companies = [
            i for i, exp in enumerate(resume.experience)
            if not exp.company.strip()
        ]
        if empty_companies:
            issues.append(ResumeIssue(
                code="BP-002",
                category=ScoreCategory.BEST_PRACTICES,
                severity=IssueSeverity.INFO,
                path=f"experience[{empty_companies[0]}].company",
                message=f"{len(empty_companies)} experience entry/entries missing a company name.",
                recommendation="Add company names for credibility and context.",
                penalty=3,
            ))

        short_bullets = [
            (i, j, b)
            for i, exp in enumerate(resume.experience)
            for j, b in enumerate(exp.bullets)
            if 0 < len(b.split()) < 4
        ]
        if short_bullets:
            i, j, b = short_bullets[0]
            issues.append(ResumeIssue(
                code="BP-003",
                category=ScoreCategory.BEST_PRACTICES,
                severity=IssueSeverity.INFO,
                path=f"experience[{i}].bullets[{j}]",
                message=f"Bullet is very short: \"{b[:50]}\".",
                recommendation="Expand bullets to 8–20 words describing impact and context.",
                penalty=2,
            ))

    if resume.education:
        empty_degrees = [
            i for i, edu in enumerate(resume.education)
            if not edu.degree.strip()
        ]
        if empty_degrees:
            issues.append(ResumeIssue(
                code="BP-004",
                category=ScoreCategory.BEST_PRACTICES,
                severity=IssueSeverity.INFO,
                path=f"education[{empty_degrees[0]}].degree",
                message="An education entry is missing a degree name.",
                recommendation="Add the degree or certification name.",
                penalty=2,
            ))

    return issues


# ── Application-readiness rules ───────────────────────────────────────────


def run_readiness_rules(
    resume: ResumeData,
    jd_text: str | None,
) -> list[ResumeIssue]:
    issues: list[ResumeIssue] = []

    if not resume.contact.name:
        issues.append(ResumeIssue(
            code="READY-001",
            category=ScoreCategory.APPLICATION_READY,
            severity=IssueSeverity.ERROR,
            path="contact.name",
            message="Candidate name is missing.",
            recommendation="Add your full name to the contact section.",
            penalty=10,
        ))

    if not resume.contact.email and not resume.contact.phone:
        issues.append(ResumeIssue(
            code="READY-002",
            category=ScoreCategory.APPLICATION_READY,
            severity=IssueSeverity.ERROR,
            path="contact",
            message="No contact method (email or phone) is provided.",
            recommendation="Add at least an email address or phone number.",
            penalty=12,
        ))

    if jd_text and jd_text.strip():
        has_any_match = False
        resume_text = _resume_lower(resume)
        jd_words = set(re.findall(r"[a-z]{4,}", jd_text.lower()))
        for w in jd_words:
            if w in resume_text:
                has_any_match = True
                break
        if not has_any_match:
            issues.append(ResumeIssue(
                code="READY-003",
                category=ScoreCategory.APPLICATION_READY,
                severity=IssueSeverity.WARNING,
                path="document",
                message="Resume shares no common words with the job description.",
                recommendation="Rewrite summary and bullets to reflect the job's language.",
                penalty=8,
            ))

    return issues


# ── Builder ────────────────────────────────────────────────────────────────


def _resume_lower(resume: ResumeData) -> str:
    parts = [resume.headline, resume.summary, " ".join(resume.skills)]
    for exp in resume.experience:
        parts += [exp.title, exp.company, " ".join(exp.bullets)]
    for proj in resume.projects:
        parts += [proj.title, proj.meta, " ".join(proj.bullets)]
    for edu in resume.education:
        parts += [edu.degree, edu.institution]
    parts += resume.certifications
    return " ".join(p for p in parts if p).lower()


def build_score_report(
    resume: ResumeData,
    jd_text: str | None,
    layout: LayoutMetrics,
) -> ResumeScoreReport:
    issues = [
        *run_content_rules(resume),
        *run_format_rules(resume, layout),
        *run_optimization_rules(resume, jd_text),
        *run_best_practice_rules(resume),
        *run_readiness_rules(resume, jd_text),
    ]

    category_scores: list[CategoryScore] = []

    for category, weight in CATEGORY_WEIGHTS.items():
        category_issues = [
            issue
            for issue in issues
            if issue.category == category
        ]

        score = max(
            0,
            round(
                100
                - sum(
                    issue.penalty
                    for issue in category_issues
                )
            ),
        )

        category_scores.append(
            CategoryScore(
                category=category,
                score=score,
                weight=weight,
                issues=category_issues,
            )
        )

    overall = round(
        sum(
            category.score * category.weight
            for category in category_scores
        )
    )

    return ResumeScoreReport(
        ruleset_version=_RULESET_VERSION,
        overall_score=overall,
        categories=category_scores,
        generated_at=datetime.now(timezone.utc),
    )
