# -*- coding: utf-8 -*-
"""套件数据库（SuiteDatabase + SuiteRunDatabase，spec E.1 §2 + P0-1 ORM 迁移）。

复用 api.db。
SuiteRunDatabase 启动时回收僵尸 running → interrupted（spec E.1 §3.6）。

P0-1：从裸 sqlite3 + threading.local 迁移到平台 session_scope + ORM。
对外方法签名/返回类型完全不变（routes/suite_executor/tests 零改动）。
case_ids/setup/teardown/suite_snapshot/case_run_ids 均原生 JSON 列（dict/list 自动序列化）。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update

from insight_aitest.platform.persistence import Base, get_engine, session_scope
from insight_aitest.modules.api.backend.persistence.suite_models import (
    Suite,
    SuiteRunRecord,
    SuiteRunStatus,
)


class SuiteDatabase:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Base.metadata.create_all(get_engine(db_path), tables=[Suite.__table__])

    def create(self, suite: Suite) -> int:
        with session_scope(self.db_path) as s:
            s.add(suite)
            s.flush()
            return suite.id

    def get(self, suite_id: int) -> Suite | None:
        with session_scope(self.db_path) as s:
            return s.get(Suite, suite_id)

    def list(self) -> list[Suite]:
        stmt = select(Suite).order_by(Suite.id.desc())
        with session_scope(self.db_path) as s:
            return list(s.scalars(stmt))

    def update(self, suite_id: int, **fields) -> None:
        allowed = ("name", "description", "case_ids", "setup", "teardown")
        with session_scope(self.db_path) as s:
            suite = s.get(Suite, suite_id)
            if suite is None:
                return
            for k in allowed:
                if k not in fields or fields[k] is None:
                    continue
                setattr(suite, k, fields[k])
            suite.updated_at = datetime.now()

    def delete(self, suite_id: int) -> bool:
        with session_scope(self.db_path) as s:
            suite = s.get(Suite, suite_id)
            if suite is None:
                return False
            s.delete(suite)
            return True


class SuiteRunDatabase:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Base.metadata.create_all(get_engine(db_path), tables=[SuiteRunRecord.__table__])
        # 僵尸回收：启动时把遗留 running 标 interrupted
        with session_scope(self.db_path) as s:
            s.execute(
                update(SuiteRunRecord)
                .where(SuiteRunRecord.status == SuiteRunStatus.RUNNING)
                .values(status=SuiteRunStatus.INTERRUPTED, finished_at=datetime.now())
            )

    def create(self, run: SuiteRunRecord) -> int:
        with session_scope(self.db_path) as s:
            s.add(run)
            s.flush()
            return run.id

    def get(self, run_id: int) -> SuiteRunRecord | None:
        with session_scope(self.db_path) as s:
            run = s.get(SuiteRunRecord, run_id)
            if run is None:
                return None
            s.expunge(run)  # 脱离 session（suite_snapshot 含 list，避免回写问题）
        return run

    def list(
        self,
        suite_id: int | None = None,
        status: SuiteRunStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        stmt = select(
            SuiteRunRecord.id,
            SuiteRunRecord.suite_id,
            SuiteRunRecord.suite_name,
            SuiteRunRecord.status,
            SuiteRunRecord.total,
            SuiteRunRecord.done,
            SuiteRunRecord.setup_status,
            SuiteRunRecord.started_at,
            SuiteRunRecord.finished_at,
            SuiteRunRecord.environment_name,
        )
        if suite_id is not None:
            stmt = stmt.where(SuiteRunRecord.suite_id == suite_id)
        if status is not None:
            stmt = stmt.where(SuiteRunRecord.status == status)
        stmt = stmt.order_by(SuiteRunRecord.id.desc()).limit(limit).offset(offset)
        with session_scope(self.db_path) as s:
            rows = s.execute(stmt).all()
        return [
            {
                "id": r.id,
                "suite_id": r.suite_id,
                "suite_name": r.suite_name,
                "status": r.status.value if hasattr(r.status, "value") else r.status,
                "total": r.total,
                "done": r.done,
                "setup_status": r.setup_status,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "environment_name": r.environment_name,
            }
            for r in rows
        ]

    def update_progress(self, run_id: int, *, done: int, case_run_id: int) -> None:
        """跑完一条 case：更新 done + 追加 run_id。"""
        with session_scope(self.db_path) as s:
            run = s.get(SuiteRunRecord, run_id)
            if run is None:
                return
            ids = list(run.case_run_ids)
            ids.append(case_run_id)
            run.done = done
            run.case_run_ids = ids

    def update_setup_status(self, run_id: int, setup_status: str | None) -> None:
        with session_scope(self.db_path) as s:
            run = s.get(SuiteRunRecord, run_id)
            if run is None:
                return
            run.setup_status = setup_status

    def finish(self, run_id: int, *, status: SuiteRunStatus, error: str | None = None) -> None:
        with session_scope(self.db_path) as s:
            run = s.get(SuiteRunRecord, run_id)
            if run is None:
                return
            run.status = status
            run.finished_at = datetime.now()
            run.error = error

    def delete(self, run_id: int) -> bool:
        with session_scope(self.db_path) as s:
            run = s.get(SuiteRunRecord, run_id)
            if run is None:
                return False
            s.delete(run)
            return True
