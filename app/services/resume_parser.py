"""Parse raw resume text into structured ResumeData.

A fast heuristic parser is the default; an optional AI parser (Ollama)
gives better results for unusual layouts.
"""
import logging
import re

from pydantic import ValidationError
from app.ai.ollama_client import OllamaClient
from app.ai.prompts import PARSE_PROMPT, PARSE_SYSTEM
from app.schemas import ContactInfo, EducationItem, ExperienceItem, ProjectItem, ResumeData

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/[^\s|,]+", re.I)
BULLET_RE = re.compile(r"^\s*[\u2022\u00b7\u25aa\u2023*\-\u2013]\s+")
DATE_RANGE_RE = re.compile(
    r"(\d{4}|[A-Za-z]{3,9}\.?\s+\d{4})\s*(?:[-\u2013\u2014]|to)\s*(\d{4}|[A-Za-z]{3,9}\.?\s+\d{4}|present|current)",
    re.I,
)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")

SECTION_ALIASES = {
    "summary": {
        "summary",
        "professional summary",
        "profile",
        "objective",
        "career objective",
        "about",
        "about me",
    },
    "skills": {
        "skills",
        "technical skills",
        "core competencies",
        "key skills",
        "technologies",
        "core skills",
    },
    "experience": {
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "employment history",
        "work history",
    },
    "education": {
        "education",
        "academic background",
        "academics",
        "education and training",
    },
    "certifications": {
        "certifications",
        "certificates",
        "certifications and licenses",
        "certifications and training",
        "certifications training",
        "professional certifications",
        "licenses",
        "licenses and certifications",
        "courses and certifications",
        "professional certifications and training",
    },
    "projects": {
        "projects",
        "project experience",
        "key projects",
    },
    "languages": {
        "languages",
        "language",
    },
}


def _extract_headline(header_lines: list[str], name: str) -> str:
    for raw in header_lines:
        line = raw.strip()
        if not line:
            continue
        if line == name:
            continue
        if EMAIL_RE.search(line):
            continue
        if _find_phone(line):
            continue
        if "linkedin" in line.lower():
            continue
        if "," in line and len(line) < 80:
            continue
        if len(line) < 120:
            return line
    return ""


def parse_resume(text: str) -> ResumeData:
    """Heuristic section-based parser."""
    logger.info("Parsing resume with heuristic parser (%d chars)", len(text))
    lines = [line.rstrip() for line in text.splitlines()]

    sections: dict[str, list[str]] = {"header": []}
    current = "header"

    for line in lines:
        key = _match_section(line)
        if key:
            current = key
            sections.setdefault(key, [])
        else:
            sections.setdefault(current, []).append(line)

    contact = _parse_contact(sections.get("header", []), text)
    headline = _extract_headline(sections.get("header", []), contact.name)

    return ResumeData(
        contact=contact,
        headline=headline,
        summary=" ".join(l.strip() for l in sections.get("summary", []) if l.strip()),
        skills=_parse_skills(sections.get("skills", [])),
        experience=_parse_experience(sections.get("experience", [])),
        education=_parse_education(sections.get("education", [])),
        certifications=_parse_certifications(sections.get("certifications", [])),
        projects=_parse_projects(sections.get("projects", [])),
        languages=_parse_languages(sections.get("languages", [])),
        raw_text=text,
    )


def parse_resume_ai(text: str, client: OllamaClient) -> ResumeData:
    """AI-based parser using Ollama; falls back to the heuristic parser."""
    logger.info("Parsing resume with AI parser (%d chars)", len(text))
    data = client.generate_json(PARSE_PROMPT.format(text=text[:8000]), system=PARSE_SYSTEM)

    if "contact" not in data:
        data["contact"] = {
            "name": data.get("name", ""),
            "email": data.get("email", ""),
            "phone": data.get("phone", ""),
            "location": data.get("location", ""),
            "linkedin": data.get("linkedin", ""),
            "website": data.get("website", ""),
        }

    fields = {k: v for k, v in data.items() if k in ResumeData.model_fields}

    projects = fields.get("projects")
    if isinstance(projects, list):
        fields["projects"] = [
            {
                "title": p.get("title") or p.get("name") or "",
                "meta": p.get("meta") or " - ".join(
                    d for d in (p.get("start_date", ""), p.get("end_date", "")) if d
                ),
                "start_date": p.get("start_date", ""),
                "end_date": p.get("end_date", ""),
                "description": p.get("description", ""),
                "bullets": p.get("bullets") or ([p["description"]] if p.get("description") else []),
            }
            for p in projects
            if isinstance(p, dict)
        ]

    try:
        resume = ResumeData.model_validate(fields)
    except ValidationError:
        resume = parse_resume(text)

    resume.raw_text = text
    return resume


def _match_section(line: str) -> str | None:
    clean = re.sub(r"[^a-z ]", "", line.lower()).strip()
    clean = re.sub(r"\s+", " ", clean)
    if not clean or len(clean) > 40:
        return None
    for key, aliases in SECTION_ALIASES.items():
        if clean in aliases:
            return key
    return None


def _find_phone(text: str) -> str:
    for match in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        if 9 <= len(digits) <= 15:
            return match.group(0).strip()
    return ""


