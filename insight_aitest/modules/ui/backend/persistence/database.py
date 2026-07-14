# -*- coding: utf-8 -*-
"""UI 执行历史数据库（UIRunDatabase，spec F §5 + P0-1 ORM 迁移）。

独立 ui.db（~/.insight_eye/ui.db）。单表 ui_runs，steps 序列化为 results_json。历史不可变（无 update）。
结构与 E 的 RunDatabase 同形，加 base_url_used 字段。

P0-1：从裸 sqlite3 + threading.local 迁移到平台 session_scope + ORM。
对外方法签名/返回类型完全不变（routes/executor/tests 零改动）。
steps（list[UIStepResult]）↔ results_json（JSON 列）由本类桥接。
"""

from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import select

from insight_aitest.platform.persistence import Base, ensure_schema, get_engine, session_scope
from insight_aitest.modules.ui.backend.persistence.models import RunRecord, RunStatus, UIStepResult


def _ensure_ui_run_project_column(db_path: str) -> None:
    """增量迁移：给旧 ui_runs 表补 project_id 列（幂等）。"""
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(ui_runs)")}
        if "project_id" not in cols:
            conn.execute("ALTER TABLE ui_runs ADD COLUMN project_id INTEGER")
        conn.commit()


class UIRunDatabase:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Base.metadata.create_all(get_engine(db_path), tables=[RunRecord.__table__])
        ensure_schema(db_path, [_ensure_ui_run_project_column])

    def create_run(self, run: RunRecord) -> int:
        # UIStepResult 对象 → dict（存 results_json JSON 列）
        run.steps = [asdict(s) if isinstance(s, UIStepResult) else s for s in run.steps]
        with session_scope(self.db_path) as s:
            s.add(run)
            s.flush()
            return run.id

    def get_run(self, run_id: int) -> RunRecord | None:
        with session_scope(self.db_path) as s:
            run = s.get(RunRecord, run_id)
            if run is None:
                return None
            s.expunge(run)  # 脱离 session 再改 steps（避免回写 StepResult 到 JSON 列）
        # dict → UIStepResult 对象（业务层期望 run.steps 是 UIStepResult 列表）
        run.steps = [UIStepResult(**st) for st in run.steps]
        return run

    def list_runs(
        self,
        case_id: int | None = None,
        status: RunStatus | None = None,
        project_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """摘要列表（不含 steps）。"""
        stmt = select(
            RunRecord.id,
            RunRecord.case_id,
            RunRecord.case_title,
            RunRecord.status,
            RunRecord.total_steps,
            RunRecord.passed_steps,
            RunRecord.started_at,
            RunRecord.duration_ms,
            RunRecord.base_url_used,
            RunRecord.project_id,
        )
        if case_id is not None:
            stmt = stmt.where(RunRecord.case_id == case_id)
        if status is not None:
            stmt = stmt.where(RunRecord.status == status)
        if project_id is not None:
            stmt = stmt.where(RunRecord.project_id == project_id)
        stmt = stmt.order_by(RunRecord.id.desc()).limit(limit).offset(offset)
        with session_scope(self.db_path) as s:
            rows = s.execute(stmt).all()
        return [
            {
                "id": r.id,
                "case_id": r.case_id,
                "case_title": r.case_title,
                "status": r.status.value if hasattr(r.status, "value") else r.status,
                "total_steps": r.total_steps,
                "passed_steps": r.passed_steps,
                "started_at": r.started_at,
                "duration_ms": r.duration_ms,
                "base_url_used": r.base_url_used,
                "project_id": r.project_id,
            }
            for r in rows
        ]

    def delete_run(self, run_id: int) -> bool:
        with session_scope(self.db_path) as s:
            run = s.get(RunRecord, run_id)
            if run is None:
                return False
            s.delete(run)
            return True

    def count_by_project(self, project_id: int | None) -> int:
        """统计某项目下的 UI 执行记录数（project_id=None 统计未分类）。"""
        from sqlalchemy import func

        stmt = select(func.count(RunRecord.id))
        if project_id is not None:
            stmt = stmt.where(RunRecord.project_id == project_id)
        else:
            stmt = stmt.where(RunRecord.project_id.is_(None))
        with session_scope(self.db_path) as s:
            return s.scalar(stmt) or 0
