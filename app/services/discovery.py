"""Achievement Discovery Service — guided interview for uncovering quantified achievements."""
from __future__ import annotations

import logging
import re
from typing import Sequence

from app.domain.discovery import (
    AchievementResult,
    DiscoverySession,
    InterviewAnswer,
    InterviewQuestion,
    MetricStatus,
    QuestionCategory,
)

logger = logging.getLogger(__name__)

# ── Question bank ───────────────────────────────────────────────────

_ROLE_QUESTIONS: list[InterviewQuestion] = [
    InterviewQuestion(
        question_text="Tell me about your current role and main responsibilities.",
        context="Understanding your daily work helps identify hidden achievements.",
        category=QuestionCategory.ROLE,
        question_id="role_overview",
    ),
    InterviewQuestion(
        question_text="What project or accomplishment are you most proud of in this role?",
        context="Focus on concrete outcomes and results.",
        follow_ups=[
            "What was the measurable impact?",
            "How long did this take?",
        ],
        category=QuestionCategory.ACHIEVEMENT,
        question_id="proudest_achievement",
    ),
    InterviewQuestion(
        question_text="Describe a time you improved a process or system. What changed?",
        context="Process improvements often contain quantifiable metrics.",
        follow_ups=[
            "What was the before/after difference?",
            "What tools or technologies did you use?",
        ],
        category=QuestionCategory.ACHIEVEMENT,
        question_id="process_improvement",
    ),
    InterviewQuestion(
        question_text="Have you led or mentored anyone? Tell me about the impact.",
        context="Leadership and mentoring are strong achievement signals.",
        follow_ups=[
            "How many people were on your team?",
            "What was the outcome for the people you mentored?",
        ],
        category=QuestionCategory.IMPACT,
        question_id="leadership",
    ),
    InterviewQuestion(
        question_text="What technical challenges have you solved recently?",
        context="Technical problem-solving reveals depth of expertise.",
        follow_ups=[
            "What was the performance improvement?",
            "What tools or frameworks were involved?",
        ],
        category=QuestionCategory.CHALLENGE,
        question_id="technical_challenges",
    ),
    InterviewQuestion(
        question_text="Describe the scale of systems or projects you've worked on.",
        context="Scale metrics (users, data volume, traffic) strengthen resume claims.",
        follow_ups=[
            "What was the peak traffic or data volume?",
            "How did you ensure reliability at that scale?",
        ],
        category=QuestionCategory.SCALE,
        question_id="scale",
    ),
    InterviewQuestion(
        question_text="What certifications, awards, or recognitions have you received?",
        context="Formal recognition validates skills and achievements.",
        category=QuestionCategory.ACHIEVEMENT,
        question_id="certifications",
    ),
    InterviewQuestion(
        question_text="Tell me about a time you delivered a project under tight constraints.",
        context="Constraint delivery shows project management skill.",
        follow_ups=[
            "What was the deadline?",
            "What tradeoffs did you make?",
        ],
        category=QuestionCategory.ACHIEVEMENT,
        question_id="constraints",
    ),
    InterviewQuestion(
        question_text="What business value have you created (revenue, cost savings, efficiency)?",
        context="Business impact is the strongest achievement signal.",
        follow_ups=[
            "Can you quantify the dollar amount or percentage?",
            "How was this measured?",
        ],
        category=QuestionCategory.METRIC,
        question_id="business_value",
    ),
    InterviewQuestion(
        question_text="What unique skills or domain knowledge do you bring that others don't?",
        context="Differentiating skills are key to standing out.",
        category=QuestionCategory.TOOL,
        question_id="unique_skills",
    ),
]

_METRIC_PATTERNS = [
    (r"(\d+(?:\.\d+)?)\s*%", re.IGNORECASE, "percentage"),
    (r"\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(k|m|b|million|billion|thousand)?",
     re.IGNORECASE, "dollar"),
    (r"(\d+(?:,\d{3})*)\s*(users?|customers?|clients?|people|engineers?|developers?|members)",
     re.IGNORECASE, "people_count"),
    (r"(\d+(?:\.\d+)?)\s*(x|times|fold)\s*(faster|improvement|increase|reduction)?",
     re.IGNORECASE, "multiplier"),
    (r"(\d+)\s*(days?|weeks?|months?|hours?|minutes?)",
     re.IGNORECASE, "time_duration"),
    (r"(\d+(?:,\d{3})*)\s*(gb|tb|mb|pb|records?|rows?|transactions?)",
     re.IGNORECASE, "data_volume"),
    (r"(increased|improved|reduced|decreased|saved|cut)\s.*?(\d+(?:\.\d+)?)\s*%",
     re.IGNORECASE, "improvement_pct"),
]

