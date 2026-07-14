# -*- coding: utf-8 -*-
"""测试用例数据库（TestCaseDatabase，spec D §3 + P0-1 ORM 迁移）。

独立 testcase.db（~/.insight_eye/testcase.db）。
P0-1：从裸 sqlite3 + threading.local 迁移到平台 session_scope + ORM。
对外方法签名/返回类型完全不变（业务层 routes/generator/tests 零改动）。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select, update

from insight_aitest.platform.persistence import Base, ensure_schema, get_engine, session_scope
from insight_aitest.modules.testcase.backend.persistence.models import (
    CaseStatus,
    CaseType,
    TestCase,
)


def _ensure_project_columns(db_path: str) -> None:
    """增量迁移：给旧 testcases 表补 project_id/version_id 列（幂等）。"""
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(testcases)")}
        if "project_id" not in cols:
            conn.execute("ALTER TABLE testcases ADD COLUMN project_id INTEGER")
        if "version_id" not in cols:
            conn.execute("ALTER TABLE testcases ADD COLUMN version_id INTEGER")
        conn.commit()


def _ensure_task_columns(db_path: str) -> None:
    """增量迁移：给旧 testcases 表补 task_id/batch_id 列（幂等）。

    task_id: 反向追溯到生成它的 Agent task（逻辑外键，nullable）。
    batch_id: 批次标识，同一次批量生成共享（如 "batch-42-1719..."）。
    """
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(testcases)")}
        if "task_id" not in cols:
            conn.execute("ALTER TABLE testcases ADD COLUMN task_id INTEGER")
        if "batch_id" not in cols:
            conn.execute("ALTER TABLE testcases ADD COLUMN batch_id TEXT")
        conn.commit()


class TestCaseDatabase:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        # CREATE TABLE IF NOT EXISTS 语义：存量表已存在则不重建（旧数据兼容）。
        # tables= 只建本模块的表，避免 Base.metadata 里其他模块的表被误建到本库。
        Base.metadata.create_all(get_engine(db_path), tables=[TestCase.__table__])
        # 增量迁移：旧 testcases 表补 project_id/version_id 列（幂等）
        ensure_schema(db_path, [_ensure_project_columns, _ensure_task_columns])

    def create_case(self, case: TestCase) -> int:
        with session_scope(self.db_path) as s:
            s.add(case)
            s.flush()  # 拿 id（不 commit，由 session_scope 统一 commit）
            return case.id

    def get_case(self, case_id: int) -> TestCase | None:
        with session_scope(self.db_path) as s:
            return s.get(TestCase, case_id)

    def list_cases(
        self,
        type_filter: CaseType | None = None,
        status_filter: CaseStatus | None = None,
        project_id: int | None = None,
        version_id: int | None = None,
        source: str | None = None,
        task_id: int | None = None,
    ) -> list[TestCase]:
        """列出用例，可按 type/status/project/version/source(前缀)/task_id 过滤。

        source 用前缀匹配（``source like 'ai:batch%'``），便于按
        "manual" / "ai" / "ai:batch:42" 等来源族聚合筛选。
        task_id 精确匹配，回溯某次 Agent task 生成的全部用例。
        """
        stmt = select(TestCase)
        if type_filter is not None:
            stmt = stmt.where(TestCase.type == type_filter)
        if status_filter is not None:
            stmt = stmt.where(TestCase.status == status_filter)
        if project_id is not None:
            stmt = stmt.where(TestCase.project_id == project_id)
        if version_id is not None:
            stmt = stmt.where(TestCase.version_id == version_id)
        if source:
            stmt = stmt.where(TestCase.source.like(f"{source}%"))
        if task_id is not None:
            stmt = stmt.where(TestCase.task_id == task_id)
        stmt = stmt.order_by(TestCase.updated_at.desc())
        with session_scope(self.db_path) as s:
            return list(s.scalars(stmt))

    def list_cases_by_batch(self, batch_id: str) -> list[TestCase]:
        """按 batch_id 列出同批次用例（按 id 升序，与生成顺序一致）。"""
        stmt = select(TestCase).where(TestCase.batch_id == batch_id).order_by(TestCase.id)
        with session_scope(self.db_path) as s:
            return list(s.scalars(stmt))

    def update_cases_batch(self, case_ids: list[int], **fields) -> int:
        """批量更新指定 id 的用例，返回受影响行数。

        可更新字段：status/version_id/priority/test_design/task_id/batch_id。
        仅接受白名单内的字段，其余忽略，避免误改 title/content 等。
        status/priority/test_design 传枚举对象或对应 value 均可。
        """
        if not case_ids:
            return 0
        allowed = (
            "status",
            "version_id",
            "priority",
            "test_design",
            "task_id",
            "batch_id",
        )
        clean: dict[str, object] = {}
        for k in allowed:
            if k in fields and fields[k] is not None:
                clean[k] = fields[k]
        if not clean:
            return 0
        clean["updated_at"] = datetime.now()
        with session_scope(self.db_path) as s:
            result = s.execute(update(TestCase).where(TestCase.id.in_(case_ids)).values(**clean))
            return result.rowcount or 0

    def update_cases_in_batch(self, case_ids: list[int], batch_id: str, **fields) -> int:
        """批量更新指定 id 且属于该 batch_id 的用例，返回受影响行数。

        与 update_cases_batch 的区别：额外限定 batch_id，defense-in-depth——
        即使传入的 case_ids 跨批次，也只更新属于本批次的，避免误改批次外用例。
        可更新字段白名单同 update_cases_batch。
        """
        if not case_ids or not batch_id:
            return 0
        allowed = (
            "status",
            "version_id",
            "priority",
            "test_design",
            "task_id",
            "batch_id",
        )
        clean: dict[str, object] = {}
        for k in allowed:
            if k in fields and fields[k] is not None:
                clean[k] = fields[k]
        if not clean:
            return 0
        clean["updated_at"] = datetime.now()
        with session_scope(self.db_path) as s:
            result = s.execute(
                update(TestCase)
                .where(TestCase.id.in_(case_ids))
                .where(TestCase.batch_id == batch_id)
                .values(**clean)
            )
            return result.rowcount or 0

    def delete_cases_batch(self, case_ids: list[int]) -> int:
        """批量删除指定 id 的用例，返回删除行数。"""
        if not case_ids:
            return 0
        with session_scope(self.db_path) as s:
            result = s.execute(delete(TestCase).where(TestCase.id.in_(case_ids)))
            return result.rowcount or 0

    def list_case_ids_by_batch_excluding(self, batch_id: str, exclude_ids: list[int]) -> list[int]:
        """列出 batch 内、但不在 exclude_ids 中的用例 id（用于 batch-sync 删除未选）。"""
        stmt = select(TestCase.id).where(TestCase.batch_id == batch_id)
        if exclude_ids:
            stmt = stmt.where(~TestCase.id.in_(exclude_ids))
        with session_scope(self.db_path) as s:
            return list(s.scalars(stmt))

    def count_by_project(self, project_id: int | None) -> int:
        """统计某项目下的用例数（project_id=None 统计未分类）。"""
        from sqlalchemy import func

        stmt = select(func.count(TestCase.id))
        if project_id is not None:
            stmt = stmt.where(TestCase.project_id == project_id)
        else:
            stmt = stmt.where(TestCase.project_id.is_(None))
        with session_scope(self.db_path) as s:
            return s.scalar(stmt) or 0

    def update_case(self, case_id: int, **fields) -> None:
        """可更新字段：title/description/priority/test_design/preconditions/content/tags/project_id/version_id/task_id/batch_id/source。

        source 纳入白名单以支撑质量自检（标记 ai:validated/ai:fixed/ai:invalid）。
        """
        allowed = (
            "title",
            "description",
            "priority",
            "test_design",
            "preconditions",
            "content",
            "tags",
            "project_id",
            "version_id",
            "task_id",
            "batch_id",
            "source",
        )
        with session_scope(self.db_path) as s:
            case = s.get(TestCase, case_id)
            if case is None:
                return
            for k in allowed:
                if k not in fields or fields[k] is None:
                    continue
                setattr(case, k, fields[k])
            case.updated_at = datetime.now()

    def update_status(self, case_id: int, status: CaseStatus) -> None:
        with session_scope(self.db_path) as s:
            case = s.get(TestCase, case_id)
            if case is None:
                return
            case.status = status
            case.updated_at = datetime.now()

    def update_result(self, case_id: int, result: str, run_at: datetime | None = None) -> None:
        """E/F 执行后回填结果（闭环支撑）。"""
        ts = run_at or datetime.now()
        with session_scope(self.db_path) as s:
            case = s.get(TestCase, case_id)
            if case is None:
                return
            case.last_result = result
            case.last_run_at = ts
            case.updated_at = datetime.now()

    def delete_case(self, case_id: int) -> bool:
        with session_scope(self.db_path) as s:
            case = s.get(TestCase, case_id)
            if case is None:
                return False
            s.delete(case)
            return True
