# -*- coding: utf-8 -*-
"""用例创建路径应正确写入 project_id/version_id（阶段 1 数据贯通）。"""
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


def test_create_case_with_project(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post(
        "/api/modules/testcase/testcases",
        json={"title": "登录测试", "type": "functional", "project_id": 5, "version_id": 7},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["project_id"] == 5
    assert data["version_id"] == 7


def test_create_case_without_project_defaults_null(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post(
        "/api/modules/testcase/testcases",
        json={"title": "无项目用例", "type": "functional"},
    )
    assert r.status_code == 201
    assert r.json()["project_id"] is None


def test_list_cases_filter_by_project(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    c.post("/api/modules/testcase/testcases", json={"title": "p1", "project_id": 1})
    c.post("/api/modules/testcase/testcases", json={"title": "p2", "project_id": 2})
    c.post("/api/modules/testcase/testcases", json={"title": "无项目"})

    # 按 project_id=1 过滤
    r = c.get("/api/modules/testcase/testcases?project_id=1")
    assert r.status_code == 200
    cases = r.json()
    assert len(cases) == 1
    assert cases[0]["title"] == "p1"
