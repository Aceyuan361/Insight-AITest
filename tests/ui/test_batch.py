# -*- coding: utf-8 -*-
"""UI 批量执行测试。"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_app(tmp_path, monkeypatch):
    """构建含 batch 路由的测试 app，monkeypatch 掉 D 交互和浏览器。"""
    import insight_aitest.modules.ui.backend.deps as ui_deps
    from insight_aitest.modules.ui.backend.persistence.batch_database import UIBatchRunDatabase
    from insight_aitest.modules.ui.backend.persistence.database import UIRunDatabase
    db_path = str(tmp_path / "ui.db")
    ui_deps._batch_db = UIBatchRunDatabase(db_path)
    ui_deps._run_db = UIRunDatabase(db_path)

    from insight_aitest.modules.ui.backend.routes import batch as batch_mod
    # monkeypatch D 交互
    batch_mod._fetch_case_from_d = lambda case_id: {
        "id": case_id, "title": f"case-{case_id}", "content": {"base_url": "http://test.local", "steps": [{"kind": "action", "action": "点x"}]}
    }
    # monkeypatch agent factory
    from insight_aitest.modules.ui.backend.engine import executor as exe
    from tests.ui.test_executor import FakeAgent, _patch_launch

    class FakePage:
        async def goto(self, url): pass

    class FakeCtx:
        async def __aenter__(self): return FakePage()
        async def __aexit__(self, *a): return False

    monkeypatch.setattr(exe, "_launch_browser", lambda headless=True, viewport=None, timeout=30000: FakeCtx())
    batch_mod._make_agent_factory = lambda: (lambda page: FakeAgent(["ok"]))

    app = FastAPI()
    from insight_aitest.modules.ui.backend.routes.batch import router
    app.include_router(router, prefix="/api/modules/ui")
    return TestClient(app)


def test_batch_execute_and_list(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/ui/batch/execute", json={"case_ids": [1, 2, 3]})
    assert r.status_code == 201
    batch = r.json()
    assert batch["total"] == 3
    assert batch["status"] == "running"

    # 列表
    r2 = c.get("/api/modules/ui/batch/runs")
    assert r2.status_code == 200
    assert len(r2.json()) == 1


def test_batch_empty_case_ids(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/ui/batch/execute", json={"case_ids": []})
    assert r.status_code == 422


def test_batch_get_detail(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    c.post("/api/modules/ui/batch/execute", json={"case_ids": [1]})
    batch_id = c.get("/api/modules/ui/batch/runs").json()[0]["id"]
    r = c.get(f"/api/modules/ui/batch/runs/{batch_id}")
    assert r.status_code == 200
    assert r.json()["total"] == 1


def test_batch_get_404(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.get("/api/modules/ui/batch/runs/999")
    assert r.status_code == 404


def test_batch_delete(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    c.post("/api/modules/ui/batch/execute", json={"case_ids": [1]})
    batch_id = c.get("/api/modules/ui/batch/runs").json()[0]["id"]
    assert c.delete(f"/api/modules/ui/batch/runs/{batch_id}").status_code == 200
    assert c.get(f"/api/modules/ui/batch/runs/{batch_id}").status_code == 404
