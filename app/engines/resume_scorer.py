"""23-Factor Resume Score — weighted scoring across all resume dimensions.

Each factor evaluates a specific aspect of resume quality. The factors are
grouped into categories and weighted to produce an overall score 0-100.
"""
import re
from dataclasses import dataclass, field

from app.schemas import ResumeData


@dataclass
class FactorResult:
    name: str
    score: float
    weight: float
    max_score: float = 10.0
    message: str = ""

    @property
    def weighted_score(self) -> float:
        return (self.score / self.max_score) * self.weight if self.max_score else 0.0


@dataclass
class ResumeScore:
    overall: float = 0.0
    factors: list[FactorResult] = field(default_factory=list)
    grade: str = ""

    def __post_init__(self):
        if self.overall >= 90:
            self.grade = "A"
        elif self.overall >= 80:
            self.grade = "B"
        elif self.overall >= 70:
            self.grade = "C"
        elif self.overall >= 60:
            self.grade = "D"
        else:
            self.grade = "F"


def calculate_resume_score(resume: ResumeData, jd_text: str = "") -> ResumeScore:
    """Evaluate a resume across 23 factors and return a weighted score."""
    factors: list[FactorResult] = []
    jd_lower = jd_text.lower() if jd_text else ""

    # ── Contact & Format (factors 1-5) ──────────────────────────────
    factors.append(_f_contact_name(resume))
    factors.append(_f_contact_email(resume))
    factors.append(_f_contact_phone(resume))
    factors.append(_f_contact_location(resume))
    factors.append(_f_contact_linkedin(resume))

    # ── Summary (factors 6-8) ───────────────────────────────────────
    factors.append(_f_summary_exists(resume))
    factors.append(_f_summary_length(resume))
    factors.append(_f_summary_keywords(resume, jd_lower))

    # ── Skills (factors 9-11) ───────────────────────────────────────
    factors.append(_f_skills_count(resume))
    factors.append(_f_skills_match(resume, jd_lower))
    factors.append(_f_skills_relevant(resume, jd_lower))

    # ── Experience (factors 12-17) ───────────────────────────────────
    factors.append(_f_experience_entries(resume))
    factors.append(_f_bullet_count(resume))
    factors.append(_f_bullet_length(resume))
    factors.append(_f_bullet_metrics(resume))
    factors.append(_f_action_verbs(resume))
    factors.append(_f_dates_consistency(resume))

    # ── Education & Certifications (factors 18-20) ───────────────────
    factors.append(_f_education_exists(resume))
    factors.append(_f_certifications(resume))
    factors.append(_f_projects_exist(resume))

    # ── Overall Quality (factors 21-23) ──────────────────────────────
    factors.append(_f_word_count(resume))
    factors.append(_f_no_duplicates(resume))
    factors.append(_f_section_order(resume))

    total_weighted = sum(f.weighted_score for f in factors)
    total_weight = sum(f.weight for f in factors)
    overall = round(total_weighted / total_weight * 100, 1) if total_weight else 0.0
    overall = max(0.0, min(100.0, overall))

    return ResumeScore(overall=overall, factors=factors)


# ── Factor implementations ────────────────────────────────────────────────

def _f_contact_name(r: ResumeData) -> FactorResult:
    has = bool(r.contact.name and r.contact.name.strip())
    return FactorResult("Contact: Name", 10.0 if has else 0.0, 3.0,
                        message="" if has else "Add your full name")


def _f_contact_email(r: ResumeData) -> FactorResult:
    has = bool(r.contact.email and "@" in r.contact.email)
    return FactorResult("Contact: Email", 10.0 if has else 0.0, 4.0,
                        message="" if has else "Add a professional email address")


def _f_contact_phone(r: ResumeData) -> FactorResult:
    has = bool(r.contact.phone and r.contact.phone.strip())
    return FactorResult("Contact: Phone", 10.0 if has else 0.0, 3.0,
                        message="" if has else "Add a phone number")


def _f_contact_location(r: ResumeData) -> FactorResult:
    has = bool(r.contact.location and r.contact.location.strip())
    return FactorResult("Contact: Location", 10.0 if has else 0.0, 2.0,
                        message="" if has else "Add city/state for local jobs")


def _f_contact_linkedin(r: ResumeData) -> FactorResult:
    has = bool(r.contact.linkedin and r.contact.linkedin.strip())
    return FactorResult("Contact: LinkedIn", 10.0 if has else 0.0, 2.0,
                        message="" if has else "Add LinkedIn URL")


def _f_summary_exists(r: ResumeData) -> FactorResult:
    has = bool(r.summary and r.summary.strip())
    return FactorResult("Summary: Exists", 10.0 if has else 0.0, 5.0,
                        message="" if has else "Add a professional summary")


