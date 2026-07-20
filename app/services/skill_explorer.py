"""AI Skills Explorer — suggest skills to add from job descriptions.

Deterministic skill suggestion based on keyword extraction from JDs,
compared against the candidate's existing skills. No AI calls needed.
"""
import re
from dataclasses import dataclass

from app.schemas import ResumeData


@dataclass
class SkillSuggestion:
    skill: str
    reason: str
    importance: int  # 1-5, 5 = critical
    in_jd: bool = True


def explore_skills(resume: ResumeData, jd_text: str) -> list[SkillSuggestion]:
    """Suggest skills the candidate should add based on the job description.

    Returns up to 10 skill suggestions sorted by importance descending.
    """
    resume_skills_lower = {s.lower() for s in resume.skills}
    seen: set[str] = set()
    suggestions: list[SkillSuggestion] = []

    # Extract potential skills from JD (if provided)
    if jd_text and jd_text.strip():
        jd_lower = jd_text.lower()
        jd_skills = _extract_jd_skills(jd_lower)

        for skill, importance, context in jd_skills:
            skill_lower = skill.lower()
            if skill_lower in resume_skills_lower or skill_lower in seen:
                continue
            if any(skill_lower in s for s in resume_skills_lower):
                continue
            seen.add(skill_lower)
            reason = f"Mentioned in JD: {context}" if context else "Required by job description"
            suggestions.append(SkillSuggestion(
                skill=skill,
                reason=reason,
                importance=importance,
                in_jd=True,
            ))

    # Check for common complementary skills (always, even without JD)
    complementary = _suggest_complementary(resume)
    for skill, reason in complementary:
        skill_lower = skill.lower()
        if skill_lower not in resume_skills_lower and skill_lower not in seen:
            seen.add(skill_lower)
            suggestions.append(SkillSuggestion(
                skill=skill,
                reason=reason,
                importance=2,
                in_jd=False,
            ))

    suggestions.sort(key=lambda s: s.importance, reverse=True)
    return suggestions[:10]


def _resume_skills_text(resume: ResumeData) -> str:
    parts = list(resume.skills)
    parts.extend(s.title for s in resume.experience if s.title)
    parts.extend(s.company for s in resume.experience if s.company)
    parts.extend(b for s in resume.experience for b in s.bullets)
    return " ".join(parts).lower()


# ── Skill extraction from JD ──────────────────────────────────────────────

# Known technical skills to look for in JD text
_TECH_SKILLS = {
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab",
    # Frameworks
    "django", "flask", "fastapi", "spring", "react", "vue", "angular",
    "node.js", "next.js", "rails", "laravel", ".net", "asp.net",
    "graphql", "tailwind", "bootstrap",
    # Databases
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "dynamodb", "sqlite", "oracle", "snowflake", "bigquery", "redshift",
    # Cloud & DevOps
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible",
    "jenkins", "github actions", "gitlab ci", "ci/cd", "helm", "argocd",
    "cloudflare", "nginx", "s3", "ec2", "lambda",
    # Data & Analytics
    "spark", "hadoop", "kafka", "airflow", "dbt",
    "tableau", "power bi", "looker", "pandas", "numpy",
    # AI/ML
    "tensorflow", "pytorch", "keras", "scikit-learn", "langchain",
    "openai", "machine learning", "deep learning", "nlp",
    "computer vision", "transformers", "llm",
    # Tools
    "git", "linux", "bash", "jira", "confluence", "postman", "figma", "jupyter",
    # Methodologies
    "agile", "scrum", "kanban", "devops", "tdd", "saas", "microservices",
    "serverless", "rest", "grpc",
    # Testing
    "pytest", "jest", "cypress", "selenium", "playwright", "junit",
    # Security
    "owasp", "ssl/tls", "oauth", "jwt",
}

