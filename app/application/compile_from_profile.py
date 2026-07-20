"""Compile from Profile use-case: deterministic resume compilation from master profile."""
from __future__ import annotations

import logging
import threading

from app.domain.job_requirements import JobRequirements
from app.domain.master_profile import ResumeCompilerConfig
from app.domain.pipeline import PipelineResult

logger = logging.getLogger(__name__)


class CompileFromProfileUseCase:
    """Compile a targeted resume from the master career profile.

    This is a deterministic alternative to AI optimization — it selects
    and arranges existing career evidence based on relevance to a job.
    """

    def run(
        self,
        job_text: str = "",
        job_title: str = "",
        resume_id: int | None = None,
        job_id: int | None = None,
        config: ResumeCompilerConfig | None = None,
        cancel_event: threading.Event | None = None,
        progress=None,
    ) -> PipelineResult:
        from app.database.repositories.master_profile_repository import (
            MasterProfileRepository,
        )
        from app.services.profile_compiler import compile_resume

        def _emit(label: str, pct: int) -> None:
            if progress is not None:
                progress(label, pct)

        _emit("Loading master profile", 10)
        if cancel_event is not None and cancel_event.is_set():
            from app.ui.workers import OperationCancelled
            raise OperationCancelled("Cancelled")

        repo = MasterProfileRepository()
        profile = repo.get()
        if profile is None:
            raise ValueError(
                "No master profile found. "
                "Build a profile first from the Master Profile page."
            )

        _emit("Analyzing job requirements", 30)
        if cancel_event is not None and cancel_event.is_set():
            from app.ui.workers import OperationCancelled
            raise OperationCancelled("Cancelled")

        # Build job requirements from available text
        job_req = JobRequirements()
        if job_text:
            words = [
                w.strip()
                for w in job_text.split()
                if len(w.strip()) >= 3
            ]
            job_req = JobRequirements(
                required_skills=[
                    __import__(
                        "app.domain.job_requirements",
                        fromlist=["Requirement"],
                    ).Requirement(name=w)
                    for w in words[:30]
                ],
            )

        if config is None:
            config = ResumeCompilerConfig()

        _emit("Compiling resume", 60)
        if cancel_event is not None and cancel_event.is_set():
            from app.ui.workers import OperationCancelled
            raise OperationCancelled("Cancelled")

        compiled = compile_resume(profile, job_req, config)

        _emit("Converting to resume format", 85)
        optimized = _compiled_to_resume_data(compiled, profile)

        _emit("Complete", 100)

        from app.domain.fact_guard import FactGuardResult
        return PipelineResult(
            ats_before=None,
            optimized=optimized,
            cover_letter="",
            cover_letter_warnings=[],
            fact_guard=FactGuardResult(),
            ats_after_score=0,
            skill_gap=None,
            salary_estimate=None,
            duration_seconds=0.0,
            requires_review=False,
        )


def _compiled_to_resume_data(compiled, profile):
    """Convert a CompiledResume into a ResumeData for the pipeline."""
    from app.domain.resume import (
        ContactInfo,
        EducationItem,
        ExperienceItem,
        ResumeData,
    )

    contact = ContactInfo()
    headline = profile.headline or ""
    summary = ""
    experience: list[ExperienceItem] = []
    skills: list[str] = []
    education: list[EducationItem] = []
    certifications: list[str] = []
    projects = []

    for section in compiled.sections:
        if section.section_name == "Summary":
            for item in section.items:
                summary = item.text
        elif section.section_name == "Skills":
            for item in section.items:
                skills.append(item.text)
        elif section.section_name == "Education":
            for item in section.items:
                parts = item.text.split(" — ")
                degree = parts[0] if parts else ""
                inst_year = parts[1] if len(parts) > 1 else ""
                institution = inst_year.split("(")[0].strip()
                year = (
                    inst_year.split("(")[1].rstrip(")")
                    if "(" in inst_year
                    else ""
                )
                education.append(EducationItem(
                    degree=degree,
                    institution=institution,
                    year=year,
                ))
        elif section.section_name == "Certifications":
            for item in section.items:
                certifications.append(item.text)
        elif section.section_name == "Experience":
            # Group bullets by source entry
            entry_bullets: dict[int | None, list[str]] = {}
            for item in section.items:
                key = item.source_entry_id
                entry_bullets.setdefault(key, []).append(item.text)

            for entry_id, bullets in entry_bullets.items():
                # Find the entry in profile
                source_entry = None
                for e in profile.entries:
                    if e.id == entry_id:
                        source_entry = e
                        break
                if source_entry:
                    experience.append(ExperienceItem(
                        title=source_entry.role,
                        company=source_entry.company,
                        start_date=source_entry.date_from,
                        end_date=source_entry.date_to,
                        bullets=bullets,
                    ))

    return ResumeData(
        contact=contact,
        headline=headline,
        summary=summary,
        skills=skills,
        experience=experience,
        education=education,
        certifications=certifications,
        projects=projects,
    )
