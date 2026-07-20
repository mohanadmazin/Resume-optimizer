"""Evidence Vault service — business logic for career facts and evidence."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.domain.evidence import (
    CareerFact,
    EvidenceSource,
    FactConfidence,
    FactType,
    FactVerificationEvent,
    FactWithSources,
)

if TYPE_CHECKING:
    from app.database.repositories.evidence_repository import CareerFactRepository
    from app.database.repositories.evidence_source_repository import (
        EvidenceSourceRepository,
    )

FACT_TYPE_KEYWORDS: dict[FactType, list[str]] = {
    FactType.ACHIEVEMENT: ["achieved", "accomplished", "delivered", "exceeded", "surpassed", "improved", "increased", "reduced", "saved"],
    FactType.METRIC: ["%", "revenue", "cost", "budget", "million", "billion", "thousand", "percent", "faster", "more"],
    FactType.TECHNOLOGY: ["python", "javascript", "react", "aws", "docker", "kubernetes", "sql", "api", "database"],
    FactType.AWARD: ["award", "recognized", "prize", "honored", "certificate"],
    FactType.CERTIFICATION: ["certified", "certification", "license", "credential"],
    FactType.PUBLICATION: ["published", "article", "paper", "blog", "author"],
    FactType.PROJECT: ["project", "initiative", "launched", "built", "developed", "implemented"],
    FactType.TEAM: ["team", "led", "managed", "mentored", "supervised", "coached"],
    FactType.BUDGET: ["budget", "funded", "financial", "cost"],
    FactType.CUSTOMER: ["client", "customer", "stakeholder", "partner"],
    FactType.TESTIMONIAL: ["testimonial", "review", "feedback", "referenced"],
    FactType.PORTFOLIO: ["portfolio", "demo", "sample", "showcase"],
}

METRIC_PATTERN = re.compile(
    r"\$[\d,]+(?:\.\d+)?[mbkMBK]?"
    r"|\d+(?:\.\d+)?\s*%"
    r"|\d+(?:,\d{3})+\b"
)


class EvidenceVault:
    """Service for managing career facts and evidence sources."""

    def __init__(
        self,
        fact_repo: CareerFactRepository | None = None,
        source_repo: EvidenceSourceRepository | None = None,
    ) -> None:
        from app.database.repositories.evidence_repository import CareerFactRepository
        from app.database.repositories.evidence_source_repository import (
            EvidenceSourceRepository,
        )

        self._fact_repo = fact_repo or CareerFactRepository()
        self._source_repo = source_repo or EvidenceSourceRepository()

    def add_fact(self, fact: CareerFact) -> int:
        if not fact.statement.strip():
            raise ValueError("Fact statement cannot be empty.")
        if not fact.fact_type or fact.fact_type == FactType.OTHER:
            fact.fact_type = self._classify_fact(fact.statement)
        if not fact.confidence or fact.confidence == FactConfidence.UNSUPPORTED:
            fact.confidence = FactConfidence.USER_ESTIMATE
        fact.tags = fact.tags or self._extract_tags(fact.statement)
        if not fact.metrics_json:
            fact.metrics_json = self._extract_metrics(fact.statement)
        return self._fact_repo.create(fact)

    def update_fact(self, fact_id: int, updates: dict[str, object]) -> bool:
        return self._fact_repo.update(fact_id, updates)

    def delete_fact(self, fact_id: int) -> bool:
        return self._fact_repo.delete(fact_id)

    def get_fact(self, fact_id: int) -> CareerFact | None:
        return self._fact_repo.get(fact_id)

    def list_facts(
        self,
        fact_type: str | None = None,
        confidence: str | None = None,
        employer: str | None = None,
        tag: str | None = None,
    ) -> list[CareerFact]:
        return self._fact_repo.list_all(
            fact_type=fact_type,
            confidence=confidence,
            employer=employer,
            tag=tag,
        )

    def search_facts(self, query: str, limit: int = 20) -> list[CareerFact]:
        return self._fact_repo.search(query, limit=limit)

    def verify_fact(self, fact_id: int, confidence: FactConfidence, reason: str = "") -> bool:
        fact = self._fact_repo.get(fact_id)
        if fact is None:
            return False
        event = FactVerificationEvent(
            fact_id=fact_id,
            previous_confidence=fact.confidence,
            new_confidence=confidence,
            reason=reason,
        )
        self._source_repo.add_verification_event(event)
        return self._fact_repo.update(fact_id, {"confidence": confidence})

    def reject_fact(self, fact_id: int, reason: str = "") -> bool:
        return self.verify_fact(
            fact_id, FactConfidence.CONTRADICTORY, reason=reason
        )

    def add_source(self, source: EvidenceSource) -> int:
        return self._source_repo.create_source(source)

    def link_source(self, fact_id: int, source_id: int) -> bool:
        return self._source_repo.link_source(fact_id, source_id)

    def unlink_source(self, fact_id: int, source_id: int) -> bool:
        return self._source_repo.unlink_source(fact_id, source_id)

    def get_fact_with_sources(self, fact_id: int) -> FactWithSources | None:
        fact = self._fact_repo.get(fact_id)
        if fact is None:
            return None
        sources = self._source_repo.get_fact_sources(fact_id)
        links = self._source_repo.get_fact_links(fact_id)
        return FactWithSources(
            fact=fact,
            sources=sources,
            linked_content_count=len(links),
        )

    def get_verification_history(self, fact_id: int) -> list[FactVerificationEvent]:
        return self._source_repo.get_verification_history(fact_id)

    def get_all_sources(self, source_type: str | None = None) -> list[EvidenceSource]:
        return self._source_repo.list_sources(source_type=source_type)

    def import_facts_from_resume(
        self,
        resume_text: str,
        employer: str = "",
    ) -> list[int]:
        bullets = [
            line.strip()
            for line in resume_text.split("\n")
            if line.strip()
            and len(line.strip()) > 20
            and not line.strip().startswith("#")
        ]
        fact_ids: list[int] = []
        for bullet in bullets[:50]:
            fact = CareerFact(
                statement=bullet,
                employer=employer,
                fact_type=self._classify_fact(bullet),
                confidence=FactConfidence.REASONABLE_PARAPHRASE,
                tags=self._extract_tags(bullet),
                metrics_json=self._extract_metrics(bullet),
            )
            fid = self.add_fact(fact)
            fact_ids.append(fid)
        return fact_ids

    def get_vault_stats(self) -> dict[str, object]:
        total = self._fact_repo.count()
        by_type = self._fact_repo.count_by_type()
        return {"total_facts": total, "by_type": by_type}

    @staticmethod
    def _classify_fact(statement: str) -> FactType:
        lower = statement.lower()
        best_type = FactType.OTHER
        best_score = 0
        for fact_type, keywords in FACT_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lower)
            if score > best_score:
                best_score = score
                best_type = fact_type
        return best_type

    @staticmethod
    def _extract_tags(statement: str) -> list[str]:
        lower = statement.lower()
        tags: list[str] = []
        tech_keywords = [
            "python", "javascript", "react", "aws", "docker", "kubernetes",
            "sql", "api", "git", "java", "typescript", "html", "css",
            "postgresql", "mysql", "redis", "graphql", "rest",
        ]
        for kw in tech_keywords:
            if kw in lower:
                tags.append(kw)
        return tags

    @staticmethod
    def _extract_metrics(statement: str) -> dict[str, str]:
        metrics: dict[str, str] = {}
        matches = METRIC_PATTERN.findall(statement)
        for i, match in enumerate(matches):
            metrics[f"metric_{i}"] = match
        return metrics

    # ── Resume data import ──────────────────────────────────────────────

    def import_from_resume_data(self, resume_data: object) -> list[int]:
        """Extract career facts from a parsed ResumeData object.

        Creates facts from experience bullets, skills, education, and
        certifications. Deduplicates by checking existing fact statements
        before inserting.
        """
        from app.domain.resume import ResumeData

        if not isinstance(resume_data, ResumeData):
            return []

        existing = {f.statement.strip().lower() for f in self.list_facts()}
        fact_ids: list[int] = []

        # Import experience bullets
        for exp in resume_data.experience:
            for bullet in exp.bullets:
                stmt = bullet.strip()
                if not stmt or stmt.lower() in existing:
                    continue
                fact = CareerFact(
                    statement=stmt,
                    fact_type=self._classify_fact(stmt),
                    confidence=FactConfidence.REASONABLE_PARAPHRASE,
                    employer=exp.company,
                    date_from=exp.start_date,
                    date_to=exp.end_date,
                    tags=self._extract_tags(stmt),
                    metrics_json=self._extract_metrics(stmt),
                )
                fid = self.add_fact(fact)
                fact_ids.append(fid)
                existing.add(stmt.lower())

        # Import skills as technology facts
        for skill in resume_data.skills:
            stmt = f"Proficient in {skill}"
            if stmt.lower() in existing:
                continue
            fact = CareerFact(
                statement=stmt,
                fact_type=FactType.TECHNOLOGY,
                confidence=FactConfidence.USER_CONFIRMED,
                tags=[skill.lower()],
            )
            fid = self.add_fact(fact)
            fact_ids.append(fid)
            existing.add(stmt.lower())

        # Import education
        for edu in resume_data.education:
            stmt = f"{edu.degree} from {edu.institution}".strip()
            if not edu.degree and not edu.institution:
                continue
            if stmt.lower() in existing:
                continue
            fact = CareerFact(
                statement=stmt,
                fact_type=FactType.CERTIFICATION,
                confidence=FactConfidence.VERIFIED,
                date_from=edu.year,
            )
            fid = self.add_fact(fact)
            fact_ids.append(fid)
            existing.add(stmt.lower())

        # Import certifications
        for cert in resume_data.certifications:
            stmt = cert.strip()
            if not stmt or stmt.lower() in existing:
                continue
            fact = CareerFact(
                statement=stmt,
                fact_type=FactType.CERTIFICATION,
                confidence=FactConfidence.VERIFIED,
            )
            fid = self.add_fact(fact)
            fact_ids.append(fid)
            existing.add(stmt.lower())

        # Import projects
        for proj in resume_data.projects:
            stmt = proj.title.strip()
            if not stmt or stmt.lower() in existing:
                continue
            bullets_text = "; ".join(proj.bullets) if proj.bullets else proj.description
            full_stmt = f"{stmt}: {bullets_text}" if bullets_text else stmt
            fact = CareerFact(
                statement=full_stmt[:500],
                fact_type=FactType.PROJECT,
                confidence=FactConfidence.REASONABLE_PARAPHRASE,
                date_from=proj.start_date,
                date_to=proj.end_date,
            )
            fid = self.add_fact(fact)
            fact_ids.append(fid)
            existing.add(stmt.lower())

        return fact_ids

    def build_master_profile(self, facts: list[CareerFact] | None = None) -> "MasterCareerProfile":  # noqa: F821
        """Assemble a MasterCareerProfile from vault facts.

        Groups facts by employer into career entries, extracts skills
        and certifications, and builds a comprehensive profile.
        """
        from app.domain.master_profile import (
            CareerEntry,
            MasterCareerProfile,
        )

        if facts is None:
            facts = self.list_facts()

        # Group facts by employer into career entries
        employer_entries: dict[str, list[CareerFact]] = {}
        orphan_facts: list[CareerFact] = []

        for fact in facts:
            if fact.fact_type == FactType.CERTIFICATION:
                continue  # handled separately
            if fact.employer:
                employer_entries.setdefault(fact.employer, []).append(fact)
            else:
                orphan_facts.append(fact)

        entries: list[CareerEntry] = []
        entry_id = 0
        for employer, emp_facts in sorted(employer_entries.items()):
            # Determine date range from facts
            dates_from = [f.date_from for f in emp_facts if f.date_from]
            dates_to = [f.date_to for f in emp_facts if f.date_to]
            date_from = min(dates_from) if dates_from else ""
            date_to = max(dates_to) if dates_to else ""

            # Guess role from first achievement or responsibility
            role = ""
            for f in emp_facts:
                if f.fact_type in (FactType.ACHIEVEMENT, FactType.RESPONSIBILITY):
                    role = f.statement[:60]
                    break

            bullets = [f.statement for f in emp_facts]
            tags = list({t for f in emp_facts for t in f.tags})

            entries.append(CareerEntry(
                id=entry_id,
                role=role,
                company=employer,
                date_from=date_from,
                date_to=date_to,
                bullets=bullets,
                tags=tags,
            ))
            entry_id += 1

        # Add orphan facts as a separate entry
        if orphan_facts:
            bullets = [f.statement for f in orphan_facts]
            tags = list({t for f in orphan_facts for t in f.tags})
            entries.append(CareerEntry(
                id=entry_id,
                role="Other Experience",
                company="",
                bullets=bullets,
                tags=tags,
            ))

        # Extract skills from technology facts
        skills = sorted({
            tag
            for f in facts
            if f.fact_type == FactType.TECHNOLOGY
            for tag in f.tags
        })

        # Extract certifications
        certifications = [
            f.statement for f in facts
            if f.fact_type == FactType.CERTIFICATION
        ]

        return MasterCareerProfile(
            name="Career Profile",
            entries=entries,
            skills=skills,
            certifications=certifications,
            total_fact_count=len(facts),
        )
