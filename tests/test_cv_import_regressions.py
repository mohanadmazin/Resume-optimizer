"""Regression coverage for the 2026 network-engineer resume layout."""
from pathlib import Path

import fitz

from app.domain.resume import ContactInfo, ResumeData
from app.exports.exporter import export_text_pdf, to_markdown
from app.services.ats_engine import analyze
from app.services.resume_parser import parse_resume


CV_TEXT = """MOHANAD A. FATHI
Project Engineer - Enterprise Network & Security | SD-WAN | SASE | Palo Alto
Kuala Lumpur,Malaysia | +601127670002 | mohanad@example.com | linkedin.com/in/example

PROFESSIONAL SUMMARY
Network engineer delivering enterprise deployments.

CORE TECHNICAL SKILLS
Network Architecture | SD-WAN | Palo Alto Networks | BGP | OSPF

PROFESSIONAL EXPERIENCE
Project Engineer · Example Sdn Bhd · Kuala Lumpur Sep 2024 - Present
• Delivered enterprise network projects.

SELECTED PROJECT DELIVERY
Data Center Build & SD-WAN Transformation | Project within Example role Mar 2025 - May 2025
• Migrated a live data center without downtime.

CERTIFICATIONS
SASE Advanced Security\tCato Networks\t2025
CCNP Routing & Switching\tCisco\t2014

EDUCATION
Master's degree in Computer Networks: Universiti Putra Malaysia (UPM), Selangor · GPA 3.625 | 2015-2019
Bachelor's degree in Computer Technology: Dijlah University College, Baghdad · GPA 3.7 | 2009-2013

LANGUAGES
English (Professional) | Arabic (Native)
"""


def test_cv_layout_parses_location_skills_projects_and_dates() -> None:
    resume = parse_resume(CV_TEXT)

    assert resume.contact.location == "Kuala Lumpur, Malaysia"
    assert resume.skills == [
        "Network Architecture",
        "SD-WAN",
        "Palo Alto Networks",
        "BGP",
        "OSPF",
    ]
    assert len(resume.experience) == 1
    assert resume.experience[0].location == "Kuala Lumpur"
    assert len(resume.projects) == 1
    assert resume.projects[0].title == "Data Center Build & SD-WAN Transformation"
    assert resume.projects[0].meta == "Project within Example role"
    assert resume.projects[0].start_date == "Mar 2025"
    assert resume.projects[0].end_date == "May 2025"
    assert resume.certifications[0] == "SASE Advanced Security | Cato Networks | 2025"


def test_cv_layout_parses_education_location_and_cgpa() -> None:
    resume = parse_resume(CV_TEXT)
    masters, bachelors = resume.education

    assert masters.institution == "Universiti Putra Malaysia (UPM)"
    assert masters.location == "Selangor"
    assert masters.cgpa == "3.625"
    assert masters.year == "2015 – 2019"
    assert bachelors.institution == "Dijlah University College"
    assert bachelors.location == "Baghdad"
    assert bachelors.cgpa == "3.7"

    markdown = to_markdown(resume)
    assert "Universiti Putra Malaysia (UPM), Selangor" in markdown
    assert "CGPA 3.625" in markdown


def test_ats_does_not_select_job_location_as_missing_keywords() -> None:
    resume = parse_resume(CV_TEXT)
    jd = """Security Architect
Kuala Lumpur, Federal Territory of Kuala Lumpur, Malaysia

Requirements:
- Network security and security architecture
- Palo Alto firewalls and SD-WAN
- BGP, OSPF and network segmentation
"""
    result = analyze(resume, jd)

    combined = " ".join(result.missing_keywords)
    assert "federal territory" not in combined
    assert "territory kuala" not in combined
    assert "lumpur malaysia" not in combined
    assert "network security" in result.missing_keywords
    assert "security architecture" in result.missing_keywords


def test_ats_uses_structured_revision_instead_of_stale_raw_text() -> None:
    resume = ResumeData(
        contact=ContactInfo(email="candidate@example.com", phone="60123456789"),
        summary="Python engineer",
        skills=["Python"],
        raw_text="Python Docker",  # stale imported source
    )
    jd = "Requirements:\nPython and Docker"

    before = analyze(resume, jd)
    assert "docker" in before.missing_keywords

    resume.skills.append("Docker")
    after = analyze(resume, jd)
    assert "docker" not in after.missing_keywords
    assert after.ats_score > before.ats_score


def test_cover_letter_pdf_export(tmp_path: Path) -> None:
    output = tmp_path / "cover-letter.pdf"
    export_text_pdf(
        "Dear Hiring Manager,\n\nI am applying for the Network Engineer role.\n\nSincerely,\nCandidate",
        str(output),
    )

    assert output.exists()
    with fitz.open(output) as document:
        assert document.page_count == 1
        text = "".join(page.get_text() for page in document)
    assert "Network Engineer role" in text
