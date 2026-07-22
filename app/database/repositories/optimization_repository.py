"""Repository for persisted optimization runs and review decisions."""
from __future__ import annotations

import json

from app.database.models import Optimization
from app.database.repositories.base import BaseRepository


class OptimizationRepository(BaseRepository):
    def save(
        self,
        resume_id: int,
        job_id: int,
        model: str,
        optimized_json: str,
        *,
        fact_guard_json: str = "{}",
        accepted_changes: list[int] | None = None,
        original_score: int = 0,
        optimized_score: int = 0,
    ) -> int:
        row = Optimization(
            resume_id=resume_id,
            job_id=job_id,
            model=model,
            optimized_json=optimized_json,
            fact_guard_json=fact_guard_json,
            accepted_changes_json=json.dumps(accepted_changes or []),
            original_score=original_score,
            optimized_score=optimized_score,
        )
        self.add(row)
        self.flush()
        return int(row.id)

    def get(self, optimization_id: int) -> Optimization | None:
        return self.session.query(Optimization).filter(Optimization.id == optimization_id).first()

    def get_latest_for_pair(self, resume_id: int, job_id: int) -> Optimization | None:
        return (
            self.session.query(Optimization)
            .filter(Optimization.resume_id == resume_id, Optimization.job_id == job_id)
            .order_by(Optimization.id.desc())
            .first()
        )

    def update_review(
        self,
        optimization_id: int,
        *,
        optimized_json: str,
        fact_guard_json: str,
        accepted_changes: list[int],
        optimized_score: int,
    ) -> bool:
        row = self.get(optimization_id)
        if row is None:
            return False
        row.optimized_json = optimized_json
        row.fact_guard_json = fact_guard_json
        row.accepted_changes_json = json.dumps(accepted_changes)
        row.optimized_score = optimized_score
        return True
