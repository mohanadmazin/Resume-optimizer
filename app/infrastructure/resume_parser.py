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
from app.domain.certification import format_certification
from app.engines.parser_fact_guard import verify_parse
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
        "core technical skills",
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
        "selected project delivery",
        "selected projects",
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


def _normalise_location(value: str) -> str:
    """Clean spacing in a location without changing its wording."""
    return re.sub(r"\s*,\s*", ", ", re.sub(r"\s+", " ", value)).strip(" |")


def _location_from_contact_line(line: str) -> str:
    """Extract the non-contact segment from a combined header line.

    Many resumes put ``City, Country | phone | email | LinkedIn`` in one
    paragraph.  The old parser discarded the whole line as soon as it saw an
    email or phone, which also discarded the location.
    """
    if not (EMAIL_RE.search(line) or _find_phone(line) or "linkedin" in line.lower()):
        return ""
    for segment in re.split(r"\s*\|\s*", line):
        candidate = _normalise_location(segment)
        if not candidate:
            continue
        if EMAIL_RE.search(candidate) or _find_phone(candidate):
            continue
        if "linkedin" in candidate.lower() or re.search(r"https?://|www\.", candidate, re.I):
            continue
        if any(ch.isdigit() for ch in candidate):
            continue
        if 1 <= len(candidate.split()) <= 10 and len(candidate) < 100:
            return candidate
    return ""


def _parse_contact(header_lines: list[str], full_text: str) -> ContactInfo:
    contact = ContactInfo()

    email = EMAIL_RE.search(full_text)
    contact.email = email.group(0) if email else ""

    contact.phone = _find_phone("\n".join(header_lines) or full_text)

    linkedin = LINKEDIN_RE.search(full_text)
    contact.linkedin = linkedin.group(0) if linkedin else ""

    # Extract location before filtering contact-bearing lines.
    for raw in header_lines:
        location = _location_from_contact_line(raw.strip())
        if location:
            contact.location = location
            break

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

    if not contact.location:
        for line in cleaned[:6]:
            if "," in line and len(line) < 80:
                contact.location = _normalise_location(line)
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


def _split_role_header(value: str) -> list[str]:
    """Split title/company/location while preserving commas inside locations."""
    if re.search(r"[|\u00b7]", value):
        return [part.strip() for part in re.split(r"\s*[|\u00b7]\s*", value) if part.strip()]
    if re.search(r"\s+(?:at|@)\s+", value, re.I):
        return [part.strip() for part in re.split(r"\s+(?:at|@)\s+", value, maxsplit=1, flags=re.I) if part.strip()]
    # Legacy fallback for simple ``Title, Company`` headers.
    return [part.strip() for part in value.split(",", 1) if part.strip()]


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
        if (
            current is not None
            and current.title
            and not current.bullets
            and re.match(r"^(?:initially|assigned|seconded|contracted|promoted|concurrent)", line, re.I)
        ):
            current.bullets.append(line)
            continue
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
                parts = _split_role_header(line)
                if parts:
                    current.title = parts[0]
                if len(parts) > 1:
                    current.company = parts[1]
                if len(parts) > 2:
                    current.location = " | ".join(parts[2:])
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
        parts = _split_role_header(line)
        if parts:
            current.title = parts[0]
        if len(parts) > 1:
            current.company = parts[1]
        if len(parts) > 2:
            current.location = " | ".join(parts[2:])
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
    """Parse degree, institution, location, CGPA/GPA, and year range."""
    cleaned = [BULLET_RE.sub("", raw).strip() for raw in lines if raw.strip()]
    items: list[EducationItem] = []
    current: EducationItem | None = None

    for line in cleaned:
        is_degree = any(term in line.casefold() for term in _DEGREE_TERMS)
        if is_degree:
            if current is not None:
                items.append(current)

            years = re.findall(r"\b(?:19|20)\d{2}\b", line)
            year = " – ".join(years[-2:]) if years else ""
            cgpa_match = re.search(
                r"\b(?:CGPA|GPA)\s*:?\s*([0-9]+(?:\.[0-9]+)?(?:\s*/\s*[0-9]+(?:\.[0-9]+)?)?)",
                line,
                re.I,
            )
            cgpa = cgpa_match.group(1).replace(" ", "") if cgpa_match else ""

            body = DATE_RANGE_RE.sub("", line)
            body = re.sub(r"\|?\s*\b(?:CGPA|GPA)\s*:?\s*[0-9]+(?:\.[0-9]+)?(?:\s*/\s*[0-9]+(?:\.[0-9]+)?)?", "", body, flags=re.I)
            body = body.strip(" \t|·,–—-")

            degree = body
            institution = ""
            location = ""
            if ":" in body:
                left, right = body.split(":", 1)
                if any(term in left.casefold() for term in _DEGREE_TERMS):
                    degree, remainder = left.strip(), right.strip(" ,·|")
                    if "," in remainder:
                        institution, location = [part.strip() for part in remainder.rsplit(",", 1)]
                    else:
                        institution = remainder
            if not institution:
                parts = [part.strip() for part in re.split(r"\s*[·|]\s*", body) if part.strip()]
                degree = parts[0] if parts else body
                if len(parts) > 1:
                    institution = parts[1]
                if len(parts) > 2:
                    location = " | ".join(parts[2:])

            current = EducationItem(
                degree=degree,
                institution=institution,
                location=location,
                cgpa=cgpa,
                year=year,
            )
            continue

        years = re.findall(r"\b(?:19|20)\d{2}\b", line)
        cgpa_match = re.search(r"\b(?:CGPA|GPA)\s*:?\s*([0-9.]+(?:\s*/\s*[0-9.]+)?)", line, re.I)
        if current is not None and years:
            current.year = " – ".join(years[-2:])
        if current is not None and cgpa_match:
            current.cgpa = cgpa_match.group(1).replace(" ", "")
        elif current is not None and not current.institution:
            current.institution = line
        elif current is None:
            current = EducationItem(degree=line)

    if current is not None:
        items.append(current)
    return items


