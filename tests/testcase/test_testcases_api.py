# -*- coding: utf-8 -*-
"""用例 CRUD + 状态切换 API 集成测试。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_app(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")
    import insight_aitest.modules.testcase.backend.deps as tc_deps
    tc_deps._tc_db = None
    # 注入 tmp db
    from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase
    tc_deps._tc_db = TestCaseDatabase(str(tmp_path / "testcase.db"))
    from insight_aitest.modules.testcase.backend.routes import router as tc_router
    app = FastAPI()
    app.include_router(tc_router, prefix="/api/modules/testcase")
    return TestClient(app)


def test_create_get_list_update_status_delete(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/testcase/testcases", json={
        "title": "登录测试", "type": "functional",
        "content": {"steps": [], "expected": "成功"}, "preconditions": "已开登录页"})
    assert r.status_code == 201
    cid = r.json()["id"]
    assert r.json()["status"] == "draft"

    assert c.get(f"/api/modules/testcase/testcases/{cid}").json()["title"] == "登录测试"
    assert len(c.get("/api/modules/testcase/testcases").json()) == 1

    r = c.patch(f"/api/modules/testcase/testcases/{cid}/status", json={"status": "reviewed"})
    assert r.json()["status"] == "reviewed"

    r = c.put(f"/api/modules/testcase/testcases/{cid}", json={"title": "登录正向"})
    assert r.json()["title"] == "登录正向"

    assert c.delete(f"/api/modules/testcase/testcases/{cid}").status_code == 200
    assert c.get(f"/api/modules/testcase/testcases/{cid}").status_code == 404


def test_list_filter(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    c.post("/api/modules/testcase/testcases", json={"title": "a", "type": "functional"})
    c.post("/api/modules/testcase/testcases", json={"title": "b", "type": "api"})
    assert len(c.get("/api/modules/testcase/testcases").json()) == 2
    assert len(c.get("/api/modules/testcase/testcases?type=functional").json()) == 1
    assert len(c.get("/api/modules/testcase/testcases?type=api").json()) == 1


def test_update_result_endpoint(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    cid = c.post("/api/modules/testcase/testcases", json={
        "title": "API 用例", "type": "api",
        "content": {"base_url": "http://x", "steps": []}}).json()["id"]
    r = c.patch(f"/api/modules/testcase/testcases/{cid}/result",
                json={"result": "passed", "run_at": "2026-06-25T10:00:00"})
    assert r.status_code == 200
    body = r.json()
    assert body["last_result"] == "passed"
    assert body["last_run_at"] is not None

    # 404
    assert c.patch("/api/modules/testcase/testcases/9999/result",
                   json={"result": "failed"}).status_code == 404


def test_update_content_and_tags(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    cid = c.post("/api/modules/testcase/testcases", json={"title": "x"}).json()["id"]
    r = c.put(f"/api/modules/testcase/testcases/{cid}", json={
        "content": {"steps": [{"no": 1, "action": "点"}], "expected": "ok"},
        "tags": ["登录", "正向"]})
    body = r.json()
    assert body["content"]["expected"] == "ok"
    assert body["tags"] == ["登录", "正向"]


def test_health(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    assert c.get("/api/modules/testcase/health").json()["status"] == "healthy"
