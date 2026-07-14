# -*- coding: utf-8 -*-
"""runs API 集成测试（monkeypatch _make_agent_factory + D 交互，不启动浏览器）。

对标 tests/api/test_runs_api.py：不走 build_app（短路径 import 会绕过 monkeypatch），
而是用长路径 import ui router 构造最小 FastAPI app。
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeAgent:
    """契约对齐 pymidscene 0.3.0：ai_action / ai_assert / ai_query 均 async（蛇形），
    ai_assert 返回 bool（True=通过），不抛 AssertionError。ai_query 包 {data,thought}。"""

    def __init__(self, script):
        self.script = list(script)

    async def ai_action(self, p):
        return self.script.pop(0) if self.script else "ok"

    async def ai_assert(self, p):
        ok = self.script.pop(0) if self.script else True
        return bool(ok)

    async def ai_query(self, s):
        result = self.script.pop(0) if self.script else {}
        return {"data": result} if isinstance(result, dict) else result


def _client(monkeypatch, tmp_path, agent_script=None):
    """构造 TestClient，注入 FakeAgent 工厂 + 假 D 用例。
    用长路径 import（与 monkeypatch 字符串路径一致），不走 build_app。"""
    import insight_aitest.modules.ui.backend.deps as ui_deps
    from insight_aitest.modules.ui.backend.persistence.database import UIRunDatabase
    ui_deps._run_db = UIRunDatabase(str(tmp_path / "ui.db"))

    # mock D：execute 拉 D 用例 + 回填 D 结果
    fake_case = {
        "id": 1, "title": "登录测试", "type": "ui", "status": "ready",
        "content": {"base_url": "http://x", "steps": [
            {"kind": "action", "action": "点登录"}]}}
    monkeypatch.setattr(
        "insight_aitest.modules.ui.backend.routes.runs._fetch_case_from_d",
        lambda case_id: fake_case,
    )
    monkeypatch.setattr(
        "insight_aitest.modules.ui.backend.routes.runs._patch_result_to_d",
        lambda case_id, result, run_at: True,
    )
    # FakeAgent 工厂（_make_agent_factory 返回一个 factory(page) 函数）
    script = agent_script or ["ok"]
    monkeypatch.setattr(
        "insight_aitest.modules.ui.backend.routes.runs._make_agent_factory",
        lambda: (lambda page: FakeAgent(script)),
    )
    # no-op 浏览器（避免真启动 Playwright）
    monkeypatch.setattr(
        "insight_aitest.modules.ui.backend.engine.executor._launch_browser",
        lambda headless=True, viewport=None, timeout=30000: _FakeBrowserCtx(),
    )

    from insight_aitest.modules.ui.backend.routes import router as ui_router
    app = FastAPI()
    app.include_router(ui_router, prefix="/api/modules/ui")
    return TestClient(app)


class _FakeBrowserCtx:
    async def __aenter__(self):
        return _FakePage()

    async def __aexit__(self, *a):
        return False


class _FakePage:
    async def goto(self, url):
        pass


def test_execute_returns_run(tmp_path, monkeypatch):
    client = _client(monkeypatch, tmp_path, ["ok"])
    r = client.post("/api/modules/ui/runs/execute", json={"case_id": 1})
    assert r.status_code == 200
    data = r.json()
    assert data["case_id"] == 1
    assert data["status"] == "passed"
    assert data["total_steps"] == 1
    assert data["base_url_used"] == "http://x"


def test_execute_with_base_url_override(tmp_path, monkeypatch):
    client = _client(monkeypatch, tmp_path, ["ok"])
    r = client.post("/api/modules/ui/runs/execute?base_url=http://staging",
                    json={"case_id": 1})
    assert r.status_code == 200
    assert r.json()["base_url_used"] == "http://staging"


def test_execute_case_not_found(tmp_path, monkeypatch):
    client = _client(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "insight_aitest.modules.ui.backend.routes.runs._fetch_case_from_d",
        lambda case_id: None,
    )
    r = client.post("/api/modules/ui/runs/execute", json={"case_id": 999})
    assert r.status_code == 404


def test_list_runs(tmp_path, monkeypatch):
    client = _client(monkeypatch, tmp_path, ["ok"])
    client.post("/api/modules/ui/runs/execute", json={"case_id": 1})
    r = client.get("/api/modules/ui/runs?case_id=1")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert "steps" not in rows[0]  # 摘要不含 steps


def test_get_run_detail(tmp_path, monkeypatch):
    client = _client(monkeypatch, tmp_path, ["ok"])
    rid = client.post("/api/modules/ui/runs/execute", json={"case_id": 1}).json()["id"]
    r = client.get(f"/api/modules/ui/runs/{rid}")
    assert r.status_code == 200
    data = r.json()
    assert "steps" in data
    assert len(data["steps"]) == 1


def test_get_run_not_found(tmp_path, monkeypatch):
    client = _client(monkeypatch, tmp_path)
    r = client.get("/api/modules/ui/runs/99999")
    assert r.status_code == 404


def test_delete_run(tmp_path, monkeypatch):
    client = _client(monkeypatch, tmp_path, ["ok"])
    rid = client.post("/api/modules/ui/runs/execute", json={"case_id": 1}).json()["id"]
    r = client.delete(f"/api/modules/ui/runs/{rid}")
    assert r.status_code == 200
    # 删后再取 404
    assert client.get(f"/api/modules/ui/runs/{rid}").status_code == 404


def test_stats(tmp_path, monkeypatch):
    client = _client(monkeypatch, tmp_path, ["ok"])
    client.post("/api/modules/ui/runs/execute", json={"case_id": 1})
    r = client.get("/api/modules/ui/runs/stats?case_id=1")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["passed"] == 1


def test_execute_vision_config_error_400(tmp_path, monkeypatch):
    """视觉模型未配置 → _make_agent_factory 抛 VisionConfigError → HTTP 400。"""
    client = _client(monkeypatch, tmp_path, ["ok"])
    # 覆盖 _make_agent_factory 使其抛 VisionConfigError
    from insight_aitest.modules.ui.backend.engine.executor import VisionConfigError
    def boom():
        raise VisionConfigError("视觉模型未配置")
    monkeypatch.setattr(
        "insight_aitest.modules.ui.backend.routes.runs._make_agent_factory", boom
    )
    r = client.post("/api/modules/ui/runs/execute", json={"case_id": 1})
    assert r.status_code == 400
    assert "视觉模型" in r.json()["detail"]
