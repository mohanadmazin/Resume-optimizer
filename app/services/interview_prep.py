"""Interview prep service — generate role-specific interview questions with STAR outlines."""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field

from app.ai.ollama_client import OllamaClient
from app.ai.prompts import (
    INTERVIEW_QUESTIONS_PROMPT,
    INTERVIEW_QUESTIONS_SYSTEM,
)
from app.domain.resume import ResumeData
from app.services.agent import _resume_to_text

logger = logging.getLogger(__name__)


class STAROutline(BaseModel):
    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""


class InterviewQuestion(BaseModel):
    category: str = ""
    question: str = ""
    star: STAROutline = Field(default_factory=STAROutline)


class InterviewQuestionsResult(BaseModel):
    questions: list[InterviewQuestion] = Field(default_factory=list)


class InterviewPrepService:
    """Generates interview questions with STAR outlines."""

    def __init__(self, client: OllamaClient | None = None) -> None:
        self._client = client or OllamaClient()

    def generate_questions(
        self,
        resume: ResumeData,
        role: str,
        company: str,
    ) -> InterviewQuestionsResult:
        resume_text = _resume_to_text(resume)

        prompt = INTERVIEW_QUESTIONS_PROMPT.format(
            resume_text=resume_text,
            role=role,
            company=company,
        )

        raw_text = self._client.generate(
            prompt=prompt,
            system=INTERVIEW_QUESTIONS_SYSTEM,
            json_mode=True,
        )

        try:
            raw_json = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.warning("Interview prep returned invalid JSON")
            return InterviewQuestionsResult()

        questions: list[InterviewQuestion] = []
        for item in raw_json.get("questions", []):
            star_data = item.get("star", {})
            questions.append(
                InterviewQuestion(
                    category=item.get("category", ""),
                    question=item.get("question", ""),
                    star=STAROutline(
                        situation=star_data.get("situation", ""),
                        task=star_data.get("task", ""),
                        action=star_data.get("action", ""),
                        result=star_data.get("result", ""),
                    ),
                )
            )

        return InterviewQuestionsResult(questions=questions)

    def to_markdown(self, result: InterviewQuestionsResult) -> str:
        """Convert interview questions to markdown for export."""
        lines: list[str] = ["# Interview Preparation\n"]

        categories = ["behavioral", "technical", "situational"]
        for cat in categories:
            cat_questions = [q for q in result.questions if q.category == cat]
            if not cat_questions:
                continue
            lines.append(f"\n## {cat.title()} Questions\n")
            for i, q in enumerate(cat_questions, 1):
                lines.append(f"### {i}. {q.question}\n")
                if q.star.situation:
                    lines.append(f"**Situation:** {q.star.situation}")
                if q.star.task:
                    lines.append(f"**Task:** {q.star.task}")
                if q.star.action:
                    lines.append(f"**Action:** {q.star.action}")
                if q.star.result:
                    lines.append(f"**Result:** {q.star.result}")
                lines.append("")

        return "\n".join(lines)
