"""Deterministic content quality checker — no AI, no network calls.

Scans resumes for weak words, passive voice, short bullets, missing metrics,
and summary issues. Returns a ContentCheckResult with issues and an overall
score from 0-100.
"""
import re

from app.domain.content_check import ContentCheckResult, ContentIssue, IssueType
from app.schemas import ResumeData

WEAK_WORDS = {
    "responsible for": "Replace with an action verb (led, built, delivered)",
    "assisted": "Use a stronger verb (led, implemented, drove)",
    "helped": "Use a stronger verb (delivered, facilitated, enabled)",
    "worked on": "Use a stronger verb (developed, built, implemented)",
    "familiar with": "State proficiency level or remove",
    "knowledge of": "State proficiency level or remove",
    "experience with": "State specific achievements instead",
    "various": "Be specific about what types",
    "multiple": "Use a specific number",
    "several": "Use a specific number",
    "many": "Use a specific number",
    "some": "Be more specific or remove",
    "a lot of": "Use a specific number",
    "thing": "Be specific about what thing",
    "stuff": "Be specific about what",
    "etc": "Be specific or remove",
    "duties included": "Use action verbs instead",
    "tasked with": "Use action verbs instead",
    "in charge of": "Use 'led' or 'managed' instead",
}

PASSIVE_PATTERNS = [
    re.compile(r"\b(?:was|were|is|are|been|being)\s+(?:\w+ed)\b", re.I),
    re.compile(r"\b(?:was|were|is|are)\s+(?:\w+en)\b", re.I),
]

ACTION_VERBS = {
    "led", "built", "developed", "implemented", "designed", "created",
    "delivered", "launched", "managed", "optimized", "reduced", "increased",
    "improved", "automated", "migrated", "deployed", "configured", "architected",
    "established", "initiated", "spearheaded", "orchestrated", "coordinated",
    "negotiated", "resolved", "streamlined", "consolidated", "scaled",
    "integrat", "monitor", "analy", "test", "debug", "refactor", "audit",
    "mentor", "coach", "recruit", "present", "report", "budget", "forecast",
    "architect", "prototype", "survey", "benchmark", "profil",
}


def check_content(resume: ResumeData) -> ContentCheckResult:
    """Run all deterministic content checks on a resume."""
    issues: list[ContentIssue] = []

    _check_summary(resume, issues)
    _check_contact(resume, issues)
    _check_experience_bullets(resume, issues)
    _check_project_bullets(resume, issues)

    score = _calculate_score(issues)
    return ContentCheckResult(issues=issues, score=score)


def _check_summary(resume: ResumeData, issues: list[ContentIssue]) -> None:
    summary = (resume.summary or "").strip()
    if not summary:
        issues.append(ContentIssue(
            issue_type=IssueType.SUMMARY_TOO_SHORT,
            severity="error",
            path="summary",
            message="No professional summary",
            suggestion="Add a 2-4 sentence summary highlighting your key qualifications",
        ))
        return

    word_count = len(summary.split())
    if word_count < 20:
        issues.append(ContentIssue(
            issue_type=IssueType.SUMMARY_TOO_SHORT,
            severity="warning",
            path="summary",
            message=f"Summary is too short ({word_count} words)",
            suggestion="Expand to 2-4 sentences (40-80 words) covering your experience and value",
        ))
    elif word_count > 150:
        issues.append(ContentIssue(
            issue_type=IssueType.SUMMARY_TOO_LONG,
            severity="warning",
            path="summary",
            message=f"Summary is too long ({word_count} words)",
            suggestion="Condense to 2-4 sentences (40-80 words) for maximum impact",
        ))

    _check_weak_words(summary, "summary", issues)