# Context patterns for importance detection
_CRITICAL_PATTERNS = [
    re.compile(r"(?:must|required|need|essential|critical)\s+(?:experience\s+)?(?:with|in)\s+([a-z][a-z0-9+#.\s]{1,25})", re.I),
    re.compile(r"(?:required|minimum)\s+(?:skills?|qualifications?)\s*:?\s*(.+?)(?:\.|$)", re.I),
]
_IMPORTANT_PATTERNS = [
    re.compile(r"(?:preferred|nice[\s-]to[\s-]have|bonus|plus)\s+(?:experience\s+)?(?:with|in)\s+([a-z][a-z0-9+#.\s]{1,25})", re.I),
    re.compile(r"(?:experience|proficiency|familiar(?:ity)?)\s+(?:with|in)\s+([a-z][a-z0-9+#.\s]{1,25})", re.I),
]


def _extract_jd_skills(jd_lower: str) -> list[tuple[str, int, str]]:
    """Extract skills from JD text with importance scores."""
    found: dict[str, tuple[int, str]] = {}

    # Check critical patterns first (importance 5)
    for pattern in _CRITICAL_PATTERNS:
        for match in pattern.finditer(jd_lower):
            context = match.group(0).strip()
            tokens = set(re.findall(r"\b[a-z][a-z0-9+#.-]+\b", context))
            for skill in _TECH_SKILLS:
                if skill in tokens or skill in context:
                    if skill not in found or found[skill][0] < 5:
                        found[skill] = (5, context[:60])

    # Check important patterns (importance 3-4)
    for pattern in _IMPORTANT_PATTERNS:
        for match in pattern.finditer(jd_lower):
            context = match.group(0).strip()
            tokens = set(re.findall(r"\b[a-z][a-z0-9+#.-]+\b", context))
            for skill in _TECH_SKILLS:
                if skill in tokens or skill in context:
                    if skill not in found or found[skill][0] < 4:
                        found[skill] = (4, context[:60])

    # Direct mention scan (importance 2-3)
    for skill in _TECH_SKILLS:
        if skill in found:
            continue
        if skill in jd_lower:
            # Check if it appears in a requirements/qualifications section
            importance = 3 if _in_requirements_section(jd_lower, skill) else 2
            found[skill] = (importance, "mentioned in JD")

    return [(skill, imp, ctx) for skill, (imp, ctx) in found.items()]


def _in_requirements_section(jd_lower: str, skill: str) -> bool:
    section_headers = ["requirement", "qualification", "must have", "skill"]
    lines = jd_lower.split("\n")
    in_section = False
    for line in lines:
        stripped = line.strip()
        if any(h in stripped for h in section_headers) and len(stripped) < 50:
            in_section = True
            continue
        if in_section and not stripped:
            in_section = False
            continue
        if in_section and skill in stripped:
            return True
    return False


# ── Complementary skill suggestions ───────────────────────────────────────

_COMPLEMENTARY_MAP: dict[str, list[tuple[str, str]]] = {
    "python": [("fastapi", "Python web framework"), ("pytest", "Python testing")],
    "javascript": [("node.js", "JS runtime"), ("jest", "JS testing")],
    "react": [("next.js", "React framework"), ("typescript", "Type-safe JS")],
    "aws": [("terraform", "Infrastructure as Code"), ("docker", "Containerization")],
    "docker": [("kubernetes", "Container orchestration")],
    "kubernetes": [("helm", "K8s package manager")],
    "sql": [("postgresql", "Advanced SQL database")],
    "machine learning": [("pytorch", "ML framework"), ("tensorflow", "ML framework")],
    "devops": [("ci/cd", "Continuous delivery"), ("terraform", "IaC")],
}


def _suggest_complementary(resume: ResumeData) -> list[tuple[str, str]]:
    """Suggest complementary skills based on what's already in the resume."""
    skills_lower = {s.lower() for s in resume.skills}
    resume_text = _resume_skills_text(resume)
    suggestions: list[tuple[str, str]] = []

    for existing_skill, complements in _COMPLEMENTARY_MAP.items():
        if existing_skill in skills_lower or existing_skill in resume_text:
            for skill, reason in complements:
                if skill.lower() not in skills_lower:
                    suggestions.append((skill, f"Complements {existing_skill}: {reason}"))

    return suggestions[:5]
