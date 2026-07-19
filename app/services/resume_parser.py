"""Parse raw resume text into structured ResumeData.

A fast heuristic parser is the default; an optional AI parser (Ollama)
gives better results for unusual layouts.
"""
import logging
import re

from pydantic import ValidationError
from app.ai.ollama_client import OllamaClient, OllamaError
from app.ai.prompts import PARSE_PROMPT, PARSE_SYSTEM
from app.domain.fact_guard import HallucinatedField
from app.services.parser_fact_guard import verify_parse
from app.schemas import ContactInfo, EducationItem, ExperienceItem, ParseWarning, ProjectItem, ResumeData

logger = logging.getLogger(__name__)

MAX_AI_PARSE_CHARACTERS = 40_000

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

    experience, exp_warnings = _parse_experience(sections.get("experience", []))

    return ResumeData(
        contact=contact,
        headline=headline,
        summary=" ".join(line.strip() for line in sections.get("summary", []) if line.strip()),
        skills=_parse_skills(sections.get("skills", [])),
        experience=experience,
        education=_parse_education(sections.get("education", [])),
        certifications=_parse_certifications(sections.get("certifications", [])),
        projects=_parse_projects(sections.get("projects", [])),
        languages=_parse_languages(sections.get("languages", [])),
        raw_text=text,
        parse_warnings=exp_warnings,
    )


def parse_resume_ai(text: str, client: OllamaClient) -> ResumeData:
    """AI-based parser using Ollama; falls back to the heuristic parser."""
    logger.info("Parsing resume with AI parser (%d chars)", len(text))

    bounded_text = text[:MAX_AI_PARSE_CHARACTERS]

    try:
        data = client.generate_json(PARSE_PROMPT.format(text=bounded_text), system=PARSE_SYSTEM)

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

        resume = ResumeData.model_validate(fields)

        # Normalize skills: deduplicate and clean
        resume.skills = _normalize_skills(resume.skills)

        # ── Parser fact guard: strip hallucinated fields ────────────────
        fact_result = verify_parse(resume, text)
        if fact_result.has_hallucinations:
            for h in fact_result.hallucinated_fields:
                _strip_hallucinated_field(resume, h)
            invalid_experience_bullets: dict[int, set[int]] = {}
            invalid_project_bullets: dict[int, set[int]] = {}
            for field in fact_result.hallucinated_fields:
                if field.section.startswith("experience_bullets:"):
                    invalid_experience_bullets.setdefault(
                        int(field.section.split(":", 1)[1]), set()
                    ).add(field.index)
                elif field.section.startswith("project_bullets:"):
                    invalid_project_bullets.setdefault(
                        int(field.section.split(":", 1)[1]), set()
                    ).add(field.index)
            for item_index, bullet_indexes in invalid_experience_bullets.items():
                if item_index < len(resume.experience):
                    for bullet_index in sorted(bullet_indexes, reverse=True):
                        if bullet_index < len(resume.experience[item_index].bullets):
                            del resume.experience[item_index].bullets[bullet_index]
            for item_index, bullet_indexes in invalid_project_bullets.items():
                if item_index < len(resume.projects):
                    for bullet_index in sorted(bullet_indexes, reverse=True):
                        if bullet_index < len(resume.projects[item_index].bullets):
                            del resume.projects[item_index].bullets[bullet_index]
            # Delete invalid certifications by reverse-sorted index
            invalid_cert_indexes = sorted(
                {
                    field.index
                    for field in fact_result.hallucinated_fields
                    if field.section == "certifications"
                },
                reverse=True,
            )
            for index in invalid_cert_indexes:
                if 0 <= index < len(resume.certifications):
                    del resume.certifications[index]
            # Remove blanked list items
            resume.skills = [s for s in resume.skills if s]
            resume.languages = [lang for lang in resume.languages if lang]
            resume.parse_warnings.extend(fact_result.warnings)
            logger.info(
                "Parser fact guard stripped %d hallucinated field(s)",
                len(fact_result.hallucinated_fields),
            )

        if len(text) > MAX_AI_PARSE_CHARACTERS:
            resume.parse_warnings.append(
                ParseWarning(
                    section="document",
                    line=0,
                    message=(
                        "The document was truncated before AI "
                        "parsing because it exceeded the safe limit."
                    ),
                )
            )

    except (OllamaError, ValidationError, ValueError, TypeError) as exc:
        logger.warning("AI parsing failed; using heuristic parser: %s", exc)
        resume = parse_resume(text)

    resume.raw_text = text
    return resume


def _strip_hallucinated_field(resume: ResumeData, h: HallucinatedField) -> None:
    """Remove or blank a hallucinated field."""
    if h.section == "experience" and h.index < len(resume.experience):
        setattr(resume.experience[h.index], h.field, "")
    elif h.section.startswith("experience_bullets:") and h.index is not None:
        return  # Removed in a reverse-sorted batch.
    elif h.section == "education" and h.index < len(resume.education):
        setattr(resume.education[h.index], h.field, "")
    elif h.section == "certifications" and h.index < len(resume.certifications):
        # Removed in a reverse-sorted batch after all findings are collected.
        return
    elif h.section == "skills" and h.index < len(resume.skills):
        resume.skills[h.index] = ""
    elif h.section == "projects" and h.index < len(resume.projects):
        setattr(resume.projects[h.index], h.field, "")
    elif h.section.startswith("project_bullets:") and h.index is not None:
        return  # Removed in a reverse-sorted batch.
    elif h.section == "languages" and h.index < len(resume.languages):
        resume.languages[h.index] = ""


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


