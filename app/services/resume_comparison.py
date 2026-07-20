"""Resume comparison service — structured side-by-side diff."""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from app.domain.resume import ResumeData


@dataclass(frozen=True)
class FieldDiff:
    """Diff for a single text field."""
    field_name: str
    old_value: str
    new_value: str
    changed: bool


@dataclass(frozen=True)
class BulletDiff:
    """Diff for a single bullet point within an experience entry."""
    index: int
    old_text: str
    new_text: str
    changed: bool


@dataclass(frozen=True)
class ExperienceDiff:
    """Diff for one experience entry (matched by index)."""
    index: int
    title: FieldDiff
    company: FieldDiff
    start_date: FieldDiff
    end_date: FieldDiff
    bullets: list[BulletDiff] = field(default_factory=list)


@dataclass(frozen=True)
class ResumeComparison:
    """Full structured comparison between two resumes."""
    name: FieldDiff
    headline: FieldDiff
    summary: FieldDiff
    skills_old: list[str]
    skills_new: list[str]
    skills_changed: bool
    experience: list[ExperienceDiff]
    total_changes: int


def _field_diff(label: str, old: str | None, new: str | None) -> FieldDiff:
    o = old or ""
    n = new or ""
    return FieldDiff(field_name=label, old_value=o, new_value=n, changed=o != n)


def compare_resumes(old: ResumeData, new: ResumeData) -> ResumeComparison:
    """Produce a structured comparison between two resumes."""

    name_diff = _field_diff("Name", old.contact.name, new.contact.name)
    headline_diff = _field_diff("Headline", old.headline, new.headline)
    summary_diff = _field_diff("Summary", old.summary, new.summary)

    skills_changed = old.skills != new.skills

    experience_diffs: list[ExperienceDiff] = []
    matcher = SequenceMatcher(
        None,
        [(e.title, e.company) for e in old.experience],
        [(e.title, e.company) for e in new.experience],
    )

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                oe = old.experience[i1 + k]
                ne = new.experience[j1 + k]
                exp_diff = _diff_experience(i1 + k, oe, ne)
                experience_diffs.append(exp_diff)
        elif tag == "replace":
            max_len = max(i2 - i1, j2 - j1)
            for k in range(max_len):
                oe = old.experience[i1 + k] if k < (i2 - i1) else None
                ne = new.experience[j1 + k] if k < (j2 - j1) else None
                if oe and ne:
                    experience_diffs.append(_diff_experience(i1 + k, oe, ne))
                elif ne:
                    experience_diffs.append(_all_new_experience(i1 + k, ne))
                elif oe:
                    experience_diffs.append(_all_deleted_experience(i1 + k, oe))
        elif tag == "insert":
            for k in range(j2 - j1):
                experience_diffs.append(_all_new_experience(i1 + k, new.experience[j1 + k]))
        elif tag == "delete":
            for k in range(i2 - i1):
                experience_diffs.append(_all_deleted_experience(i1 + k, old.experience[i1 + k]))

    experience_diffs.sort(key=lambda e: e.index)

    total = sum(1 for d in [name_diff, headline_diff, summary_diff] if d.changed)
    total += 1 if skills_changed else 0
    for exp in experience_diffs:
        exp_changed = exp.title.changed or exp.company.changed or exp.start_date.changed or exp.end_date.changed or any(b.changed for b in exp.bullets)
        if exp_changed:
            total += 1
        total += sum(1 for b in exp.bullets if b.changed)

    return ResumeComparison(
        name=name_diff,
        headline=headline_diff,
        summary=summary_diff,
        skills_old=old.skills,
        skills_new=new.skills,
        skills_changed=skills_changed,
        experience=experience_diffs,
        total_changes=total,
    )


def _diff_experience(idx: int, old, new) -> ExperienceDiff:
    bullet_matcher = SequenceMatcher(None, old.bullets, new.bullets)
    bullets: list[BulletDiff] = []
    for btag, bi1, bi2, bj1, bj2 in bullet_matcher.get_opcodes():
        if btag == "equal":
            for k in range(bi2 - bi1):
                bullets.append(BulletDiff(idx + k, old.bullets[bi1 + k], new.bullets[bj1 + k], False))
        else:
            max_len = max(bi2 - bi1, bj2 - bj1)
            for k in range(max_len):
                ob = old.bullets[bi1 + k] if k < (bi2 - bi1) else ""
                nb = new.bullets[bj1 + k] if k < (bj2 - bj1) else ""
                bullets.append(BulletDiff(bi1 + k, ob, nb, ob != nb))

    return ExperienceDiff(
        index=idx,
        title=_field_diff("Title", old.title, new.title),
        company=_field_diff("Company", old.company, new.company),
        start_date=_field_diff("Start", old.start_date, new.start_date),
        end_date=_field_diff("End", old.end_date, new.end_date),
        bullets=bullets,
    )


def _all_new_experience(idx: int, exp) -> ExperienceDiff:
    return ExperienceDiff(
        index=idx,
        title=FieldDiff("Title", "", exp.title, True),
        company=FieldDiff("Company", "", exp.company, True),
        start_date=FieldDiff("Start", "", exp.start_date or "", True),
        end_date=FieldDiff("End", "", exp.end_date or "", True),
        bullets=[BulletDiff(k, "", b, True) for k, b in enumerate(exp.bullets)],
    )


def _all_deleted_experience(idx: int, exp) -> ExperienceDiff:
    return ExperienceDiff(
        index=idx,
        title=FieldDiff("Title", exp.title, "", True),
        company=FieldDiff("Company", exp.company, "", True),
        start_date=FieldDiff("Start", exp.start_date or "", "", True),
        end_date=FieldDiff("End", exp.end_date or "", "", True),
        bullets=[BulletDiff(k, b, "", True) for k, b in enumerate(exp.bullets)],
    )