_TOOLS_KEYWORDS = {
    "python", "java", "javascript", "typescript", "react", "vue", "angular",
    "django", "flask", "fastapi", "spring", "node.js", "aws", "gcp", "azure",
    "docker", "kubernetes", "terraform", "kafka", "redis", "postgresql",
    "mongodb", "elasticsearch", "graphql", "rest", "grpc", "ci/cd",
    "jenkins", "github actions", "gitlab ci", "snowflake", "spark", "airflow",
}


def start_interview(role: str = "") -> DiscoverySession:
    """Create a new discovery interview session."""
    session = DiscoverySession(role=role)
    if _ROLE_QUESTIONS:
        session.questions_asked.append(_ROLE_QUESTIONS[0])
        session.current_question_index = 1
    return session


def get_next_question(session: DiscoverySession) -> InterviewQuestion | None:
    """Return the next question, or None if interview is complete."""
    if session.is_complete:
        return None
    idx = session.current_question_index
    if idx >= len(_ROLE_QUESTIONS):
        session.is_complete = True
        return None
    question = _ROLE_QUESTIONS[idx]
    session.questions_asked.append(question)
    session.current_question_index = idx + 1
    if session.current_question_index >= session.max_questions:
        session.is_complete = True
    return question


def answer_question(
    session: DiscoverySession,
    answer_text: str,
) -> InterviewAnswer:
    """Process an answer, extract metrics, and return the answer record."""
    metrics = extract_metrics(answer_text)
    tools = extract_tools(answer_text)

    confidence = 0.5
    if metrics:
        confidence += 0.2
    if tools:
        confidence += 0.1
    if len(answer_text.split()) >= 20:
        confidence += 0.1
    confidence = min(confidence, 1.0)

    answer = InterviewAnswer(
        answer_text=answer_text,
        extracted_metrics=metrics,
        confidence=confidence,
    )
    session.answers.append(answer)
    return answer


def extract_metrics(text: str) -> list[str]:
    """Extract quantified metrics from free text."""
    found: list[str] = []
    for pattern, flags, label in _METRIC_PATTERNS:
        for match in re.finditer(pattern, text, flags):
            value = match.group(0).strip()
            if value and value not in found:
                found.append(f"{label}: {value}")
    return found


def extract_tools(text: str) -> list[str]:
    """Extract tool/technology names from text."""
    lower = text.lower()
    return sorted({t for t in _TOOLS_KEYWORDS if t in lower})


def extract_achievements(session: DiscoverySession) -> list[AchievementResult]:
    """Synthesize answers into AchievementResult objects."""
    achievements: list[AchievementResult] = []

    for answer in session.answers:
        if not answer.answer_text.strip():
            continue

        tools = extract_tools(answer.answer_text)
        metrics = extract_metrics(answer.answer_text)

        # Determine metric status
        metric_status = MetricStatus.UNAVAILABLE
        if metrics:
            metric_status = MetricStatus.ESTIMATE

        # Build statement from the answer
        statement = answer.answer_text.strip()
        if len(statement) > 200:
            statement = statement[:197] + "..."

        # Try to extract before/after values
        prev_val, curr_val = _extract_before_after(answer.answer_text)

        metric_dict: dict[str, str] = {}
        for m in metrics:
            parts = m.split(": ", 1)
            if len(parts) == 2:
                metric_dict[parts[0]] = parts[1]

        if statement:
            achievements.append(AchievementResult(
                statement=statement,
                metrics=metric_dict,
                previous_value=prev_val,
                current_value=curr_val,
                metric_status=metric_status,
                tools_used=tools,
                category=session.questions_asked[
                    session.answers.index(answer)
                ].category if session.answers.index(answer) < len(session.questions_asked) else QuestionCategory.ACHIEVEMENT,
            ))

    return achievements


def _extract_before_after(text: str) -> tuple[str, str]:
    """Try to extract before/after comparison from text."""
    patterns = [
        r"from\s+(\d+)\s+to\s+(\d+)",
        r"(?:went|changed|improved)\s+from\s+(\d+.*?)(?:\s+to\s+)(\d+.*?)(?:\.|,|$)",
        r"(?:before|was)\s+(\d+.*?)(?:\s*,?\s*(?:now|after|became|to))\s+(\d+.*?)(?:\.|,|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip()
    return "", ""


def store_achievements(
    achievements: Sequence[AchievementResult],
    session: DiscoverySession | None = None,
) -> list[int]:
    """Save achievements to the evidence vault as career facts."""
    from app.domain.evidence import CareerFact, FactConfidence, FactType
    from app.services.evidence_vault import EvidenceVault

    vault = EvidenceVault()
    fact_ids: list[int] = []

    for ach in achievements:
        fact_kwargs: dict = dict(
            statement=ach.statement,
            fact_type=FactType.ACHIEVEMENT,
            confidence=FactConfidence.USER_CONFIRMED,
        )
        if ach.metrics:
            fact_kwargs["metrics_json"] = ach.metrics
        fact = CareerFact(**fact_kwargs)
        fid = vault.add_fact(fact)
        fact_ids.append(fid)

    return fact_ids
