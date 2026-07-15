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
