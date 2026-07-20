"""LinkedIn data import service — parse LinkedIn data export (JSON/CSV)."""
from __future__ import annotations

import csv
import io
import json
import logging
from pathlib import Path

from app.domain.resume import (
    ContactInfo,
    EducationItem,
    ExperienceItem,
    ResumeData,
)

logger = logging.getLogger(__name__)


def _parse_linkedin_json(path: Path) -> ResumeData:
    """Parse a LinkedIn data export JSON file into ResumeData."""
    raw = json.loads(path.read_text(encoding="utf-8"))

    contact = ContactInfo()
    if "firstName" in raw or "lastName" in raw:
        first = raw.get("firstName", "")
        last = raw.get("lastName", "")
        contact = ContactInfo(
            name=f"{first} {last}".strip(),
            email=raw.get("emailAddress", ""),
            phone=raw.get("phoneNumbers", [{}])[0].get("number", "") if raw.get("phoneNumbers") else "",
            location=raw.get("address", ""),
            linkedin=raw.get("profileHandle", ""),
        )

    headline = raw.get("headline", "")
    summary = raw.get("summary", "")

    skills: list[str] = []
    for s in raw.get("skills", []):
        name = s.get("name", "") if isinstance(s, dict) else str(s)
        if name:
            skills.append(name)

    experience: list[ExperienceItem] = []
    for pos in raw.get("positions", []):
        company = pos.get("companyName", "")
        title = pos.get("title", "")
        start = ""
        end = ""
        if "timePeriod" in pos:
            tp = pos["timePeriod"]
            start_date = tp.get("startDate", {})
            end_date = tp.get("endDate", {})
            start = f"{start_date.get('month', '')} {start_date.get('year', '')}".strip()
            end = f"{end_date.get('month', '')} {end_date.get('year', '')}".strip() or "Present"
        bullets = []
        if pos.get("description"):
            bullets = [line.strip() for line in pos["description"].split("\n") if line.strip()]

        experience.append(
            ExperienceItem(
                title=title,
                company=company,
                start_date=start,
                end_date=end,
                bullets=bullets,
            )
        )

    education: list[EducationItem] = []
    for edu in raw.get("educations", []):
        school = edu.get("schoolName", "")
        degree = edu.get("degree", "") or edu.get("fieldOfStudy", "")
        year = ""
        if "timePeriod" in edu:
            tp = edu["timePeriod"]
            start = tp.get("startDate", {})
            end = tp.get("endDate", {})
            start_y = start.get("year", "")
            end_y = end.get("year", "")
            year = f"{start_y}-{end_y}" if start_y and end_y else str(end_y or start_y)
        education.append(
            EducationItem(degree=degree, institution=school, year=year)
        )

    return ResumeData(
        contact=contact,
        headline=headline,
        summary=summary,
        skills=skills,
        experience=experience,
        education=education,
    )


def _parse_linkedin_csv(path: Path) -> ResumeData:
    """Parse a LinkedIn connections CSV export into a minimal ResumeData."""
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    contact = ContactInfo()
    experience: list[ExperienceItem] = []
    skills: list[str] = []

    for row in reader:
        first = row.get("First Name", "")
        last = row.get("Last Name", "")
        if first or last:
            contact = ContactInfo(
                name=f"{first} {last}".strip(),
                email=row.get("Email Address", ""),
            )
        company = row.get("Company", "")
        title = row.get("Position", "")
        if company or title:
            experience.append(
                ExperienceItem(title=title, company=company)
            )
        raw_skills = row.get("Skills", "")
        if raw_skills:
            skills.extend(s.strip() for s in raw_skills.split(";") if s.strip())

    return ResumeData(
        contact=contact,
        skills=skills,
        experience=experience,
    )


def import_linkedin(path: Path) -> ResumeData:
    """Import a LinkedIn data export file into ResumeData.

    Supports JSON (full export) and CSV (connections export).
    """
    suffix = path.suffix.lower()

    if suffix == ".json":
        return _parse_linkedin_json(path)
    elif suffix == ".csv":
        return _parse_linkedin_csv(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use .json or .csv")
