# -*- coding: utf-8 -*-
"""用例归属迁移端点测试。

覆盖 PATCH /testcases/{id}/assignment 与 POST /testcases/batch-assign。
沿用 test_testcases_api.py 的 _setup_app 模式注入 tmp DB。
"""
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_app(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")
    import insight_aitest.modules.testcase.backend.deps as tc_deps

    tc_deps._tc_db = None
    from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase

    tc_deps._tc_db = TestCaseDatabase(str(tmp_path / "testcase.db"))
    from insight_aitest.modules.testcase.backend.routes import router as tc_router

    app = FastAPI()
    app.include_router(tc_router, prefix="/api/modules/testcase")
    return TestClient(app)


def _create_case(c, **overrides):
    payload = {
        "title": "测试用例",
        "type": "functional",
        "description": "测试描述",
        "preconditions": "无",
        "content": {"steps": [{"no": 1, "action": "操作", "data": ""}], "expected": "预期"},
        "tags": ["test"],
        "source": "manual",
    }
    payload.update(overrides)
    return c.post("/api/modules/testcase/testcases", json=payload).json()["id"]


def test_update_assignment(tmp_path, monkeypatch):
    """PATCH /testcases/{id}/assignment changes project/version."""
    c = _setup_app(tmp_path, monkeypatch)
    cid = _create_case(c)
    with patch(
        "insight_aitest.modules.testcase.backend.routes.testcases._validate_version_belongs_to_project",
        return_value=True,
    ):
        resp = c.patch(
            f"/api/modules/testcase/testcases/{cid}/assignment",
            json={"project_id": 1, "version_id": 2},
        )
    assert resp.status_code == 200
    case = resp.json()
    assert case["project_id"] == 1
    assert case["version_id"] == 2


def test_batch_assign(tmp_path, monkeypatch):
    """POST /testcases/batch-assign batch changes ownership."""
    c = _setup_app(tmp_path, monkeypatch)
    cid = _create_case(c)
    with patch(
        "insight_aitest.modules.testcase.backend.routes.testcases._validate_version_belongs_to_project",
        return_value=True,
    ):
        resp = c.post(
            "/api/modules/testcase/testcases/batch-assign",
            json={"case_ids": [cid], "project_id": 1, "version_id": 3},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 1

    # 确认用例确实被改
    case = c.get(f"/api/modules/testcase/testcases/{cid}").json()
    assert case["project_id"] == 1
    assert case["version_id"] == 3


def test_assignment_validation_fails(tmp_path, monkeypatch):
    """Version not in project returns 400."""
    c = _setup_app(tmp_path, monkeypatch)
    cid = _create_case(c)
    with patch(
        "insight_aitest.modules.testcase.backend.routes.testcases._validate_version_belongs_to_project",
        return_value=False,
    ):
        resp = c.patch(
            f"/api/modules/testcase/testcases/{cid}/assignment",
            json={"project_id": 1, "version_id": 999},
        )
    assert resp.status_code == 400


def test_assignment_404_when_missing(tmp_path, monkeypatch):
    """不存在的用例返回 404。"""
    c = _setup_app(tmp_path, monkeypatch)
    resp = c.patch(
        "/api/modules/testcase/testcases/9999/assignment",
        json={"project_id": 1, "version_id": 2},
    )
    assert resp.status_code == 404


def test_batch_assign_skips_missing(tmp_path, monkeypatch):
    """批量迁移只更新存在的用例，total 反映请求数。"""
    c = _setup_app(tmp_path, monkeypatch)
    cid = _create_case(c)
    resp = c.post(
        "/api/modules/testcase/testcases/batch-assign",
        json={"case_ids": [cid, 9999], "version_id": 3},
    )
    # 仅给 version_id（无 project_id）跳过跨 DB 校验，直接更新
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 1
    assert data["total"] == 2
