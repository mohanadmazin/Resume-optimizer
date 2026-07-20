"""Tests for Phase 9: Content Checker, Resume Scorer, Skill Explorer."""
from app.domain.content_check import ContentCheckResult, IssueType
from app.domain.resume import ContactInfo, EducationItem, ExperienceItem, ProjectItem, ResumeData
from app.services.content_checker import check_content
from app.services.resume_scorer import ResumeScore, calculate_resume_score
from app.services.skill_explorer import SkillSuggestion, explore_skills


# ── Content Checker ────────────────────────────────────────────────────────

def _full_resume() -> ResumeData:
    return ResumeData(
        contact=ContactInfo(
            name="Jane Doe",
            email="jane@example.com",
            phone="+1-555-123-4567",
            location="Seattle, WA",
            linkedin="linkedin.com/in/janedoe",
        ),
        summary="Senior backend developer with 8 years of experience building scalable APIs.",
        skills=["Python", "SQL", "Docker", "FastAPI", "PostgreSQL"],
        experience=[
            ExperienceItem(
                title="Senior Developer",
                company="Acme",
                start_date="2020",
                end_date="Present",
                bullets=[
                    "Built REST APIs serving 10k requests per second",
                    "Reduced deployment time by 60% through CI/CD automation",
                ],
            )
        ],
        education=[],
        certifications=[],
    )


def test_content_check_clean_resume():
    result = check_content(_full_resume())
    assert isinstance(result, ContentCheckResult)
    assert result.score > 80
    errors = [i for i in result.issues if i.severity == "error"]
    assert len(errors) == 0


def test_content_check_missing_email():
    resume = _full_resume()
    resume.contact.email = ""
    result = check_content(resume)
    assert any(i.issue_type == IssueType.CONTACT_INCOMPLETE and "email" in i.path for i in result.issues)


def test_content_check_missing_summary():
    resume = _full_resume()
    resume.summary = ""
    result = check_content(resume)
    assert any(i.issue_type == IssueType.SUMMARY_TOO_SHORT for i in result.issues)
    assert result.score <= 90


def test_content_check_short_summary():
    resume = _full_resume()
    resume.summary = "Developer."
    result = check_content(resume)
    assert any(i.issue_type == IssueType.SUMMARY_TOO_SHORT for i in result.issues)


def test_content_check_long_summary():
    resume = _full_resume()
    resume.summary = " ".join(["word"] * 200)
    result = check_content(resume)
    assert any(i.issue_type == IssueType.SUMMARY_TOO_LONG for i in result.issues)


def test_content_check_weak_words():
    resume = _full_resume()
    resume.experience[0].bullets = ["Responsible for building things"]
    result = check_content(resume)
    assert any(i.issue_type == IssueType.WEAK_WORD for i in result.issues)


def test_content_check_passive_voice():
    resume = _full_resume()
    resume.experience[0].bullets = ["The system was improved by the team to handle more traffic"]
    result = check_content(resume)
    assert any(i.issue_type == IssueType.PASSIVE_VOICE for i in result.issues)


def test_content_check_short_bullet():
    resume = _full_resume()
    resume.experience[0].bullets = ["Built things"]
    result = check_content(resume)
    assert any(i.issue_type == IssueType.SHORT_BULLET for i in result.issues)


def test_content_check_no_metrics():
    resume = _full_resume()
    resume.experience[0].bullets = ["Built amazing things that helped the team a lot"]
    result = check_content(resume)
    assert any(i.issue_type == IssueType.NO_METRICS for i in result.issues)


def test_content_check_project_bullets():
    resume = _full_resume()
    resume.projects = [
        ProjectItem(title="Side Project", bullets=["Did stuff"])
    ]
    result = check_content(resume)
    assert any("projects" in i.path for i in result.issues)


def test_content_check_score_decreases_with_issues():
    clean = check_content(_full_resume())
    dirty = ResumeData(
        contact=ContactInfo(name="X"),
        summary="Hi",
        experience=[ExperienceItem(
            title="Job",
            bullets=["Responsible for things", "Was involved in stuff"],
        )],
    )
    dirty_result = check_content(dirty)
    assert dirty_result.score < clean.score