def _check_contact(resume: ResumeData, issues: list[ContentIssue]) -> None:
    contact = resume.contact
    if not contact.email:
        issues.append(ContentIssue(
            issue_type=IssueType.CONTACT_INCOMPLETE,
            severity="error",
            path="contact.email",
            message="Missing email address",
            suggestion="Add a professional email address",
        ))
    if not contact.phone:
        issues.append(ContentIssue(
            issue_type=IssueType.CONTACT_INCOMPLETE,
            severity="warning",
            path="contact.phone",
            message="Missing phone number",
            suggestion="Add a phone number for recruiter contact",
        ))
    if not contact.linkedin:
        issues.append(ContentIssue(
            issue_type=IssueType.CONTACT_INCOMPLETE,
            severity="info",
            path="contact.linkedin",
            message="Missing LinkedIn profile",
            suggestion="Add your LinkedIn URL for professional credibility",
        ))


def _check_experience_bullets(resume: ResumeData, issues: list[ContentIssue]) -> None:
    for i, exp in enumerate(resume.experience):
        path_prefix = f"experience[{i}]"

        for j, bullet in enumerate(exp.bullets):
            bullet_path = f"{path_prefix}.bullets[{j}]"
            _check_bullet(bullet, bullet_path, issues)


def _check_project_bullets(resume: ResumeData, issues: list[ContentIssue]) -> None:
    for i, proj in enumerate(resume.projects):
        path_prefix = f"projects[{i}]"

        for j, bullet in enumerate(proj.bullets):
            bullet_path = f"{path_prefix}.bullets[{j}]"
            _check_bullet(bullet, bullet_path, issues)


def _check_bullet(text: str, path: str, issues: list[ContentIssue]) -> None:
    text = text.strip()

    if len(text) < 40:
        issues.append(ContentIssue(
            issue_type=IssueType.SHORT_BULLET,
            severity="warning",
            path=path,
            message=f"Bullet is too short ({len(text)} chars)",
            suggestion="Expand to 1-2 lines with context, action, and result",
        ))

    if not re.search(r"\d", text):
        issues.append(ContentIssue(
            issue_type=IssueType.NO_METRICS,
            severity="info",
            path=path,
            message="Bullet has no quantified metrics",
            suggestion="Add numbers, percentages, or dollar amounts to quantify impact",
        ))

    words = text.split()
    if words and words[0][0].isupper():
        first_word = words[0].rstrip(":").lower()
        has_action = any(first_word.startswith(av) for av in ACTION_VERBS)
        if not has_action and not _looks_like_metric_first(words):
            issues.append(ContentIssue(
                issue_type=IssueType.BULLET_NO_ACTION,
                severity="info",
                path=path,
                message=f"Bullet starts with '{words[0]}' — consider an action verb",
                suggestion="Start bullets with strong action verbs (led, built, delivered, etc.)",
            ))

    _check_weak_words(text, path, issues)
    _check_passive_voice(text, path, issues)


def _looks_like_metric_first(words: list[str]) -> bool:
    if not words:
        return False
    first = words[0]
    return bool(re.match(r"^\d", first) or first.startswith("$") or first.startswith("€"))


def _check_weak_words(text: str, path: str, issues: list[ContentIssue]) -> None:
    text_lower = text.lower()
    for weak, suggestion in WEAK_WORDS.items():
        if weak in text_lower:
            issues.append(ContentIssue(
                issue_type=IssueType.WEAK_WORD,
                severity="warning",
                path=path,
                message=f"Contains weak phrase: '{weak}'",
                suggestion=suggestion,
            ))


def _check_passive_voice(text: str, path: str, issues: list[ContentIssue]) -> None:
    for pattern in PASSIVE_PATTERNS:
        match = pattern.search(text)
        if match:
            issues.append(ContentIssue(
                issue_type=IssueType.PASSIVE_VOICE,
                severity="info",
                path=path,
                message=f"Possible passive voice: '{match.group()}'",
                suggestion="Rewrite in active voice for stronger impact",
            ))
            return


def _calculate_score(issues: list[ContentIssue]) -> int:
    penalties = {
        "error": 15,
        "warning": 5,
        "info": 2,
    }
    score = 100
    for issue in issues:
        score -= penalties.get(issue.severity, 2)
    return max(0, score)