def _normalize_skills(skills: list[str]) -> list[str]:
    """Deduplicate and clean skills from AI parser output.

    Preserves original case for display but deduplicates by lowercased form.
    """
    seen: set[str] = set()
    result: list[str] = []
    for skill in skills:
        cleaned = skill.strip(" .")
        if not cleaned or len(cleaned) >= 40:
            continue
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def _parse_experience(lines: list[str]) -> tuple[list[ExperienceItem], list[ParseWarning]]:
    items: list[ExperienceItem] = []
    warnings: list[ParseWarning] = []
    current: ExperienceItem | None = None
    line_num = 0
    for raw in lines:
        line_num += 1
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
            # Check if this looks like a new experience entry (short, title-case, no digits)
            stripped = line.strip()
            is_new_entry = (
                len(stripped) < 60
                and not stripped[0].islower()
                and not any(ch.isdigit() for ch in stripped)
                and not BULLET_RE.match(stripped)
            )
            if is_new_entry:
                # This is likely a new job title — don't merge into previous bullet
                items.append(current)
                current = ExperienceItem()
                parts = [
                    p.strip(" ,|\u2013\u2014-")
                    for p in re.split(r"\s*(?:\||,|\u2013|\u2014| at | @ )\s*", line)
                    if p.strip(" ,|\u2013\u2014-")
                ]
                if parts:
                    current.title = parts[0]
                if len(parts) > 1:
                    current.company = parts[1]
                continue
            warnings.append(ParseWarning(
                section="experience",
                line=line_num,
                message=(
                    f"Merged line into previous bullet (ambiguous): \"{line[:80]}\""
                ),
            ))
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
    return [item for item in items if item.title or item.bullets], warnings


_DEGREE_TERMS = {
    "bachelor", "master", "phd", "doctor", "diploma", "associate",
    "bsc", "msc", "mba",
}


def _split_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw in lines:
        line = BULLET_RE.sub("", raw).strip()
        if not line:
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _parse_education(lines: list[str]) -> list[EducationItem]:
    cleaned = [BULLET_RE.sub("", raw).strip() for raw in lines if raw.strip()]
    items: list[EducationItem] = []
    current: EducationItem | None = None

    for line in cleaned:
        is_degree = any(term in line.casefold() for term in _DEGREE_TERMS)
        if is_degree:
            if current is not None:
                items.append(current)
            parts = [part.strip() for part in re.split(r"\s*[·|]\s*", line) if part.strip()]
            if len(parts) == 1:
                comma_parts = [part.strip() for part in line.split(",") if part.strip()]
                parts = comma_parts if len(comma_parts) > 1 else parts
            parts = [
                part for part in parts
                if not re.fullmatch(r"(?:19|20)\d{2}(?:\s*[–-]\s*(?:19|20)\d{2})?", part)
            ]
            current = EducationItem(
                degree=parts[0],
                institution=" · ".join(parts[1:]),
            )
            inline_years = re.findall(r"\b(?:19|20)\d{2}\b", line)
            if inline_years:
                current.year = " – ".join(inline_years[-2:])
            continue

        years = re.findall(r"\b(?:19|20)\d{2}\b", line)
        if current is not None and years:
            current.year = " – ".join(years[-2:])
        elif current is not None and not current.institution:
            current.institution = line
        elif current is None:
            current = EducationItem(degree=line)

    if current is not None:
        items.append(current)
    return items


def _parse_certifications(lines: list[str]) -> list[str]:
    values: list[str] = []
    for raw in lines:
        line = BULLET_RE.sub("", raw).strip()
        if not line:
            continue
        for part in re.split(r"[;\u2022\u00b7|]", line):
            cert = part.strip(" .")
            if cert:
                values.append(cert)

    # Table-based resumes commonly flatten each certification into three
    # consecutive lines: name, issuer, year. Reassemble those records.
    if any(re.fullmatch(r"(?:19|20)\d{2}", value) for value in values):
        certs: list[str] = []
        pending: list[str] = []
        for value in values:
            pending.append(value)
            if re.fullmatch(r"(?:19|20)\d{2}", value):
                certs.append(" | ".join(pending))
                pending = []
        certs.extend(pending)
        return list(dict.fromkeys(certs))
    return list(dict.fromkeys(values))


def _parse_projects(lines: list[str]) -> list[ProjectItem]:
    """Same header/bullet grouping heuristic as _parse_experience, but
    projects only have a title, an optional context/date line, and
    bullets - no separate company field."""
    items: list[ProjectItem] = []
    current: ProjectItem | None = None

    def project_from_header(value: str) -> ProjectItem:
        dates = DATE_RANGE_RE.search(value)
        if not dates:
            return ProjectItem(title=value)
        title = DATE_RANGE_RE.sub("", value).strip(" ,|·–—-")
        start = dates.group(1).strip()
        end = dates.group(2).strip()
        return ProjectItem(
            title=title,
            meta=f"{start} – {end}",
            start_date=start,
            end_date=end,
        )
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
        # But only if it doesn't look like a new project title (has dates or is short title-like)
        if current is not None and current.bullets and not current.meta and not DATE_RANGE_RE.search(line):
            # Check if this looks like a new project title
            stripped = line.strip()
            is_new_title = (
                len(stripped) < 80
                and not stripped[0].islower()
                and not any(ch.isdigit() for ch in stripped)
                and not BULLET_RE.match(stripped)
            )
            if is_new_title:
                items.append(current)
                current = project_from_header(line)
                continue
            current.bullets[-1] += " " + line
            continue
        if current is not None:
            items.append(current)
        current = project_from_header(line)
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