# ── Resume Scorer ──────────────────────────────────────────────────────────

def test_scorer_perfect_resume():
    resume = _full_resume()
    resume.education = [EducationItem(degree="BSc CS", institution="MIT", year="2015")]
    score = calculate_resume_score(resume)
    assert isinstance(score, ResumeScore)
    assert score.overall >= 70
    assert len(score.factors) == 23
    assert score.grade in ("A", "B", "C")


def test_scorer_empty_resume():
    score = calculate_resume_score(ResumeData())
    assert score.overall < 30
    assert score.grade == "F"


def test_scorer_with_jd():
    resume = _full_resume()
    jd = "We need Python, Docker, and Kubernetes experience. AWS preferred."
    score = calculate_resume_score(resume, jd)
    assert len(score.factors) == 23
    assert score.overall > 0


def test_scorer_factors_have_weights():
    score = calculate_resume_score(_full_resume())
    for factor in score.factors:
        assert factor.weight > 0
        assert 0 <= factor.score <= factor.max_score


def test_scorer_grades():
    assert ResumeScore(overall=95).grade == "A"
    assert ResumeScore(overall=85).grade == "B"
    assert ResumeScore(overall=75).grade == "C"
    assert ResumeScore(overall=65).grade == "D"
    assert ResumeScore(overall=40).grade == "F"


def test_scorer_missing_skills_reduces_score():
    resume = _full_resume()
    resume.skills = []
    score_no_skills = calculate_resume_score(resume)
    score_with_skills = calculate_resume_score(_full_resume())
    assert score_no_skills.overall < score_with_skills.overall


def test_scorer_no_bullets_reduces_score():
    resume = _full_resume()
    resume.experience[0].bullets = []
    score = calculate_resume_score(resume)
    bullet_factor = next(f for f in score.factors if "Bullets" in f.name)
    assert bullet_factor.score < 10.0


# ── Skill Explorer ─────────────────────────────────────────────────────────

def test_skill_explorer_empty_jd():
    resume = _full_resume()
    result = explore_skills(resume, "")
    # No JD means no JD-based suggestions, but complementary may exist
    jd_suggestions = [s for s in result if s.in_jd]
    assert jd_suggestions == []


def test_skill_explorer_no_overlap():
    resume = _full_resume()
    jd = "Looking for someone with Kubernetes, Terraform, and Go experience."
    result = explore_skills(resume, jd)
    assert len(result) > 0
    skills = [s.skill.lower() for s in result]
    assert any("kubernetes" in s for s in skills)
    assert any("terraform" in s for s in skills)


def test_skill_explorer_deduplicates():
    resume = _full_resume()
    jd = "We need Python, python, PYTHON experience."
    result = explore_skills(resume, jd)
    python_suggestions = [s for s in result if s.skill.lower() == "python"]
    assert len(python_suggestions) == 0  # Already in resume


def test_skill_explorer_importance_sorting():
    resume = _full_resume()
    jd = "Must have Kubernetes. Nice to have Terraform."
    result = explore_skills(resume, jd)
    if len(result) >= 2:
        assert result[0].importance >= result[-1].importance


def test_skill_explorer_suggestion_model():
    s = SkillSuggestion(skill="Go", reason="In JD", importance=4, in_jd=True)
    assert s.skill == "Go"
    assert s.importance == 4
    assert s.in_jd is True


def test_skill_explorer_complementary():
    resume = _full_resume()
    resume.skills = ["Python", "Docker"]
    jd = ""
    result = explore_skills(resume, jd)
    # Should suggest complementary skills even without JD
    assert len(result) > 0
    reasons = [s.reason.lower() for s in result]
    assert any("complement" in r for r in reasons)


def test_skill_explorer_no_suggestion_for_existing():
    resume = _full_resume()
    jd = "We need Python, SQL, Docker, FastAPI, PostgreSQL."
    result = explore_skills(resume, jd)
    existing = {s.lower() for s in resume.skills}
    for suggestion in result:
        assert suggestion.skill.lower() not in existing
