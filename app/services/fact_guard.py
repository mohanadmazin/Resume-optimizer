"""Deterministic fact guard — validates AI-generated resume changes against source."""
import logging
import re
from collections import Counter
from difflib import SequenceMatcher

from app.domain.fact_guard import ChangeType, FactGuardResult, ProposedChange
from app.domain.resume import ResumeData

logger = logging.getLogger(__name__)

# Common false-positive entity patterns to ignore
_IGNORE_TOKENS = {
    "team", "project", "product", "system", "platform", "process", "service",
    "application", "solution", "environment", "infrastructure", "architecture",
    "methodology", "framework", "approach", "strategy", "initiative", "program",
    "department", "organization", "group", "division", "unit", "office",
    "client", "stakeholder", "customer", "user", "partner", "vendor",
    # Sentence starters that look like entities
    "developed", "led", "managed", "created", "built", "implemented",
    "designed", "established", "delivered", "maintained", "reduced",
    "increased", "improved", "launched", "collaborated", "coordinated",
    "optimized", "automated", "integrated", "migrated", "deployed",
    "configured", "architected", "spearheaded", "orchestrated",
}

# Pattern for numbers (integers, decimals, percentages, currency)
_NUMBER_RE = re.compile(
    r"(?:"
    r"\$[\d,]+(?:\.\d+)?"       # currency: $1,000, $50.50
    r"|\d{1,3}(?:,\d{3})+"      # comma-separated: 1,000,000
    r"|\d+%"                     # percentages: 50%
    r"|\d+(?:\.\d+)?"           # plain numbers: 42, 3.14
    r")"
)

# Pattern for capitalized words (potential proper nouns / entities)
# Require at least 2 consecutive capitalized words or known company suffixes
_ENTITY_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"  # Multi-word: "Acme Corp"
    r"|\b([A-Z][a-z]+(?:Corp|Inc|Ltd|LLC|Co|Company|Group|Solutions|Technologies|Systems))\b"
)

# Pattern for tech-looking tokens (case-sensitive: React, C++, Node.js)
_TECH_RE = re.compile(
    r"\b([A-Z][A-Za-z#+.]{1,20})\b"  # React, C++, Node.js, etc.
)

# Skill aliases shared with ats_engine for normalization consistency
_SKILL_ALIASES: dict[str, str] = {
    "js": "javascript",
    "nodejs": "node.js",
    "node js": "node.js",
    "reactjs": "react",
    "react.js": "react",
    "vuejs": "vue",
    "vue.js": "vue",
    "angularjs": "angular",
    "angular.js": "angular",
    "postgres": "postgresql",
    "psql": "postgresql",
    "pgsql": "postgresql",
    "k8s": "kubernetes",
    "kube": "kubernetes",
    "py": "python",
    "python3": "python",
    "ts": "typescript",
    "golang": "go",
    "rustlang": "rust",
    "aws": "amazon web services",
    "gcp": "google cloud platform",
    "azure": "microsoft azure",
    "rest": "restful apis",
    "restful": "restful apis",
    "rest api": "restful apis",
    "rest apis": "restful apis",
    "ci cd": "ci/cd",
    "continuous integration": "ci/cd",
    "continuous delivery": "ci/cd",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "dev ops": "devops",
}


def _normalize_skill(value: str) -> str:
    """Normalize a skill token to its canonical lowercase form."""
    value = value.lower().strip()
    return _SKILL_ALIASES.get(value, value)


def _extract_numbers(text: str) -> set[str]:
    """Extract all number-like tokens from text."""
    return set(_NUMBER_RE.findall(text))


def _extract_entities(text: str) -> set[str]:
    """Extract multi-word proper nouns and known company-suffix entities."""
    entities: set[str] = set()
    for match in _ENTITY_RE.finditer(text):
        entity = match.group(0)
        if entity.lower() not in _IGNORE_TOKENS:
            entities.add(entity)
    return entities


def _extract_tech_tokens(text: str) -> set[str]:
    """Extract technology-looking tokens (CamelCase, #, ++, .js, etc.)."""
    return {m for m in _TECH_RE.findall(text) if len(m) > 1}


