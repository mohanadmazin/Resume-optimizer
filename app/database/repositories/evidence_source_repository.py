"""Evidence sources repository."""
from __future__ import annotations


from app.database.session import get_session
from app.database.models import (
    CareerFact as CareerFactModel,
    CareerFactSource,
    ContentFactLink,
    EvidenceSource as EvidenceSourceModel,
    FactVerificationEvent,
)
from app.domain.evidence import (
    EvidenceSource,
    FactConfidence,
    FactVerificationEvent as FactVerificationEventModel,
    SourceType,
)


class EvidenceSourceRepository:
    """CRUD + queries for evidence sources, linking, and verification events."""

    def create_source(self, source: EvidenceSource) -> int:
        with get_session() as session:
            row = EvidenceSourceModel(
                source_type=source.source_type.value,
                name=source.name,
                file_path=source.file_path,
                excerpt=source.excerpt,
                page_reference=source.page_reference,
                notes=source.notes,
            )
            session.add(row)
            session.flush()
            return row.id

    def get_source(self, source_id: int) -> EvidenceSource | None:
        with get_session() as session:
            row = session.get(EvidenceSourceModel, source_id)
            if row is None:
                return None
            return self._source_to_domain(row)

    def list_sources(self, source_type: str | None = None) -> list[EvidenceSource]:
        with get_session() as session:
            query = session.query(EvidenceSourceModel)
            if source_type:
                query = query.filter(EvidenceSourceModel.source_type == source_type)
            rows = query.order_by(EvidenceSourceModel.created_at.desc()).all()
            return [self._source_to_domain(r) for r in rows]

    def link_source(self, fact_id: int, source_id: int) -> bool:
        with get_session() as session:
            existing = (
                session.query(CareerFactSource)
                .filter_by(fact_id=fact_id, source_id=source_id)
                .first()
            )
            if existing:
                return False
            session.add(CareerFactSource(fact_id=fact_id, source_id=source_id))
            return True

    def unlink_source(self, fact_id: int, source_id: int) -> bool:
        with get_session() as session:
            row = (
                session.query(CareerFactSource)
                .filter_by(fact_id=fact_id, source_id=source_id)
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            return True

    def get_fact_sources(self, fact_id: int) -> list[EvidenceSource]:
        with get_session() as session:
            fact = session.get(CareerFactModel, fact_id)
            if fact is None:
                return []
            return [self._source_to_domain(s) for s in fact.sources]

    def link_content(
        self,
        content_type: str,
        content_id: int,
        fact_id: int,
        relevance: str = "direct",
    ) -> bool:
        with get_session() as session:
            existing = (
                session.query(ContentFactLink)
                .filter_by(
                    content_type=content_type,
                    content_id=content_id,
                    fact_id=fact_id,
                )
                .first()
            )
            if existing:
                return False
            session.add(
                ContentFactLink(
                    content_type=content_type,
                    content_id=content_id,
                    fact_id=fact_id,
                    relevance=relevance,
                )
            )
            return True

    def get_fact_links(self, fact_id: int) -> list[dict[str, object]]:
        with get_session() as session:
            rows = (
                session.query(ContentFactLink)
                .filter_by(fact_id=fact_id)
                .all()
            )
            return [
                {
                    "content_type": r.content_type,
                    "content_id": r.content_id,
                    "relevance": r.relevance,
                }
                for r in rows
            ]

    def add_verification_event(self, event: FactVerificationEventModel) -> int:
        with get_session() as session:
            row = FactVerificationEvent(
                fact_id=event.fact_id,
                previous_confidence=event.previous_confidence.value,
                new_confidence=event.new_confidence.value,
                reason=event.reason,
                verified_by=event.verified_by,
            )
            session.add(row)
            session.flush()
            return row.id

    def get_verification_history(self, fact_id: int) -> list[FactVerificationEventModel]:
        with get_session() as session:
            rows = (
                session.query(FactVerificationEvent)
                .filter_by(fact_id=fact_id)
                .order_by(FactVerificationEvent.created_at.desc())
                .all()
            )
            return [
                FactVerificationEventModel(
                    id=r.id,
                    fact_id=r.fact_id,
                    previous_confidence=FactConfidence(r.previous_confidence),
                    new_confidence=FactConfidence(r.new_confidence),
                    reason=r.reason or "",
                    verified_by=r.verified_by or "user",
                    created_at=str(r.created_at) if r.created_at else "",
                )
                for r in rows
            ]

    @staticmethod
    def _source_to_domain(row: EvidenceSourceModel) -> EvidenceSource:
        return EvidenceSource(
            id=row.id,
            source_type=SourceType(row.source_type or "document"),
            name=row.name or "",
            file_path=row.file_path or "",
            excerpt=row.excerpt or "",
            page_reference=row.page_reference or "",
            notes=row.notes or "",
            created_at=str(row.created_at) if row.created_at else "",
        )
