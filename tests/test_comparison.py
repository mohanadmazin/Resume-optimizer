"""Tests for resume comparison service."""
from __future__ import annotations


from app.schemas import (
    ContactInfo,
    ExperienceItem,
    ResumeData,
)
from app.services.resume_comparison import compare_resumes


def _make_resume(**overrides) -> ResumeData:
    base = dict(
        contact=ContactInfo(name="Jane Doe", email="jane@test.com"),
        headline="Software Engineer",
        summary="Experienced developer.",
        skills=["Python", "SQL"],
        experience=[
            ExperienceItem(
                title="Engineer",
                company="Acme",
                start_date="2020-01",
                end_date="2023-01",
                bullets=["Built stuff.", "Fixed things."],
            )
        ],
        education=[],
        certifications=[],
    )
    base.update(overrides)
    return ResumeData(**base)


class TestCompareResumes:
    def test_identical_resumes(self):
        r = _make_resume()
        comp = compare_resumes(r, r)
        assert comp.total_changes == 0
        assert not comp.name.changed
        assert not comp.summary.changed
        assert not comp.skills_changed

    def test_name_changed(self):
        old = _make_resume()
        new = _make_resume(contact=ContactInfo(name="John Smith", email="jane@test.com"))
        comp = compare_resumes(old, new)
        assert comp.name.changed
        assert comp.name.old_value == "Jane Doe"
        assert comp.name.new_value == "John Smith"
        assert comp.total_changes == 1

    def test_summary_changed(self):
        old = _make_resume()
        new = _make_resume(summary="Senior developer with 10 years.")
        comp = compare_resumes(old, new)
        assert comp.summary.changed
        assert comp.total_changes == 1

    def test_skills_changed(self):
        old = _make_resume()
        new = _make_resume(skills=["Python", "SQL", "Rust"])
        comp = compare_resumes(old, new)
        assert comp.skills_changed
        assert "Rust" in comp.skills_new

    def test_experience_title_changed(self):
        old = _make_resume()
        new = _make_resume(experience=[
            ExperienceItem(
                title="Senior Engineer",
                company="Acme",
                start_date="2020-01",
                end_date="2023-01",
                bullets=["Built stuff.", "Fixed things."],
            )
        ])
        comp = compare_resumes(old, new)
        assert len(comp.experience) == 1
        assert comp.experience[0].title.changed
        assert comp.experience[0].title.new_value == "Senior Engineer"

    def test_experience_bullet_changed(self):
        old = _make_resume()
        new = _make_resume(experience=[
            ExperienceItem(
                title="Engineer",
                company="Acme",
                start_date="2020-01",
                end_date="2023-01",
                bullets=["Built robust stuff.", "Fixed things."],
            )
        ])
        comp = compare_resumes(old, new)
        bullets = comp.experience[0].bullets
        assert bullets[0].changed
        assert not bullets[1].changed
        assert "robust" in bullets[0].new_text

    def test_experience_added(self):
        old = _make_resume(experience=[])
        new = _make_resume(experience=[
            ExperienceItem(
                title="Intern",
                company="Startup",
                bullets=["Learned stuff."],
            )
        ])
        comp = compare_resumes(old, new)
        assert len(comp.experience) >= 1
        assert comp.experience[0].title.new_value == "Intern"

    def test_experience_deleted(self):
        old = _make_resume()
        new = _make_resume(experience=[])
        comp = compare_resumes(old, new)
        assert len(comp.experience) >= 1
        assert comp.experience[0].title.old_value == "Engineer"

    def test_multiple_changes_counted(self):
        old = _make_resume()
        new = _make_resume(
            contact=ContactInfo(name="New Name", email="new@test.com"),
            summary="New summary",
            skills=["Python", "Go"],
        )
        comp = compare_resumes(old, new)
        assert comp.total_changes >= 3
