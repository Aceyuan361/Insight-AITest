# -*- coding: utf-8 -*-
"""定时任务数据库（ScheduledSuiteDatabase）。

CRUD + 查询 enabled 列表（scheduler 启动时重建 jobs 用）。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from insight_aitest.platform.persistence import Base, get_engine, session_scope
from insight_aitest.modules.api.backend.scheduler.models import ScheduledSuite


class ScheduledSuiteDatabase:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Base.metadata.create_all(get_engine(db_path), tables=[ScheduledSuite.__table__])

    def create(
        self, *, name: str, suite_id: int, cron_expression: str,
        environment_id: int | None = None, enabled: bool = True,
    ) -> int:
        sched = ScheduledSuite(
            name=name,
            suite_id=suite_id,
            cron_expression=cron_expression,
            environment_id=environment_id,
            enabled=enabled,
        )
        with session_scope(self.db_path) as s:
            s.add(sched)
            s.flush()
            return sched.id

    def get(self, sched_id: int) -> ScheduledSuite | None:
        with session_scope(self.db_path) as s:
            return s.get(ScheduledSuite, sched_id)

    def list(self) -> list[ScheduledSuite]:
        stmt = select(ScheduledSuite).order_by(ScheduledSuite.id)
        with session_scope(self.db_path) as s:
            return list(s.scalars(stmt))

    def list_enabled(self) -> list[ScheduledSuite]:
        stmt = select(ScheduledSuite).where(ScheduledSuite.enabled == True)  # noqa: E712
        with session_scope(self.db_path) as s:
            return list(s.scalars(stmt))

    def update(self, sched_id: int, **fields) -> None:
        allowed = ("name", "suite_id", "cron_expression", "environment_id", "enabled",
                    "last_run_at", "last_status", "last_suite_run_id")
        with session_scope(self.db_path) as s:
            sched = s.get(ScheduledSuite, sched_id)
            if sched is None:
                return
            for k in allowed:
                if k not in fields or fields[k] is None:
                    continue
                setattr(sched, k, fields[k])
            sched.updated_at = datetime.now()

    def delete(self, sched_id: int) -> bool:
        with session_scope(self.db_path) as s:
            sched = s.get(ScheduledSuite, sched_id)
            if sched is None:
                return False
            s.delete(sched)
            return True

    def record_run(self, sched_id: int, status: str, suite_run_id: int | None) -> None:
        """记录一次执行结果。"""
        with session_scope(self.db_path) as s:
            sched = s.get(ScheduledSuite, sched_id)
            if sched is None:
                return
            sched.last_run_at = datetime.now()
            sched.last_status = status
            sched.last_suite_run_id = suite_run_id
            sched.updated_at = datetime.now()
