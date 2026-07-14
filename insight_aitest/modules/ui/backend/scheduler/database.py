# -*- coding: utf-8 -*-
"""UI 定时调度数据库。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from insight_aitest.platform.persistence import Base, ensure_schema, get_engine, session_scope
from insight_aitest.modules.ui.backend.scheduler.models import ScheduledUIBatch


class ScheduledUIBatchDatabase:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Base.metadata.create_all(get_engine(db_path), tables=[ScheduledUIBatch.__table__])
        ensure_schema(db_path, [])

    def create(self, *, name: str, cron_expression: str, case_ids: list, config: dict, enabled: bool = True) -> int:
        sched = ScheduledUIBatch(
            id=None,
            name=name,
            cron_expression=cron_expression,
            case_ids=case_ids,
            config=config,
            enabled=enabled,
        )
        with session_scope(self.db_path) as s:
            s.add(sched)
            s.flush()
            return sched.id

    def get(self, sched_id: int) -> ScheduledUIBatch | None:
        with session_scope(self.db_path) as s:
            return s.get(ScheduledUIBatch, sched_id)

    def list(self) -> list[ScheduledUIBatch]:
        with session_scope(self.db_path) as s:
            return list(s.execute(
                select(ScheduledUIBatch).order_by(ScheduledUIBatch.id.desc())
            ).scalars())

    def list_enabled(self) -> list[ScheduledUIBatch]:
        with session_scope(self.db_path) as s:
            return list(s.execute(
                select(ScheduledUIBatch).where(ScheduledUIBatch.enabled == True)
            ).scalars())

    def update(self, sched_id: int, **kwargs) -> ScheduledUIBatch | None:
        with session_scope(self.db_path) as s:
            sched = s.get(ScheduledUIBatch, sched_id)
            if sched is None:
                return None
            for k, v in kwargs.items():
                if hasattr(sched, k):
                    setattr(sched, k, v)
            sched.updated_at = datetime.now()
            return sched

    def delete(self, sched_id: int) -> bool:
        with session_scope(self.db_path) as s:
            sched = s.get(ScheduledUIBatch, sched_id)
            if sched is None:
                return False
            s.delete(sched)
            return True

    def record_run(self, sched_id: int, status: str, batch_run_id: int | None) -> None:
        with session_scope(self.db_path) as s:
            sched = s.get(ScheduledUIBatch, sched_id)
            if sched is None:
                return
            sched.last_run_at = datetime.now()
            sched.last_status = status
            sched.last_batch_run_id = batch_run_id
