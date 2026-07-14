# -*- coding: utf-8 -*-
"""list_cases 过滤扩展 + batch 查询测试。"""
from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase
from insight_aitest.modules.testcase.backend.persistence.models import (
    CasePriority,
    CaseStatus,
    CaseType,
    TestCase,
)


def _make_case(title, source="manual", task_id=None, batch_id=None):
    return TestCase(
        title=title,
        type=CaseType.FUNCTIONAL,
        description="",
        priority=CasePriority.P1,
        status=CaseStatus.DRAFT,
        test_design="positive",
        preconditions="",
        content={"steps": []},
        tags=[],
        source=source,
        task_id=task_id,
        batch_id=batch_id,
    )


def test_list_cases_filter_by_source(tmp_path):
    db = TestCaseDatabase(str(tmp_path / "tc.db"))
    db.create_case(_make_case("c1", source="manual"))
    db.create_case(_make_case("c2", source="ai:batch:42"))
    db.create_case(_make_case("c3", source="ai:batch:43"))
    result = db.list_cases(source="ai:batch")
    assert len(result) == 2
    result = db.list_cases(source="manual")
    assert len(result) == 1


def test_list_cases_filter_by_task_id(tmp_path):
    db = TestCaseDatabase(str(tmp_path / "tc.db"))
    db.create_case(_make_case("c1", task_id=42))
    db.create_case(_make_case("c2", task_id=42))
    db.create_case(_make_case("c3", task_id=43))
    result = db.list_cases(task_id=42)
    assert len(result) == 2


def test_list_cases_by_batch(tmp_path):
    db = TestCaseDatabase(str(tmp_path / "tc.db"))
    db.create_case(_make_case("c1", batch_id="batch-42-a"))
    db.create_case(_make_case("c2", batch_id="batch-42-a"))
    db.create_case(_make_case("c3", batch_id="batch-99-b"))
    result = db.list_cases_by_batch("batch-42-a")
    assert len(result) == 2
    assert all(c.batch_id == "batch-42-a" for c in result)
