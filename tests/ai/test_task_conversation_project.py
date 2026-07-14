# -*- coding: utf-8 -*-
"""Task + Conversation 应落地 project_id（阶段 1 数据贯通）。

修复 TaskCreateRequest 声明 project_id 但 create_task 忽略的 bug。
Conversation 新增 project_id 归属。
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_ai_app(tmp_path, monkeypatch):
    """隔离的 ai 模块 app（tmp db + mock planner）。"""
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")
    import insight_aitest.modules.ai.backend.deps as ai_deps
    ai_deps._db = None
    from insight_aitest.modules.ai.backend.persistence.database import AIDatabase
    ai_deps._db = AIDatabase(str(tmp_path / "ai.db"))

    # mock planner 避免 LLM 调用
    class FakePlanner:
        def understand(self, intent, files):
            return {"summary": "test", "scope": []}
        def propose_strategies(self, context, document_ids=None):
            return []
    ai_deps._planner = FakePlanner()

    from insight_aitest.modules.ai.backend.routes import router as ai_router
    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    return TestClient(app)


def test_create_task_persists_project_id(tmp_path, monkeypatch):
    c = _setup_ai_app(tmp_path, monkeypatch)
    resp = c.post(
        "/api/modules/ai/tasks",
        json={"intent": "测试登录", "project_id": 3, "version_id": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == 3
    assert data["version_id"] == 5


def test_list_tasks_filter_by_project(tmp_path, monkeypatch):
    c = _setup_ai_app(tmp_path, monkeypatch)
    c.post("/api/modules/ai/tasks", json={"intent": "p1", "project_id": 1})
    c.post("/api/modules/ai/tasks", json={"intent": "p2", "project_id": 2})
    c.post("/api/modules/ai/tasks", json={"intent": "无项目"})

    r = c.get("/api/modules/ai/tasks?project_id=1")
    assert r.status_code == 200
    tasks = r.json()
    assert len(tasks) == 1
    assert tasks[0]["intent"] == "p1"


def test_create_conversation_with_project(tmp_path, monkeypatch):
    c = _setup_ai_app(tmp_path, monkeypatch)
    r = c.post(
        "/api/modules/ai/conversations",
        json={"title": "项目 A 对话", "project_id": 7},
    )
    assert r.status_code == 200
    assert r.json()["project_id"] == 7


def test_list_conversations_filter_by_project(tmp_path, monkeypatch):
    c = _setup_ai_app(tmp_path, monkeypatch)
    c.post("/api/modules/ai/conversations", json={"project_id": 1})
    c.post("/api/modules/ai/conversations", json={"project_id": 2})

    r = c.get("/api/modules/ai/conversations?project_id=1")
    assert r.status_code == 200
    convs = r.json()
    assert len(convs) == 1
    assert convs[0]["project_id"] == 1
