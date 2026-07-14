# -*- coding: utf-8 -*-
"""agent_chat 对话记忆测试：消息持久化 + 历史加载。"""

from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeLLM:
    def chat(self, messages, **kwargs):
        return f"回复：收到{len(messages)}条消息"

    def stream_chat_raw(self, messages, thinking_level="off"):
        yield ("content", f"回复：收到{len(messages)}条消息")


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
    deps._db = ai_db_mod.AIDatabase(str(tmp_path / "ai.db"))
    fake = _FakeLLM()
    kb_deps._llm = fake
    kb_deps._llm_config = cfg

    from insight_aitest.modules.ai.backend.routes import router as ai_router
    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    return TestClient(app)


def test_agent_chat_persists_messages_with_task_id(tmp_path, monkeypatch):
    """agent_chat with task_id 应持久化 user 和 assistant 消息。"""
    c = _setup_app(tmp_path, monkeypatch)
    from insight_aitest.modules.ai.backend.deps import get_db

    db = get_db()
    # Create a task first
    task_id = db.create_task(intent="测试意图", project_id=1)

    # Send chat message with task_id
    r = c.post("/api/modules/ai/tasks/chat", json={
        "message": "第一条消息",
        "task_id": task_id,
    })
    assert r.status_code == 200

    # Verify messages were persisted
    msgs = db.list_messages_by_task(task_id)
    # Should have at least the user message
    assert any(m.role.value == "user" and "第一条消息" in m.content for m in msgs)


def test_agent_chat_without_task_id_no_persist(tmp_path, monkeypatch):
    """agent_chat without task_id should not persist (backward compat)."""
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/ai/tasks/chat", json={
        "message": "hello",
    })
    assert r.status_code == 200


def test_agent_chat_loads_history(tmp_path, monkeypatch):
    """agent_chat should load previous messages as context."""
    c = _setup_app(tmp_path, monkeypatch)
    from insight_aitest.modules.ai.backend.deps import get_db
    from insight_aitest.modules.ai.backend.persistence.models import Role

    db = get_db()
    task_id = db.create_task(intent="测试", project_id=1)
    # Create conversation and link to task
    conv_id = db.create_conversation(title="test", project_id=1)
    # Manually link task to conversation
    from insight_aitest.platform.persistence import session_scope
    from insight_aitest.modules.ai.backend.persistence.models import Task
    with session_scope(db.db_path) as s:
        t = s.get(Task, task_id)
        if t:
            t.conversation_id = conv_id
    # Add a previous message
    db.add_message(conv_id, Role.USER, "之前的消息", task_id=task_id)
    db.add_message(conv_id, Role.ASSISTANT, "之前的回复", task_id=task_id)

    # Send new message - the LLM should receive history
    r = c.post("/api/modules/ai/tasks/chat", json={
        "message": "新消息",
        "task_id": task_id,
    })
    assert r.status_code == 200
    # Verify the new user message was added
    msgs = db.list_messages_by_task(task_id)
    assert len(msgs) >= 3  # 2 previous + 1 new user message
