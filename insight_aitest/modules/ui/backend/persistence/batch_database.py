# -*- coding: utf-8 -*-
"""UI 批量执行数据库（UIBatchRunDatabase）。

独立 ui.db（与 ui_runs 同库）。单表 ui_batch_runs。
"""

from __future__ import annotations

from sqlalchemy import select

from insight_aitest.platform.persistence import Base, ensure_schema, get_engine, session_scope
from insight_aitest.modules.ui.backend.persistence.batch_models import (
    BatchRunStatus,
    UIBatchRun,
)


class UIBatchRunDatabase:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Base.metadata.create_all(get_engine(db_path), tables=[UIBatchRun.__table__])
        ensure_schema(db_path, [])

    def create(self, batch: UIBatchRun) -> int:
        with session_scope(self.db_path) as s:
            s.add(batch)
            s.flush()
            return batch.id

    def get(self, batch_id: int) -> UIBatchRun | None:
        with session_scope(self.db_path) as s:
            return s.get(UIBatchRun, batch_id)

    def update(
        self,
        batch_id: int,
        *,
        status: BatchRunStatus | None = None,
        passed: int | None = None,
        failed: int | None = None,
        error: int | None = None,
        case_run_ids: list | None = None,
        finished_at=None,
    ) -> UIBatchRun | None:
        with session_scope(self.db_path) as s:
            batch = s.get(UIBatchRun, batch_id)
            if batch is None:
                return None
            if status is not None:
                batch.status = status
            if passed is not None:
                batch.passed = passed
            if failed is not None:
                batch.failed = failed
            if error is not None:
                batch.error = error
            if case_run_ids is not None:
                batch.case_run_ids = case_run_ids
            if finished_at is not None:
                batch.finished_at = finished_at
            return batch

    def list(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """摘要列表（不含 config 详情）。"""
        stmt = (
            select(
                UIBatchRun.id,
                UIBatchRun.name,
                UIBatchRun.case_ids,
                UIBatchRun.status,
                UIBatchRun.total,
                UIBatchRun.passed,
                UIBatchRun.failed,
                UIBatchRun.error,
                UIBatchRun.started_at,
                UIBatchRun.finished_at,
            )
            .order_by(UIBatchRun.id.desc())
            .limit(limit)
            .offset(offset)
        )
        with session_scope(self.db_path) as s:
            rows = s.execute(stmt).all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "case_ids": r.case_ids,
                "status": r.status.value if hasattr(r.status, "value") else r.status,
                "total": r.total,
                "passed": r.passed,
                "failed": r.failed,
                "error": r.error,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
            }
            for r in rows
        ]

    def delete(self, batch_id: int) -> bool:
        with session_scope(self.db_path) as s:
            batch = s.get(UIBatchRun, batch_id)
            if batch is None:
                return False
            s.delete(batch)
            return True
