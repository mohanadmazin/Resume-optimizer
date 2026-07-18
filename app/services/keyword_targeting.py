"""Deterministic keyword requirement matching for Rezi-style targeting."""
from app.domain.keyword_targeting import (
    JobRequirement, KeywordTarget, KeywordStatus, ResumeTextIndex
)
from typing import List

def match_requirement(
    requirement: JobRequirement,
    resume_index: ResumeTextIndex,
) -> KeywordTarget:
    from app.domain.keyword_targeting import normalize
    aliases = {normalize(requirement.name)} | {normalize(a) for a in requirement.aliases}
    evidence = resume_index.find_any(aliases)
    if evidence:
        status = KeywordStatus.PRESENT
    elif resume_index.find_semantic_overlap(requirement.name):
        status = KeywordStatus.PARTIAL
    else:
        status = KeywordStatus.MISSING
    return KeywordTarget(
        canonical_name=requirement.name,
        source_phrases=requirement.source_phrases,
        importance=requirement.importance,
        frequency_in_job=requirement.frequency,
        status=status,
        evidence_paths=[match.path for match in evidence],
        suggested_paths=suggest_placement_paths(requirement, resume_index),
        requires_user_confirmation=True,
    )

def suggest_placement_paths(requirement: JobRequirement, resume_index: ResumeTextIndex) -> List[str]:
    # MVP: suggest skills section and long experience bullets
    paths = []
    skills_path = "skills"
    if skills_path not in [p for p, _ in resume_index.path_text]:
        paths.append("skills")
    for path, text in resume_index.path_text:
        if "bullets" in path and len(text.split()) >= 5:
            paths.append(path)
    return paths[:4]