def _f_summary_length(r: ResumeData) -> FactorResult:
    words = len((r.summary or "").split())
    if words == 0:
        return FactorResult("Summary: Length", 0.0, 3.0, message="No summary")
    if words < 20:
        return FactorResult("Summary: Length", 5.0, 3.0, message=f"Too short ({words} words)")
    if words > 100:
        return FactorResult("Summary: Length", 6.0, 3.0, message=f"Too long ({words} words)")
    return FactorResult("Summary: Length", 10.0, 3.0, message=f"{words} words — good")


def _f_summary_keywords(r: ResumeData, jd_lower: str) -> FactorResult:
    if not jd_lower or not r.summary:
        return FactorResult("Summary: Keywords", 5.0, 3.0, message="N/A without JD")
    summary_lower = r.summary.lower()
    jd_words = set(re.findall(r"\b[a-z]{3,}\b", jd_lower))
    matches = sum(1 for w in jd_words if w in summary_lower)
    ratio = min(matches / max(len(jd_words) * 0.1, 1), 1.0)
    score = round(ratio * 10, 1)
    return FactorResult("Summary: Keywords", score, 3.0,
                        message=f"{matches} JD keywords in summary")


def _f_skills_count(r: ResumeData) -> FactorResult:
    count = len(r.skills)
    if count == 0:
        return FactorResult("Skills: Count", 0.0, 4.0, message="No skills listed")
    if count < 5:
        return FactorResult("Skills: Count", 5.0, 4.0, message=f"Only {count} skills")
    if count > 20:
        return FactorResult("Skills: Count", 7.0, 4.0, message=f"{count} skills — trim to 8-15")
    return FactorResult("Skills: Count", 10.0, 4.0, message=f"{count} skills")


def _f_skills_match(r: ResumeData, jd_lower: str) -> FactorResult:
    if not jd_lower:
        return FactorResult("Skills: JD Match", 5.0, 4.0, message="N/A without JD")
    resume_skills = " ".join(r.skills).lower()
    jd_words = set(re.findall(r"\b[a-z]{3,}\b", jd_lower))
    matches = sum(1 for w in jd_words if w in resume_skills)
    ratio = min(matches / max(len(jd_words) * 0.15, 1), 1.0)
    score = round(ratio * 10, 1)
    return FactorResult("Skills: JD Match", score, 4.0,
                        message=f"{matches} matching skills from JD")


def _f_skills_relevant(r: ResumeData, jd_lower: str) -> FactorResult:
    if not jd_lower:
        return FactorResult("Skills: Relevance", 5.0, 3.0, message="N/A without JD")
    all_resume_text = " ".join(r.skills + [s.title for s in r.experience]).lower()
    jd_words = set(re.findall(r"\b[a-z]{3,}\b", jd_lower))
    relevant = sum(1 for w in jd_words if w in all_resume_text)
    ratio = min(relevant / max(len(jd_words) * 0.2, 1), 1.0)
    score = round(ratio * 10, 1)
    return FactorResult("Skills: Relevance", score, 3.0,
                        message=f"{relevant} JD terms found in resume")


def _f_experience_entries(r: ResumeData) -> FactorResult:
    count = len(r.experience)
    if count == 0:
        return FactorResult("Experience: Entries", 0.0, 5.0, message="No experience listed")
    if count == 1:
        return FactorResult("Experience: Entries", 6.0, 5.0, message="Only 1 entry")
    return FactorResult("Experience: Entries", 10.0, 5.0, message=f"{count} entries")


def _f_bullet_count(r: ResumeData) -> FactorResult:
    total = sum(len(exp.bullets) for exp in r.experience)
    if total == 0:
        return FactorResult("Experience: Bullets", 0.0, 4.0, message="No bullets")
    if total < 3:
        return FactorResult("Experience: Bullets", 4.0, 4.0, message=f"Only {total} bullets total")
    if total > 15:
        return FactorResult("Experience: Bullets", 7.0, 4.0, message=f"{total} bullets — consider trimming")
    return FactorResult("Experience: Bullets", 10.0, 4.0, message=f"{total} bullets")


def _f_bullet_length(r: ResumeData) -> FactorResult:
    lengths = [len(b) for exp in r.experience for b in exp.bullets]
    if not lengths:
        return FactorResult("Experience: Bullet Length", 5.0, 3.0, message="N/A")
    avg = sum(lengths) / len(lengths)
    if avg < 40:
        return FactorResult("Experience: Bullet Length", 4.0, 3.0,
                            message=f"Average {avg:.0f} chars — too short")
    if avg > 200:
        return FactorResult("Experience: Bullet Length", 6.0, 3.0,
                            message=f"Average {avg:.0f} chars — too long")
    return FactorResult("Experience: Bullet Length", 10.0, 3.0,
                        message=f"Average {avg:.0f} chars")


