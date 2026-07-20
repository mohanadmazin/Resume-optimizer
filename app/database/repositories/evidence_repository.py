"""Career facts repository."""
from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.database.session import get_session
from app.database.models import CareerFact as CareerFactModel
from app.domain.evidence import CareerFact, FactConfidence, FactType


class CareerFactRepository:
    """CRUD + queries for career facts."""

    def create(self, fact: CareerFact) -> int:
        with get_session() as session:
            row = CareerFactModel(
                statement=fact.statement,
                fact_type=fact.fact_type.value,
                confidence=fact.confidence.value,
                employer=fact.employer,
                project=fact.project,
                date_from=fact.date_from,
                date_to=fact.date_to,
                sensitive=fact.sensitive,
                metrics_json=__import__("json").dumps(fact.metrics_json),
                tags_json=__import__("json").dumps(fact.tags),
                notes=fact.notes,
            )
            session.add(row)
            session.flush()
            return row.id

    def get(self, fact_id: int) -> CareerFact | None:
        with get_session() as session:
            row = session.get(CareerFactModel, fact_id)
            if row is None:
                return None
            return self._to_domain(row)

    def list_all(
        self,
        fact_type: str | None = None,
        confidence: str | None = None,
        employer: str | None = None,
        tag: str | None = None,
    ) -> list[CareerFact]:
        with get_session() as session:
            query = session.query(CareerFactModel)
            if fact_type:
                query = query.filter(CareerFactModel.fact_type == fact_type)
            if confidence:
                query = query.filter(CareerFactModel.confidence == confidence)
            if employer:
                query = query.filter(CareerFactModel.employer == employer)
            if tag:
                query = query.filter(CareerFactModel.tags_json.contains(f'"{tag}"'))
            rows = query.order_by(CareerFactModel.created_at.desc()).all()
            return [self._to_domain(r) for r in rows]

    def update(self, fact_id: int, updates: dict[str, Any]) -> bool:
        with get_session() as session:
            row = session.get(CareerFactModel, fact_id)
            if row is None:
                return False
            import json

            for key, value in updates.items():
                if key == "fact_type":
                    row.fact_type = value.value if hasattr(value, "value") else str(value)
                elif key == "confidence":
                    row.confidence = value.value if hasattr(value, "value") else str(value)
                elif key == "metrics_json":
                    row.metrics_json = json.dumps(value)
                elif key == "tags_json":
                    row.tags_json = json.dumps(value)
                elif hasattr(row, key):
                    setattr(row, key, value)
            return True

    def delete(self, fact_id: int) -> bool:
        with get_session() as session:
            row = session.get(CareerFactModel, fact_id)
            if row is None:
                return False
            session.delete(row)
            return True

    def search(self, query_text: str, limit: int = 20) -> list[CareerFact]:
        with get_session() as session:
            rows = (
                session.query(CareerFactModel)
                .filter(CareerFactModel.statement.contains(query_text))
                .limit(limit)
                .all()
            )
            return [self._to_domain(r) for r in rows]

    def count(self) -> int:
        with get_session() as session:
            return session.query(CareerFactModel).count()

    def count_by_type(self) -> dict[str, int]:
        with get_session() as session:
            rows = (
                session.query(CareerFactModel.fact_type, text("COUNT(*)"))
                .group_by(CareerFactModel.fact_type)
                .all()
            )
            return {row[0]: row[1] for row in rows}

    @staticmethod
    def _to_domain(row: CareerFactModel) -> CareerFact:
        import json

        metrics = {}
        if row.metrics_json:
            try:
                metrics = json.loads(row.metrics_json)
            except Exception:
                pass
        tags = []
        if row.tags_json:
            try:
                tags = json.loads(row.tags_json)
            except Exception:
                pass
        return CareerFact(
            id=row.id,
            statement=row.statement or "",
            fact_type=FactType(row.fact_type or "other"),
            confidence=FactConfidence(row.confidence or "user_estimate"),
            employer=row.employer or "",
            project=row.project or "",
            date_from=row.date_from or "",
            date_to=row.date_to or "",
            sensitive=bool(row.sensitive),
            metrics_json=metrics,
            tags=tags,
            notes=row.notes or "",
            created_at=str(row.created_at) if row.created_at else "",
            updated_at=str(row.updated_at) if row.updated_at else "",
        )
