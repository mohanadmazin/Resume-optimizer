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


class FactGuard:
    """Deterministic post-generation validator for AI resume changes."""

    def __init__(self, max_bullet_change_ratio: float = 0.6):
        """Args:
            max_bullet_change_ratio: maximum fraction of bullets that can
                change in a single experience entry before flagging.
                0.6 means "if more than 60% of bullets changed, flag it."
        """
        self.max_bullet_change_ratio = max_bullet_change_ratio

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

        # --- Summary ---
        if source.summary.strip() != optimized.summary.strip():
            change = self._check_text_change(
                ChangeType.SUMMARY, "Summary",
                source.summary, optimized.summary, source,
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
                source.headline, optimized.headline, source,
            )
            all_changes.append(change)

        # --- Experience bullets ---
        if len(source.experience) == len(optimized.experience):
            for idx, (src_exp, opt_exp) in enumerate(zip(source.experience, optimized.experience)):
                section = f"{src_exp.title or 'Experience'} #{idx + 1}"
                src_bullets = src_exp.bullets
                opt_bullets = opt_exp.bullets

                # Use SequenceMatcher to detect inserted, deleted, rewritten bullets
                matcher = SequenceMatcher(None, src_bullets, opt_bullets)
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag == "equal":
                        continue
                    elif tag == "delete":
                        # Bullets removed — no change to flag in the optimized output
                        continue
                    elif tag == "insert":
                        # New bullets inserted by AI — must be checked
                        for jb in range(j1, j2):
                            new_bullet = opt_bullets[jb]
                            change = self._check_text_change(
                                ChangeType.BULLET, section,
                                "", new_bullet, source,
                            )
                            all_changes.append(change)
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
                                old_b, new_b, source,
                            )
                            all_changes.append(change)
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

        safe = [c for c in all_changes if not (c.has_new_numbers or c.has_new_entities or c.has_new_skills)]
        flagged = [c for c in all_changes if c.has_new_numbers or c.has_new_entities or c.has_new_skills]

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
        source: ResumeData,
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
        source_vocab = _source_vocabulary(source)
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
        source_tech: set[str] = set()
        for s in source.skills:
            norm = _normalize_skill(s)
            source_tech.add(norm)
            source_tech.update(_extract_tech_tokens(s))
        for exp in source.experience:
            for b in exp.bullets:
                source_tech.update(_extract_tech_tokens(b))
        # Also add lowercase matches
        source_tech_lower = {t.lower() for t in source_tech}
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
            has_new_numbers=has_new_numbers,
            has_new_entities=has_new_entities,
            has_new_skills=has_new_skills,
        )
