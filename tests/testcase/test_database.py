# -*- coding: utf-8 -*-
"""TestCaseDatabase CRUD + 过滤 + 状态/结果更新测试。"""

from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase
from insight_aitest.modules.testcase.backend.persistence.models import (
    CasePriority,
    CaseStatus,
    CaseType,
    TestCase,
    TestType,
)


def _db(tmp_path):
    return TestCaseDatabase(str(tmp_path / "testcase.db"))


def test_crud(tmp_path):
    db = _db(tmp_path)
    cid = db.create_case(
        TestCase(
            title="登录正向",
            type=CaseType.FUNCTIONAL,
            priority=CasePriority.P0,
            content={"steps": [{"no": 1, "action": "点击登录"}], "expected": "成功"},
            tags=["登录", "P0"],
        )
    )
    c = db.get_case(cid)
    assert c.title == "登录正向"
    assert c.type == CaseType.FUNCTIONAL
    assert c.priority == CasePriority.P0
    assert c.status == CaseStatus.DRAFT
    assert c.content["expected"] == "成功"
    assert c.tags == ["登录", "P0"]

    db.update_case(cid, title="登录正向测试")
    assert db.get_case(cid).title == "登录正向测试"

    db.update_status(cid, CaseStatus.REVIEWED)
    assert db.get_case(cid).status == CaseStatus.REVIEWED

    db.update_result(cid, "pass")
    got = db.get_case(cid)
    assert got.last_result == "pass"
    assert got.last_run_at is not None

    cases = db.list_cases()
    assert len(cases) == 1

    assert db.delete_case(cid) is True
    assert db.get_case(cid) is None


def test_list_filter(tmp_path):
    db = _db(tmp_path)
    db.create_case(TestCase(title="a", type=CaseType.FUNCTIONAL))
    db.create_case(TestCase(title="b", type=CaseType.API))
    db.create_case(TestCase(title="c", type=CaseType.FUNCTIONAL, status=CaseStatus.READY))
    assert len(db.list_cases()) == 3
    assert len(db.list_cases(type_filter=CaseType.FUNCTIONAL)) == 2
    assert len(db.list_cases(type_filter=CaseType.API)) == 1
    assert len(db.list_cases(status_filter=CaseStatus.READY)) == 1
    assert len(db.list_cases(type_filter=CaseType.FUNCTIONAL, status_filter=CaseStatus.READY)) == 1


def test_defaults(tmp_path):
    db = _db(tmp_path)
    cid = db.create_case(TestCase(title="默认值", type=CaseType.FUNCTIONAL))
    c = db.get_case(cid)
    assert c.priority == CasePriority.P2
    assert c.status == CaseStatus.DRAFT
    assert c.test_design == TestType.POSITIVE
    assert c.source == "manual"
    assert c.content == {}
    assert c.last_result is None


# ===== P0-1 ORM 迁移：旧库兼容（spec §8.3）=====

_LEGACY_DDL = """
CREATE TABLE testcases (
    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, type TEXT NOT NULL,
    description TEXT DEFAULT '', priority TEXT NOT NULL DEFAULT 'p2',
    status TEXT NOT NULL DEFAULT 'draft', test_design TEXT NOT NULL DEFAULT 'positive',
    preconditions TEXT DEFAULT '', content_json TEXT NOT NULL, tags TEXT DEFAULT '',
    source TEXT DEFAULT 'manual', last_run_at TIMESTAMP, last_result TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX idx_testcases_type ON testcases(type);
CREATE INDEX idx_testcases_status ON testcases(status);
"""


def test_legacy_db_compat(tmp_path):
    """旧（裸 sqlite3）schema 建库 + 样例数据 → 新 ORM 代码打开读写 + 索引保留。

    这是 P0-1 的数据兼容红线：存量用户 .db 必须被新代码直接读写，历史数据可见。
    """
    import json
    import sqlite3

    legacy = tmp_path / "testcase.db"
    # 1. 用旧 schema 建库 + 一条存量数据（模拟迁移前的用户库）
    with sqlite3.connect(legacy) as raw:
        raw.executescript(_LEGACY_DDL)
        raw.execute(
            "INSERT INTO testcases (title, type, priority, status, test_design, "
            "content_json, tags, source) VALUES (?,?,?,?,?,?,?,?)",
            (
                "存量用例",
                "functional",
                "p0",
                "ready",
                "positive",
                json.dumps({"expected": "成功"}, ensure_ascii=False),
                "登录,P0",
                "ai:glm",
            ),
        )
        raw.commit()

    # 2. 新 ORM 代码打开同一个文件（create_all 对存量表是 IF NOT EXISTS，不动）
    db = TestCaseDatabase(str(legacy))

    # 3. 存量数据可读、字段正确（枚举/JSON/逗号 tags 全部正确还原）
    c = db.get_case(1)
    assert c is not None
    assert c.title == "存量用例"
    assert c.type == CaseType.FUNCTIONAL
    assert c.priority == CasePriority.P0
    assert c.status == CaseStatus.READY
    assert c.test_design == TestType.POSITIVE
    assert c.content == {"expected": "成功"}
    assert c.tags == ["登录", "P0"]
    assert c.source == "ai:glm"

    # 4. 新增/更新/删除正常（写路径走 ORM）
    new_id = db.create_case(TestCase(title="新用例", type=CaseType.API))
    db.update_status(1, CaseStatus.DRAFT)
    assert db.get_case(new_id).title == "新用例"
    assert db.get_case(1).status == CaseStatus.DRAFT
    assert len(db.list_cases()) == 2

    # 5. 索引保留（schema 对齐红线）
    with sqlite3.connect(legacy) as raw:
        idx = sorted(
            r[0]
            for r in raw.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='testcases'"
            ).fetchall()
        )
    assert idx == ["idx_testcases_status", "idx_testcases_type"]


def test_new_db_has_indexes(tmp_path):
    """全新库（新 ORM create_all 建表）也必须有索引（spec §1.5 schema 对齐）。"""
    import sqlite3

    db = _db(tmp_path)
    db.create_case(TestCase(title="x", type=CaseType.FUNCTIONAL))
    with sqlite3.connect(tmp_path / "testcase.db") as raw:
        idx = sorted(
            r[0]
            for r in raw.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='testcases'"
            ).fetchall()
        )
    assert idx == ["idx_testcases_status", "idx_testcases_type"]
