from app.domain.resume import ContactInfo, ExperienceItem, ResumeData
from app.services.resume_parser import parse_resume

SAMPLE = """John Smith
Cairo, Egypt
john.smith@example.com | +20 100 123 4567 | linkedin.com/in/johnsmith

Summary
Software engineer with 6 years of experience building web applications.

Skills
Python, Django, PostgreSQL, Docker, AWS, REST APIs

Experience
Senior Software Engineer | Acme Corp | Jan 2021 - Present
- Built REST APIs in Django serving 2M requests per day
- Reduced infrastructure costs by 30% by containerizing services with Docker

Software Engineer | Beta Ltd | 2018 - 2020
- Developed internal tools in Python

Education
BSc Computer Science, Cairo University, 2018

Certifications
- AWS Certified Solutions Architect
"""


def test_contact():
    resume = parse_resume(SAMPLE)
    assert resume.contact.name == "John Smith"
    assert resume.contact.email == "john.smith@example.com"
    assert "linkedin.com" in resume.contact.linkedin
    assert resume.contact.phone


def test_summary_and_skills():
    resume = parse_resume(SAMPLE)
    assert "web applications" in resume.summary
    assert "Python" in resume.skills
    assert "Docker" in resume.skills


def test_experience():
    resume = parse_resume(SAMPLE)
    assert len(resume.experience) == 2
    first = resume.experience[0]
    assert first.title == "Senior Software Engineer"
    assert first.company == "Acme Corp"
    assert len(first.bullets) == 2


def test_education_and_certifications():
    resume = parse_resume(SAMPLE)
    assert resume.education
    assert resume.education[0].year == "2018"
    assert any("AWS" in cert for cert in resume.certifications)


def test_multiline_education_is_one_record():
    resume = parse_resume("""Jane Doe

Education
Bachelor of Science in Computer Science
University of Example
2018 - 2022
""")
    assert len(resume.education) == 1
    assert resume.education[0].institution == "University of Example"


def test_certification_comma_is_preserved():
    resume = parse_resume("""Jane Doe

Certifications
AWS Certified Solutions Architect, Associate
""")
    assert resume.certifications == ["AWS Certified Solutions Architect, Associate"]


def test_table_style_education_rows_stay_separate():
    resume = parse_resume("""Jane Doe

Education
Master of Science · Example University · GPA: 4.0
2019 – 2021
Bachelor of Science · Another University · GPA: 3.8
2015 – 2019
""")
    assert len(resume.education) == 2
    assert [item.year for item in resume.education] == ["2019 – 2021", "2015 – 2019"]


def test_parser_fact_guard_flags_hallucinated_contact():
    from app.services.parser_fact_guard import verify_parse

    resume = ResumeData(
        contact=ContactInfo(
            name="Alice Smith",
            email="alice@example.com",
            phone="+1-555-123-4567",
        ),
        skills=["Python"],
        experience=[
            ExperienceItem(
                title="Engineer",
                company="Acme",
                start_date="2020",
                end_date="Present",
                bullets=["Built APIs for internal tools"],
            )
        ],
    )
    raw_text = (
        "Alice Smith\n"
        "alice@example.com | +1-555-123-4567\n"
        "Built APIs for internal tools\n"
        "Acme\n"
        "Engineer\n"
        "2020 - Present\n"
        "Python"
    )
    result = verify_parse(resume, raw_text)
    assert not result.hallucinated_fields

    resume2 = ResumeData(
        contact=ContactInfo(
            name="Alice Smith",
            email="alice@example.com",
            phone="+1-555-999-0000",
        ),
        skills=["Python"],
        experience=[
            ExperienceItem(
                title="Engineer",
                company="Acme",
                start_date="2020",
                end_date="Present",
                bullets=["Built APIs for internal tools"],
            )
        ],
    )
    result2 = verify_parse(resume2, raw_text)
    assert any(f.field == "phone" for f in result2.hallucinated_fields)


def test_parser_removes_hallucinated_certifications():
    from app.services.parser_fact_guard import verify_parse

    resume = ResumeData(
        contact=ContactInfo(name="Alice"),
        certifications=["AWS SAA", "FAKE-CERT-XYZ-999"],
        skills=[],
    )
    raw_text = "Alice\nAWS SAA\n"
    result = verify_parse(resume, raw_text)
    assert any(
        f.section == "certifications" and f.extracted_value == "FAKE-CERT-XYZ-999"
        for f in result.hallucinated_fields
    )


def test_table_style_certification_fields_are_grouped():
    resume = parse_resume("""Jane Doe

Certifications
Security Professional
Certification Body
2025
Network Associate
Vendor
2024
""")
    assert resume.certifications == [
        "Security Professional | Certification Body | 2025",
        "Network Associate | Vendor | 2024",
    ]