def _parse_contact(header_lines: list[str], full_text: str) -> ContactInfo:
    contact = ContactInfo()

    email = EMAIL_RE.search(full_text)
    contact.email = email.group(0) if email else ""

    contact.phone = _find_phone("\n".join(header_lines) or full_text)

    linkedin = LINKEDIN_RE.search(full_text)
    contact.linkedin = linkedin.group(0) if linkedin else ""

    cleaned = []
    for raw in header_lines:
        line = raw.strip()
        if (
            not line
            or EMAIL_RE.search(line)
            or _find_phone(line)
            or "linkedin" in line.lower()
        ):
            continue
        cleaned.append(line)

    for line in cleaned[:5]:
        if 2 <= len(line.split()) <= 6 and not any(ch.isdigit() for ch in line):
            contact.name = line
            break

    for line in cleaned[:6]:
        if "," in line and len(line) < 80:
            contact.location = line
            break

    return contact


def _parse_skills(lines: list[str]) -> list[str]:
    skills: list[str] = []
    seen: set[str] = set()
    for raw in lines:
        line = BULLET_RE.sub("", raw).strip()
        if not line:
            continue
        # Strip known category prefixes like "Networking: ", "Security: "
        while ":" in line and len(line.split(":", 1)[0].strip()) < 15:
            line = line.split(":", 1)[1].strip()
        for part in re.split(r"[,\u2022|;]|\s{2,}", line):
            skill = part.strip(" .")
            if skill and len(skill) < 40 and skill.lower() not in seen:
                seen.add(skill.lower())
                skills.append(skill)
    return skills


def _parse_experience(lines: list[str]) -> list[ExperienceItem]:
    items: list[ExperienceItem] = []
    current: ExperienceItem | None = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if BULLET_RE.match(raw):
            if current is None:
                current = ExperienceItem()
            current.bullets.append(BULLET_RE.sub("", raw).strip())
            continue
        dates = DATE_RANGE_RE.search(line)
        # Check if line looks like a new job title (contains · or multiple parts)
        is_title_line = bool(re.search(r"\u00b7| at | @ ", line)) or (len(line.split()) > 3 and dates)
        if current is not None and current.title and not current.bullets and not current.company and not is_title_line:
            # Likely a company / date line belonging to the previous header line.
            if dates:
                current.start_date = dates.group(1).strip()
                current.end_date = dates.group(2).strip()
                line = DATE_RANGE_RE.sub("", line).strip(" ,|\u2013\u2014-")
            if line:
                current.company = line
            continue
        # Continuation line: not a bullet, no dates, but current has bullets already
        if current is not None and current.bullets and not dates:
            current.bullets[-1] += " " + line
            continue
        if current is not None:
            items.append(current)
        current = ExperienceItem()
        if dates:
            current.start_date = dates.group(1).strip()
            current.end_date = dates.group(2).strip()
            line = DATE_RANGE_RE.sub("", line).strip(" ,|\u2013\u2014-")
        parts = [
            p.strip(" ,|\u2013\u2014-")
            for p in re.split(r"\s*(?:\||,|\u2013|\u2014| at | @ )\s*", line)
            if p.strip(" ,|\u2013\u2014-")
        ]
        if parts:
            current.title = parts[0]
        if len(parts) > 1:
            current.company = parts[1]
    if current is not None:
        items.append(current)
    return [item for item in items if item.title or item.bullets]


def _parse_education(lines: list[str]) -> list[EducationItem]:
    items: list[EducationItem] = []
    for raw in lines:
        line = BULLET_RE.sub("", raw).strip()
        if not line:
            continue
        year_match = YEAR_RE.search(line)
        parts = [p.strip() for p in re.split(r"\s*[,|]\s*|\s+[\u2013\u2014-]\s+", line) if p.strip()]
        parts = [p for p in parts if not YEAR_RE.fullmatch(p)]
        items.append(
            EducationItem(
                degree=parts[0] if parts else line,
                institution=parts[1] if len(parts) > 1 else "",
                year=year_match.group(0) if year_match else "",
            )
        )
    return items


def _parse_certifications(lines: list[str]) -> list[str]:
    certs: list[str] = []
    for raw in lines:
        line = BULLET_RE.sub("", raw).strip()
        if not line:
            continue
        for part in re.split(r"[,;]", line):
            cert = part.strip(" .")
            if cert:
                certs.append(cert)
    return certs


def _parse_projects(lines: list[str]) -> list[ProjectItem]:
    """Same header/bullet grouping heuristic as _parse_experience, but
    projects only have a title, an optional context/date line, and
    bullets - no separate company field."""
    items: list[ProjectItem] = []
    current: ProjectItem | None = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if BULLET_RE.match(raw):
            if current is None:
                current = ProjectItem()
            current.bullets.append(BULLET_RE.sub("", raw).strip())
            continue
        if current is not None and current.title and not current.bullets and not current.meta:
            # Likely a context/date line belonging to the previous title line.
            current.meta = line
            continue
        # Continuation line: not a bullet, no meta yet, current has bullets
        # But only if it doesn't look like a new project title (has dates)
        if current is not None and current.bullets and not current.meta and not DATE_RANGE_RE.search(line):
            current.bullets[-1] += " " + line
            continue
        if current is not None:
            items.append(current)
        current = ProjectItem(title=line)
    if current is not None:
        items.append(current)
    return [item for item in items if item.title or item.bullets]


def _parse_languages(lines: list[str]) -> list[str]:
    langs: list[str] = []
    for raw in lines:
        line = BULLET_RE.sub("", raw).strip()
        if not line:
            continue
        for part in re.split(r"[,;\u2022\u00b7|]", line):
            lang = part.strip(" .")
            if lang:
                langs.append(lang)
    return langs
