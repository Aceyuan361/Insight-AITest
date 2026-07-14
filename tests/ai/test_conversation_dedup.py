# -*- coding: utf-8 -*-
"""会话创建去重 + 流式失败兜底测试。"""

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_app(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")

    import insight_aitest.modules.ai.backend.deps as deps
    import insight_aitest.platform.services.kb.deps as kb_deps
    import insight_aitest.modules.ai.backend.persistence.database as ai_db_mod

    deps._db = None
    deps._agent = None
    deps._planner = None
    kb_deps._llm_config = None
    kb_deps._llm = None
    kb_deps._kb_db = None
    kb_deps._vector_store = None
    kb_deps._retriever = None
    kb_deps._config_file = None

    cfg = deps.get_config()
    cfg.db_path = str(tmp_path / "kb.db")
    cfg.docs_dir = str(tmp_path / "docs")
    cfg.config_file = str(tmp_path / "ai_config.json")
    kb_deps.set_config_file(cfg.config_file)
    deps._db = ai_db_mod.AIDatabase(str(tmp_path / "ai.db"))

    from insight_aitest.modules.ai.backend.routes import router as ai_router

    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    return app, TestClient(app)


def test_create_conversation_reuses_empty(tmp_path, monkeypatch):
    """连续创建会话时，应复用已有的空会话而非重复创建。"""
    _app, c = _setup_app(tmp_path, monkeypatch)
    r1 = c.post("/api/modules/ai/conversations", json={"project_id": 1})
    assert r1.status_code == 200
    conv1 = r1.json()
    r2 = c.post("/api/modules/ai/conversations", json={"project_id": 1})
    assert r2.status_code == 200
    conv2 = r2.json()
    # 应复用同一个空会话
    assert conv1["id"] == conv2["id"]


def test_create_conversation_no_reuse_after_message(tmp_path, monkeypatch):
    """有消息的会话不复用，应创建新的。"""
    _app, c = _setup_app(tmp_path, monkeypatch)
    r1 = c.post("/api/modules/ai/conversations", json={"project_id": 1})
    conv1 = r1.json()
    # 给 conv1 加一条消息
    from insight_aitest.modules.ai.backend.deps import get_db
    from insight_aitest.modules.ai.backend.persistence.models import Role

    get_db().add_message(conv1["id"], Role.USER, "hello")
    # 再创建应得到新会话
    r2 = c.post("/api/modules/ai/conversations", json={"project_id": 1})
    conv2 = r2.json()
    assert conv1["id"] != conv2["id"]


def test_create_conversation_different_projects_not_reused(tmp_path, monkeypatch):
    """不同项目的空会话不应复用。"""
    _app, c = _setup_app(tmp_path, monkeypatch)
    r1 = c.post("/api/modules/ai/conversations", json={"project_id": 1})
    conv1 = r1.json()
    r2 = c.post("/api/modules/ai/conversations", json={"project_id": 2})
    conv2 = r2.json()
    assert conv1["id"] != conv2["id"]


def test_chat_stream_error_writes_placeholder_assistant(tmp_path, monkeypatch):
    """流式失败时应写入错误占位 assistant 消息，避免 DB 残留孤立 user 消息。"""
    app, c = _setup_app(tmp_path, monkeypatch)
    conv = c.post("/api/modules/ai/conversations", json={"project_id": 1}).json()
    conv_id = conv["id"]
    from insight_aitest.modules.ai.backend.agent.rag import StreamEvent
    from insight_aitest.modules.ai.backend.deps import get_agent

    async def fake_stream(*a, **kw):
        yield StreamEvent(type="token", data="部分")
        yield StreamEvent(type="error", data="上游 LLM 超时")

    fake_agent = MagicMock()
    fake_agent.stream_answer_async = fake_stream
    app.dependency_overrides[get_agent] = lambda: fake_agent

    with c.stream(
        "POST",
        "/api/modules/ai/chat/stream",
        json={"conversation_id": conv_id, "query": "你好"},
    ) as r:
        assert r.status_code == 200
        text = b"".join(r.iter_bytes()).decode()

    assert "event: error" in text
    # 历史应包含 user 消息 + 占位 assistant 消息（无孤立 user）
    detail = c.get(f"/api/modules/ai/conversations/{conv_id}").json()
    roles = [m["role"] for m in detail["messages"]]
    assert "user" in roles
    assert "assistant" in roles
    asst = [m for m in detail["messages"] if m["role"] == "assistant"]
    assert asst, "失败时应写入占位 assistant 消息"
    assert "失败" in asst[-1]["content"]


def test_chat_stream_exception_writes_placeholder_assistant(tmp_path, monkeypatch):
    """流式抛异常时应写入错误占位 assistant 消息。"""
    app, c = _setup_app(tmp_path, monkeypatch)
    conv = c.post("/api/modules/ai/conversations", json={"project_id": 1}).json()
    conv_id = conv["id"]
    from insight_aitest.modules.ai.backend.deps import get_agent

    async def fake_stream(*a, **kw):
        raise RuntimeError("连接断开")
        yield  # noqa: unreachable - 使函数成为 async generator

    fake_agent = MagicMock()
    fake_agent.stream_answer_async = fake_stream
    app.dependency_overrides[get_agent] = lambda: fake_agent

    with c.stream(
        "POST",
        "/api/modules/ai/chat/stream",
        json={"conversation_id": conv_id, "query": "你好"},
    ) as r:
        assert r.status_code == 200
        text = b"".join(r.iter_bytes()).decode()

    assert "event: error" in text
    detail = c.get(f"/api/modules/ai/conversations/{conv_id}").json()
    roles = [m["role"] for m in detail["messages"]]
    assert "assistant" in roles, "异常时应写入占位 assistant 消息"
    asst = [m for m in detail["messages"] if m["role"] == "assistant"]
    assert "失败" in asst[-1]["content"]
