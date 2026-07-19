"""Select the most useful bounded job-description context for AI prompts."""
from app.services.ats_engine import _extract_section_text


def select_job_context(text: str, maximum_chars: int = 12_000) -> str:
    requirements = _extract_section_text(text)
    prioritized = (
        requirements + "\n\n" + text
        if requirements and requirements != text
        else text
    )
    if len(prioritized) <= maximum_chars:
        return prioritized
    half = maximum_chars // 2
    return prioritized[:half] + "\n\n[...]\n\n" + prioritized[-half:]
