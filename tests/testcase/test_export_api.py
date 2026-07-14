# -*- coding: utf-8 -*-
"""导出 API 测试。"""
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


def test_export_one(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    cid = c.post("/api/modules/testcase/testcases", json={
        "title": "导出测试", "type": "functional",
        "content": {"steps": [{"no": 1, "action": "x", "data": ""}], "expected": "y"},
        "preconditions": "已开页"}).json()["id"]
    r = c.get(f"/api/modules/testcase/testcases/{cid}/export")
    assert r.status_code == 200
    body = r.json()
    assert body["content"]["expected"] == "y"
    assert body["preconditions"] == "已开页"
    assert body["type"] == "functional"


def test_export_batch(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    id1 = c.post("/api/modules/testcase/testcases", json={"title": "a"}).json()["id"]
    id2 = c.post("/api/modules/testcase/testcases", json={"title": "b"}).json()["id"]
    r = c.post("/api/modules/testcase/testcases/export", json={"ids": [id1, id2, 999]})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2  # 999 不存在，跳过


def test_export_not_found(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    assert c.get("/api/modules/testcase/testcases/999/export").status_code == 404