def _parse_certifications(lines: list[str]) -> list[str]:
    """Normalize certification rows to ``title | issuer | year`` strings."""
    certs: list[str] = []
    pending: list[str] = []

    for raw in lines:
        line = BULLET_RE.sub("", raw).strip()
        if not line:
            continue
        parts = [
            part.strip(" .")
            for part in re.split(r"\s*(?:\||\t+|;|\u2022|\u00b7)\s*", line)
            if part.strip(" .")
        ]
        if not parts:
            continue

        # A single extracted line may already contain all three columns.
        if len(parts) >= 2 and re.fullmatch(r"(?:19|20)\d{2}", parts[-1]):
            title = " | ".join(parts[:-2]) if len(parts) > 2 else parts[0]
            issuer = parts[-2] if len(parts) > 2 else ""
            certs.append(format_certification(title, issuer, parts[-1]))
            continue

        # Table extraction can also yield one value per line; collect until year.
        for value in parts:
            pending.append(value)
            if re.fullmatch(r"(?:19|20)\d{2}", value):
                title = " | ".join(pending[:-2]) if len(pending) > 2 else pending[0]
                issuer = pending[-2] if len(pending) > 2 else ""
                certs.append(format_certification(title, issuer, value))
                pending = []

    certs.extend(value for value in pending if value)
    return list(dict.fromkeys(certs))


def _parse_projects(lines: list[str]) -> list[ProjectItem]:
    """Same header/bullet grouping heuristic as _parse_experience, but
    projects only have a title, an optional context/date line, and
    bullets - no separate company field."""
    items: list[ProjectItem] = []
    current: ProjectItem | None = None

    def project_from_header(value: str) -> ProjectItem:
        dates = DATE_RANGE_RE.search(value)
        start = dates.group(1).strip() if dates else ""
        end = dates.group(2).strip() if dates else ""
        header = DATE_RANGE_RE.sub("", value).strip(" ,|·–—-\t") if dates else value.strip()
        parts = [part.strip() for part in re.split(r"\s*[|·]\s*", header) if part.strip()]
        title = parts[0] if parts else header
        context = " | ".join(parts[1:]) if len(parts) > 1 else ""
        return ProjectItem(
            title=title,
            meta=context,
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