def _source_vocabulary(resume: ResumeData) -> set[str]:
    """Build a vocabulary of all known tokens from the source resume.

    Includes: all skills (normalized), company names, titles, degree names,
    certification names, and project titles.  This is used to detect
    AI-injected tokens that have no basis in the source material.
    """
    vocab: set[str] = set()
    for s in resume.skills:
        norm = _normalize_skill(s)
        vocab.add(norm)
        vocab.update(norm.split())
    for exp in resume.experience:
        vocab.update(exp.company.lower().split())
        vocab.update(exp.title.lower().split())
        for b in exp.bullets:
            vocab.update(b.lower().split())
    for edu in resume.education:
        vocab.update(edu.degree.lower().split())
        vocab.update(edu.institution.lower().split())
    for cert in resume.certifications:
        vocab.update(cert.lower().split())
    for proj in resume.projects:
        vocab.update(proj.title.lower().split())
    return vocab


def _source_tech_vocab(resume: ResumeData) -> set[str]:
    """Build a lowercase set of all known tech tokens from skills and experience."""
    tech: set[str] = set()
    for s in resume.skills:
        norm = _normalize_skill(s)
        tech.add(norm)
        tech.update(_extract_tech_tokens(s))
    for exp in resume.experience:
        for b in exp.bullets:
            tech.update(_extract_tech_tokens(b))
    return {t.lower() for t in tech}


