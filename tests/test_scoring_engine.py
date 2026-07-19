from app.domain.resume import ContactInfo, ExperienceItem, ResumeData
from app.domain.scoring import CATEGORY_WEIGHTS, LayoutMetrics
from app.services.scoring_engine import build_score_report


def _full_resume() -> ResumeData:
    return ResumeData(
        contact=ContactInfo(
            name="Jane Doe",
            email="jane@example.com",
            phone="+1-555-123-4567",
            linkedin="linkedin.com/in/janedoe",
        ),
        headline="Senior Python Developer",
        summary="Backend developer with 8 years of experience building APIs.",
        skills=["Python", "SQL", "Docker", "FastAPI", "PostgreSQL"],
        experience=[
            ExperienceItem(
                title="Senior Developer",
                company="Acme",
                start_date="2020",
                end_date="Present",
                bullets=[
                    "Built REST APIs serving 10k requests per second",
                    "Reduced deployment time by 60 percent through CI/CD improvements",
                ],
            )
        ],
    )


def test_score_equals_visible_rule_results():
    resume = _full_resume()
    layout = LayoutMetrics(word_count=400, has_bullets=True)
    report = build_score_report(resume, None, layout)
    expected = round(
        sum(cat.score * cat.weight for cat in report.categories)
    )
    assert report.overall_score == expected
    assert len(report.categories) == len(CATEGORY_WEIGHTS)


def test_perfect_resume_scores_high():
    report = build_score_report(_full_resume(), None, LayoutMetrics(word_count=400, has_bullets=True))
    assert report.overall_score >= 90
    assert not any(cat.score < 90 for cat in report.categories)


def test_missing_email_fires_format_issue():
    resume = _full_resume()
    resume.contact.email = ""
    report = build_score_report(resume, None, LayoutMetrics(word_count=400, has_bullets=True))
    codes = [issue.code for cat in report.categories for issue in cat.issues]
    assert "FORMAT-001" in codes


def test_no_skills_fires_content_issue():
    resume = _full_resume()
    resume.skills = []
    report = build_score_report(resume, None, LayoutMetrics(word_count=400, has_bullets=True))
    codes = [issue.code for cat in report.categories for issue in cat.issues]
    assert "CONTENT-002" in codes


def test_short_resume_fires_format_issue():
    resume = _full_resume()
    report = build_score_report(resume, None, LayoutMetrics(word_count=80, has_bullets=True))
    codes = [issue.code for cat in report.categories for issue in cat.issues]
    assert "FORMAT-004" in codes


def test_jd_missing_keywords_fires_optimization_issue():
    jd = (
        "We need a developer skilled in Kubernetes, Terraform, AWS, "
        "microservices, and monitoring. Experience with CI/CD and "
        "infrastructure as code is required."
    )
    report = build_score_report(_full_resume(), jd, LayoutMetrics(word_count=400, has_bullets=True))
    codes = [issue.code for cat in report.categories for issue in cat.issues]
    assert "OPT-001" in codes or "OPT-002" in codes


def test_empty_resume_fires_readiness_issue():
    resume = ResumeData()
    report = build_score_report(resume, None, LayoutMetrics(word_count=0, has_bullets=False))
    codes = [issue.code for cat in report.categories for issue in cat.issues]
    assert "READY-001" in codes
