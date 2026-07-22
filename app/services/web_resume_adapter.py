"""Convert between the standalone builder state and canonical ResumeData."""
from __future__ import annotations

from copy import deepcopy

from app.domain.resume import ContactInfo, EducationItem, ExperienceItem, ProjectItem, ResumeData


def _lines(value: str) -> list[str]:
    return [line.strip(" •\t") for line in str(value or "").splitlines() if line.strip(" •\t")]


def _location(contact: dict) -> str:
    visibility = contact.get("visibility") or {}
    values = []
    for key in ("city", "state", "country"):
        if visibility.get(key, True) and str(contact.get(key, "")).strip():
            values.append(str(contact[key]).strip())
    # Preserve order while removing duplicates.
    return ", ".join(dict.fromkeys(values))


def builder_to_resume(state: dict) -> ResumeData:
    contact = state.get("contact") or {}
    summary = state.get("summary") or {}
    experience = []
    for item in state.get("experience") or []:
        experience.append(ExperienceItem(
            title=str(item.get("title", "")).strip(),
            company=str(item.get("company", "")).strip(),
            location=str(item.get("location", "")).strip(),
            start_date=str(item.get("start", "")).strip(),
            end_date=str(item.get("end", "")).strip(),
            bullets=_lines(item.get("description", "")),
        ))
    projects = []
    for item in state.get("project") or []:
        description_lines = _lines(item.get("description", ""))
        role = str(item.get("role", "")).strip()
        link = str(item.get("link", "")).strip()
        meta = ", ".join(value for value in [role, str(item.get("tools", "")).strip(), link] if value)
        projects.append(ProjectItem(
            title=str(item.get("name", "")).strip(),
            meta=meta,
            start_date=str(item.get("start", "")).strip(),
            end_date=str(item.get("end", "")).strip(),
            description="",
            bullets=description_lines,
        ))
    education = []
    for item in state.get("education") or []:
        degree = str(item.get("qualification", "")).strip()
        field = str(item.get("field", "")).strip()
        if field and field.casefold() not in degree.casefold():
            degree = f"{degree}, {field}" if degree else field
        education.append(EducationItem(
            degree=degree,
            institution=str(item.get("institution", "")).strip(),
            location=str(item.get("location", "")).strip(),
            cgpa=str(item.get("grade", "")).strip(),
            year=str(item.get("end", "")).strip() or str(item.get("start", "")).strip(),
        ))
    certifications = []
    for item in state.get("certifications") or []:
        if isinstance(item, str):
            value = item.strip()
        else:
            value = " — ".join(v for v in [str(item.get("name", "")).strip(), str(item.get("issuer", "")).strip()] if v)
            issue = str(item.get("issue", "")).strip()
            if issue:
                value = f"{value} ({issue})" if value else issue
        if value:
            certifications.append(value)
    skills = []
    for item in state.get("skills") or []:
        value = item if isinstance(item, str) else item.get("name", "")
        value = str(value).strip()
        if value:
            skills.append(value)
    coursework = state.get("coursework") or {}
    coursework_items = _lines(coursework.get("courseworkItems", ""))
    if coursework_items:
        label = str(coursework.get("courseworkTitle", "Relevant Coursework")).strip()
        skills.extend(f"{label}: {item}" for item in coursework_items)

    return ResumeData(
        contact=ContactInfo(
            name=str(contact.get("fullName", "")).strip(),
            email=str(contact.get("email", "")).strip(),
            phone=str(contact.get("phone", "")).strip(),
            location=_location(contact),
            linkedin=str(contact.get("linkedin", "")).strip(),
            website=str(contact.get("website", "")).strip(),
        ),
        headline=str(summary.get("professionalTitle", "")).strip(),
        summary=str(summary.get("summaryText", "")).strip(),
        skills=list(dict.fromkeys(skills)),
        experience=experience,
        education=education,
        certifications=certifications,
        projects=projects,
    )


def resume_to_builder(resume: ResumeData, *, year: str = "", resume_id: int | None = None) -> dict:
    location = [part.strip() for part in (resume.contact.location or "").split(",") if part.strip()]
    city = location[0] if location else ""
    state_name = location[1] if len(location) > 1 else ""
    country = location[2] if len(location) > 2 else (location[-1] if location else "Malaysia")
    data = {
        "resumeId": resume_id,
        "year": year or "2026",
        "contact": {
            "fullName": resume.contact.name,
            "email": resume.contact.email,
            "phone": resume.contact.phone,
            "linkedin": resume.contact.linkedin,
            "website": resume.contact.website,
            "country": country,
            "state": state_name,
            "city": city,
            "visibility": {"country": True, "state": True, "city": True},
        },
        "experience": [
            {
                "title": item.title,
                "company": item.company,
                "location": item.location,
                "type": "Full-time",
                "start": item.start_date,
                "end": item.end_date,
                "description": "\n".join(item.bullets),
            }
            for item in resume.experience
        ],
        "project": [
            {
                "name": item.title,
                "role": "",
                "link": "",
                "tools": item.meta,
                "start": item.start_date,
                "end": item.end_date,
                "description": "\n".join(item.bullets) or item.description,
            }
            for item in resume.projects
        ],
        "education": [
            {
                "qualification": item.degree,
                "institution": item.institution,
                "field": "",
                "location": item.location,
                "start": "",
                "end": item.year,
                "grade": item.cgpa,
                "honours": "",
                "description": "",
            }
            for item in resume.education
        ],
        "certifications": [
            {"name": item, "issuer": "", "issue": "", "expiry": "", "credentialId": "", "url": ""}
            for item in resume.certifications
        ],
        "coursework": {"courseworkTitle": "Relevant Coursework", "courseworkInstitution": "", "courseworkItems": ""},
        "skills": [{"name": item, "level": "Intermediate"} for item in resume.skills],
        "summary": {"professionalTitle": resume.headline, "summaryText": resume.summary},
        "coverLetter": {
            "coverJobTitle": "", "coverCompany": "", "coverHiringManager": "",
            "coverTone": "Professional", "jobDescription": "", "output": "",
        },
    }
    return deepcopy(data)