class FactGuard:
    """Deterministic fact guard — preventive constraints + post-generation validation."""

    def __init__(self, max_bullet_change_ratio: float = 0.6):
        """Args:
            max_bullet_change_ratio: maximum fraction of bullets that can
                change in a single experience entry before flagging.
                0.6 means "if more than 60% of bullets changed, flag it."
        """
        self.max_bullet_change_ratio = max_bullet_change_ratio

    # ── Preventive: inject constraints before generation ──────────────

    def create_constraints(self, resume: ResumeData) -> str:
        """Extract immutable facts from the resume as constraint lines.

        These are injected into the AI prompt BEFORE generation to
        prevent hallucinations rather than catching them after the fact.
        """
        lines: list[str] = []

        # Dates
        dates = set()
        for exp in resume.experience:
            if exp.start_date:
                dates.add(exp.start_date)
            if exp.end_date:
                dates.add(exp.end_date)
        if dates:
            lines.append(f"IMMUTABLE DATES: {', '.join(sorted(dates))}")

        # Employers
        employers = [exp.company for exp in resume.experience if exp.company]
        if employers:
            lines.append(f"IMMUTABLE EMPLOYERS: {', '.join(employers)}")

        # Job titles
        titles = [exp.title for exp in resume.experience if exp.title]
        if titles:
            lines.append(f"IMMUTABLE TITLES: {', '.join(titles)}")

        # Education
        edu_items = [
            f"{edu.degree} from {edu.institution}"
            for edu in resume.education
            if edu.degree or edu.institution
        ]
        if edu_items:
            lines.append(f"IMMUTABLE EDUCATION: {'; '.join(edu_items)}")

        # Certifications
        if resume.certifications:
            lines.append(f"IMMUTABLE CERTIFICATIONS: {', '.join(resume.certifications)}")

        # Skills — list exactly, do not add/remove
        if resume.skills:
            lines.append(f"IMMUTABLE SKILLS: {', '.join(resume.skills)}")

        # Numbers found in bullets — preserve exactly
        all_numbers: set[str] = set()
        for exp in resume.experience:
            for bullet in exp.bullets:
                all_numbers.update(_extract_numbers(bullet))
        if all_numbers:
            lines.append(f"IMMUTABLE NUMBERS: {', '.join(sorted(all_numbers))}")

        # Entities found in bullets — preserve exactly
        all_entities: set[str] = set()
        for exp in resume.experience:
            for bullet in exp.bullets:
                all_entities.update(_extract_entities(bullet))
        if all_entities:
            lines.append(f"IMMUTABLE ENTITIES: {', '.join(sorted(all_entities))}")

        return "\n".join(lines)

    def inject_into_prompt(self, prompt: str, constraints: str) -> str:
        """Prepend factual constraints to the optimization prompt.

        The constraints appear AFTER the system rules but BEFORE the
        user data, so the LLM sees them as authoritative instructions.
        """
        if not constraints:
            return prompt
        return (
            "CRITICAL FACTUAL CONSTRAINTS — DO NOT VIOLATE:\n"
            "<<<CONSTRAINTS>>>\n"
            f"{constraints}\n"
            "<<<END_CONSTRAINTS>>>\n\n"
            f"{prompt}"
        )

    def validate(
        self,
        source: ResumeData,
        optimized: ResumeData,
    ) -> FactGuardResult:
        """Compare source and optimized resumes, flag unsupported changes."""
        all_changes: list[ProposedChange] = []
        all_unsupported_numbers: list[str] = []
        all_unsupported_entities: list[str] = []
        all_unsupported_skills: list[str] = []

        # Pre-compute expensive vocabulary once for all change checks
        source_vocab = _source_vocabulary(source)
        source_tech = _source_tech_vocab(source)

        # --- Summary ---
        if source.summary.strip() != optimized.summary.strip():
            change = self._check_text_change(
                ChangeType.SUMMARY, "Summary",
                source.summary, optimized.summary, source_vocab, source_tech,
            )
            all_changes.append(change)
            if change.has_new_numbers:
                all_unsupported_numbers.extend(
                    _extract_numbers(optimized.summary) - _extract_numbers(source.summary)
                )
            if change.has_new_entities:
                all_unsupported_entities.extend(
                    _extract_entities(optimized.summary) - _extract_entities(source.summary)
                )

        # --- Headline ---
        if source.headline.strip() != optimized.headline.strip():
            change = self._check_text_change(
                ChangeType.HEADLINE, "Headline",
                source.headline, optimized.headline, source_vocab, source_tech,
            )
            all_changes.append(change)

        # --- Experience bullets ---
        # Track per-experience change counts for ratio enforcement
        exp_change_counts: dict[int, int] = {}
        exp_total_bullets: dict[int, int] = {}
        if len(source.experience) == len(optimized.experience):
            for idx, (src_exp, opt_exp) in enumerate(zip(source.experience, optimized.experience)):
                section = f"{src_exp.title or 'Experience'} #{idx + 1}"
                src_bullets = src_exp.bullets
                opt_bullets = opt_exp.bullets
                exp_total_bullets[idx] = len(src_bullets)
                exp_change_counts[idx] = 0

                # Use SequenceMatcher to detect inserted, deleted, rewritten bullets
                matcher = SequenceMatcher(None, src_bullets, opt_bullets)
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag == "equal":
                        continue
                    elif tag == "delete":
                        # Bullets removed — flag for review since the user may want them back
                        for ib in range(i1, i2):
                            old_b = src_bullets[ib]
                            change = ProposedChange(
                                change_type=ChangeType.BULLET_DELETED,
                                section=section,
                                original=old_b,
                                rewritten="",
                                experience_index=idx,
                                bullet_index=ib,
                                requires_review=True,
                                review_reason="bullet was deleted by the AI",
                            )
                            all_changes.append(change)
                            exp_change_counts[idx] += 1
                    elif tag == "insert":
                        # New bullets inserted by AI — must be checked
                        for jb in range(j1, j2):
                            new_bullet = opt_bullets[jb]
                            change = self._check_text_change(
                                ChangeType.BULLET, section,
                                "", new_bullet, source_vocab, source_tech,
                                experience_index=idx, bullet_index=jb,
                            )
                            all_changes.append(change)
                            exp_change_counts[idx] += 1
                            if change.has_new_numbers:
                                all_unsupported_numbers.extend(_extract_numbers(new_bullet))
                            if change.has_new_entities:
                                all_unsupported_entities.extend(_extract_entities(new_bullet))
                            if change.has_new_skills:
                                all_unsupported_skills.extend(_extract_tech_tokens(new_bullet))
                    elif tag == "replace":
                        # Existing bullets rewritten or replaced
                        for k, new_b in enumerate(opt_bullets[j1:j2]):
                            idx_in_src = i1 + k
                            old_b = src_bullets[idx_in_src] if idx_in_src < i2 else ""
                            if old_b.strip() == new_b.strip():
                                continue
                            change = self._check_text_change(
                                ChangeType.BULLET, section,
                                old_b, new_b, source_vocab, source_tech,
                                experience_index=idx, bullet_index=j1 + k,
                            )
                            all_changes.append(change)
                            exp_change_counts[idx] += 1
                            if change.has_new_numbers:
                                all_unsupported_numbers.extend(
                                    _extract_numbers(new_b) - _extract_numbers(old_b)
                                )
                            if change.has_new_entities:
                                all_unsupported_entities.extend(
                                    _extract_entities(new_b) - _extract_entities(old_b)
                                )
                            if change.has_new_skills:
                                all_unsupported_skills.extend(
                                    _extract_tech_tokens(new_b) - _extract_tech_tokens(old_b)
                                )

        # Deduplicate
        all_unsupported_numbers = list(dict.fromkeys(all_unsupported_numbers))
        all_unsupported_entities = list(dict.fromkeys(all_unsupported_entities))
        all_unsupported_skills = list(dict.fromkeys(all_unsupported_skills))

        # Enforce per-experience change ratio
        ratio_exceeded_indices: set[int] = set()
        for idx, changed in exp_change_counts.items():
            total = exp_total_bullets.get(idx, 0)
            if total > 0 and changed / total > self.max_bullet_change_ratio:
                ratio_exceeded_indices.add(idx)

        safe: list[ProposedChange] = []
        flagged: list[ProposedChange] = []
        for c in all_changes:
            # Flag all changes for experiences that exceeded the ratio
            if c.experience_index is not None and c.experience_index in ratio_exceeded_indices:
                if not c.requires_review:
                    c.requires_review = True
                    c.review_reason = (
                        f"too many bullets changed in experience #{c.experience_index + 1} "
                        f"({exp_change_counts.get(c.experience_index, 0)}/"
                        f"{exp_total_bullets.get(c.experience_index, 0)} > "
                        f"{self.max_bullet_change_ratio:.0%})"
                    )
                flagged.append(c)
            elif c.change_type == ChangeType.BULLET_DELETED:
                flagged.append(c)
            elif c.has_new_skills:
                c.change_type = ChangeType.SKILL_ADD
                flagged.append(c)
            elif c.has_new_numbers:
                c.change_type = ChangeType.METRIC_ADD
                flagged.append(c)
            elif c.has_new_entities:
                c.change_type = ChangeType.EMPLOYER_ADD
                flagged.append(c)
            else:
                # Pure language improvement — no factual additions
                if c.change_type == ChangeType.BULLET:
                    c.change_type = ChangeType.REWRITE
                safe.append(c)

        logger.info(
            "FactGuard: %d changes total, %d safe, %d flagged",
            len(all_changes), len(safe), len(flagged),
        )

        return FactGuardResult(
            safe_changes=safe,
            flagged_changes=flagged,
            unsupported_numbers=all_unsupported_numbers,
            unsupported_entities=all_unsupported_entities,
            unsupported_skills=all_unsupported_skills,
        )

    def _check_text_change(
        self,
        change_type: ChangeType,
        section: str,
        original: str,
        rewritten: str,
        source_vocab: set[str],
        source_tech_lower: set[str],
        experience_index: int | None = None,
        bullet_index: int | None = None,
    ) -> ProposedChange:
        """Run deterministic checks on a single text change."""
        has_new_numbers = False
        has_new_entities = False
        has_new_skills = False

        # Check for new numbers
        orig_numbers = _extract_numbers(original)
        new_numbers = _extract_numbers(rewritten)
        if new_numbers - orig_numbers:
            has_new_numbers = True

        # Check for new entities (multi-word proper nouns not in source)
        orig_entities = _extract_entities(original)
        new_entities = _extract_entities(rewritten)
        truly_new = {
            e for e in (new_entities - orig_entities)
            if e.lower() not in source_vocab
        }
        if truly_new:
            has_new_entities = True

        # Check for new tech tokens not in source skills or experience
        # Uses normalized lowercase comparison to catch python/Python, etc.
        orig_tech = _extract_tech_tokens(original)
        new_tech = _extract_tech_tokens(rewritten)
        truly_new_tech = {
            t for t in (new_tech - orig_tech)
            if t.lower() not in source_tech_lower
        }
        if truly_new_tech:
            has_new_skills = True

        return ProposedChange(
            change_type=change_type,
            section=section,
            original=original,
            rewritten=rewritten,
            experience_index=experience_index,
            bullet_index=bullet_index,
            has_new_numbers=has_new_numbers,
            has_new_entities=has_new_entities,
            has_new_skills=has_new_skills,
        )