def _f_bullet_metrics(r: ResumeData) -> FactorResult:
    bullets = [b for exp in r.experience for b in exp.bullets]
    if not bullets:
        return FactorResult("Experience: Metrics", 5.0, 4.0, message="N/A")
    with_numbers = sum(1 for b in bullets if re.search(r"\d", b))
    ratio = with_numbers / len(bullets)
    if ratio < 0.3:
        return FactorResult("Experience: Metrics", 3.0, 4.0,
                            message=f"Only {with_numbers}/{len(bullets)} bullets have numbers")
    if ratio < 0.6:
        return FactorResult("Experience: Metrics", 6.0, 4.0,
                            message=f"{with_numbers}/{len(bullets)} bullets have numbers")
    return FactorResult("Experience: Metrics", 10.0, 4.0,
                        message=f"{with_numbers}/{len(bullets)} bullets have numbers")


def _f_action_verbs(r: ResumeData) -> FactorResult:
    strong_verbs = {
        "led", "built", "developed", "implemented", "designed", "created",
        "delivered", "launched", "managed", "optimized", "reduced", "increased",
        "improved", "automated", "migrated", "deployed", "architected",
        "established", "initiated", "spearheaded", "orchestrated", "scaled",
        "streamlined", "consolidated", "negotiated", "resolved",
    }
    bullets = [b.lower() for exp in r.experience for b in exp.bullets]
    if not bullets:
        return FactorResult("Experience: Action Verbs", 5.0, 3.0, message="N/A")
    with_strong = sum(
        1 for b in bullets
        if any(b.split()[0].startswith(v) for v in strong_verbs if b.split())
    )
    ratio = with_strong / len(bullets)
    if ratio < 0.4:
        return FactorResult("Experience: Action Verbs", 4.0, 3.0,
                            message=f"Only {with_strong}/{len(bullets)} start with strong verbs")
    return FactorResult("Experience: Action Verbs", 10.0, 3.0,
                        message=f"{with_strong}/{len(bullets)} start with strong verbs")


def _f_dates_consistency(r: ResumeData) -> FactorResult:
    date_pattern = re.compile(r"(?:19|20)\d{2}")
    issues = 0
    for exp in r.experience:
        has_start = bool(exp.start_date and date_pattern.search(exp.start_date))
        has_end = bool(exp.end_date and date_pattern.search(exp.end_date))
        if has_start and not has_end and exp.end_date and "present" not in exp.end_date.lower():
            issues += 1
    if issues > 0:
        return FactorResult("Experience: Dates", 5.0, 2.0,
                            message=f"{issues} entries have inconsistent dates")
    return FactorResult("Experience: Dates", 10.0, 2.0, message="Dates consistent")


def _f_education_exists(r: ResumeData) -> FactorResult:
    has = len(r.education) > 0
    return FactorResult("Education: Exists", 10.0 if has else 0.0, 4.0,
                        message="" if has else "Add education section")


def _f_certifications(r: ResumeData) -> FactorResult:
    count = len(r.certifications)
    if count == 0:
        return FactorResult("Certifications", 5.0, 2.0, message="No certifications")
    return FactorResult("Certifications", 10.0, 2.0, message=f"{count} certifications")


def _f_projects_exist(r: ResumeData) -> FactorResult:
    has = len(r.projects) > 0
    return FactorResult("Projects: Exists", 10.0 if has else 3.0, 2.0,
                        message="" if has else "Consider adding projects")


def _f_word_count(r: ResumeData) -> FactorResult:
    text = " ".join(filter(None, [
        r.summary, " ".join(r.skills),
        " ".join(b for exp in r.experience for b in exp.bullets),
        " ".join(b for proj in r.projects for b in proj.bullets),
    ]))
    words = len(text.split())
    if words < 150:
        return FactorResult("Word Count", 4.0, 3.0, message=f"{words} words — too brief")
    if words > 800:
        return FactorResult("Word Count", 6.0, 3.0, message=f"{words} words — trim")
    return FactorResult("Word Count", 10.0, 3.0, message=f"{words} words")


def _f_no_duplicates(r: ResumeData) -> FactorResult:
    bullets = [b.lower().strip() for exp in r.experience for b in exp.bullets]
    bullets += [b.lower().strip() for proj in r.projects for b in proj.bullets]
    unique = set(bullets)
    dups = len(bullets) - len(unique)
    if dups > 0:
        return FactorResult("No Duplicates", 4.0, 3.0, message=f"{dups} duplicate bullets")
    return FactorResult("No Duplicates", 10.0, 3.0, message="No duplicates")


def _f_section_order(r: ResumeData) -> FactorResult:
    has_summary = bool(r.summary)
    has_skills = bool(r.skills)
    has_experience = bool(r.experience)
    score = 10.0
    msg = "Good order"
    if has_experience and not has_skills:
        score -= 2
        msg = "Add skills before or after experience"
    if has_experience and not has_summary:
        score -= 2
        msg = "Add summary above experience"
    return FactorResult("Section Order", max(score, 0.0), 2.0, message=msg)
