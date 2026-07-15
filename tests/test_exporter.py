from app.exports.exporter import to_markdown
from app.schemas import ContactInfo, EducationItem, ExperienceItem, ResumeData


def _resume() -> ResumeData:
    return ResumeData(
        contact=ContactInfo(name="Jane Doe", email="jane@example.com"),
        summary="Backend developer.",
        skills=["Python", "SQL"],
        experience=[
            ExperienceItem(
                title="Developer",
                company="Acme",
                start_date="2020",
                end_date="Present",
                bullets=["Built things"],
            )
        ],
        education=[EducationItem(degree="BSc CS", institution="MIT", year="2019")],
        certifications=["AWS SAA"],
    )


def test_markdown_structure():
    md = to_markdown(_resume())
    assert "# Jane Doe" in md
    assert "## Summary" in md
    assert "## Skills" in md
    assert "Python, SQL" in md
    assert "### Developer - Acme (2020 - Present)" in md
    assert "- Built things" in md
    assert "## Education" in md
    assert "- AWS SAA" in md


def test_markdown_minimal_resume():
    md = to_markdown(ResumeData())
    assert md.startswith("# Resume")
