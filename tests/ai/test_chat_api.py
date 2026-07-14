# -*- coding: utf-8 -*-
"""对话 API 集成测试（非流式 + SSE 流式）。mock agent。"""
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_app(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")
    import insight_aitest.modules.ai.backend.deps as deps
    import insight_aitest.platform.services.kb.deps as kb_deps
    import insight_aitest.modules.ai.backend.persistence.database as _ai_db_mod
    # 重置 ai + 平台单例
    deps._db = None
    deps._agent = None
    kb_deps._llm_config = None
    kb_deps._kb_db = None
    kb_deps._llm = None
    kb_deps._vector_store = None
    kb_deps._retriever = None
    kb_deps._config_file = None
    cfg = deps.get_config()
    cfg.db_path = str(tmp_path / "kb.db")
    cfg.docs_dir = str(tmp_path / "docs")
    # 注入独立的 ai.db 给会话库
    deps._db = _ai_db_mod.AIDatabase(str(tmp_path / "ai.db"))
    from insight_aitest.modules.ai.backend.routes import router as ai_router
    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    return app, TestClient(app)


def test_chat_non_stream(tmp_path, monkeypatch):
    app, c = _setup_app(tmp_path, monkeypatch)
    conv = c.post("/api/modules/ai/conversations").json()
    conv_id = conv["id"]
    from insight_aitest.modules.ai.backend.agent.rag import RagResult
    from insight_aitest.modules.ai.backend.deps import get_agent
    fake_agent = MagicMock()
    fake_agent.answer.return_value = RagResult(answer="回答", citations=[])
    app.dependency_overrides[get_agent] = lambda: fake_agent
    r = c.post("/api/modules/ai/chat", json={
        "conversation_id": conv_id, "query": "你好", "history_turns": 6})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "回答"


def test_chat_stream_sse(tmp_path, monkeypatch):
    app, c = _setup_app(tmp_path, monkeypatch)
    conv = c.post("/api/modules/ai/conversations").json()
    conv_id = conv["id"]
    from insight_aitest.modules.ai.backend.agent.rag import StreamEvent
    from insight_aitest.modules.ai.backend.deps import get_agent

    async def fake_stream(*a, **kw):
        yield StreamEvent(type="citations", data=[])
        yield StreamEvent(type="token", data="你")
        yield StreamEvent(type="token", data="好")
        yield StreamEvent(type="done", data=None)

    fake_agent = MagicMock()
    fake_agent.stream_answer_async = fake_stream
    app.dependency_overrides[get_agent] = lambda: fake_agent
    with c.stream("POST", "/api/modules/ai/chat/stream",
                  json={"conversation_id": conv_id, "query": "你好"}) as r:
        assert r.status_code == 200
        text = b"".join(r.iter_bytes()).decode()
    assert "event: citations" in text
    assert "event: token" in text
    assert "event: done" in text


def test_chat_stream_passes_use_rag_from_conversation(tmp_path, monkeypatch):
    """会话 rag_enabled=False 时，chat/stream 应传 use_rag=False 给 agent。"""
    app, c = _setup_app(tmp_path, monkeypatch)
    conv = c.post("/api/modules/ai/conversations", json={"rag_enabled": False}).json()
    conv_id = conv["id"]
    from insight_aitest.modules.ai.backend.agent.rag import StreamEvent
    from insight_aitest.modules.ai.backend.deps import get_agent

    captured = {}

    async def fake_stream(query, history, document_ids, use_rag=True, thinking_level="off", project_id=None):
        captured["use_rag"] = use_rag
        yield StreamEvent(type="citations", data=[])
        yield StreamEvent(type="token", data="纯聊")
        yield StreamEvent(type="done", data=None)

    fake_agent = MagicMock()
    fake_agent.stream_answer_async = fake_stream
    app.dependency_overrides[get_agent] = lambda: fake_agent
    with c.stream("POST", "/api/modules/ai/chat/stream",
                  json={"conversation_id": conv_id, "query": "你好"}) as r:
        assert r.status_code == 200
    assert captured["use_rag"] is False


def test_chat_stream_citations_format(tmp_path, monkeypatch):
    """SSE citations 事件 data 应为 {"citations":[...]}（spec §6.4 格式）。"""
    app, c = _setup_app(tmp_path, monkeypatch)
    conv = c.post("/api/modules/ai/conversations").json()
    conv_id = conv["id"]
    from insight_aitest.modules.ai.backend.agent.rag import StreamEvent
    from insight_aitest.modules.ai.backend.deps import get_agent
    from insight_aitest.modules.ai.backend.persistence.models import Citation

    citation = Citation(document_id=1, document_name="a.pdf", chunk_index=0,
                        snippet="片段内容", score=0.9)

    async def fake_stream(*a, **kw):
        yield StreamEvent(type="citations", data=[citation])
        yield StreamEvent(type="done", data=None)

    fake_agent = MagicMock()
    fake_agent.stream_answer_async = fake_stream
    app.dependency_overrides[get_agent] = lambda: fake_agent
    with c.stream("POST", "/api/modules/ai/chat/stream",
                  json={"conversation_id": conv_id, "query": "问"}) as r:
        text = b"".join(r.iter_bytes()).decode()
    # data 行应是 {"citations":[{...}]} 而非裸数组
    import json as _json
    for line in text.splitlines():
        if line.startswith("data:") and "a.pdf" in line:
            payload = _json.loads(line[len("data:"):].strip())
            assert "citations" in payload
            assert payload["citations"][0]["document_name"] == "a.pdf"
            break
    else:
        assert False, "未找到带 a.pdf 的 citations data 行"


def test_chat_unknown_conversation_404(tmp_path, monkeypatch):
    app, c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/ai/chat", json={
        "conversation_id": 99999, "query": "x"})
    assert r.status_code == 404


def test_chat_non_stream_rag_disabled(tmp_path, monkeypatch):
    """非流式 /chat：会话 rag_enabled=False 时传 use_rag=False。"""
    app, c = _setup_app(tmp_path, monkeypatch)
    conv = c.post("/api/modules/ai/conversations", json={"rag_enabled": False}).json()
    conv_id = conv["id"]
    from insight_aitest.modules.ai.backend.agent.rag import RagResult
    from insight_aitest.modules.ai.backend.deps import get_agent
    fake_agent = MagicMock()
    fake_agent.answer.return_value = RagResult(answer="纯聊", citations=[])
    app.dependency_overrides[get_agent] = lambda: fake_agent
    r = c.post("/api/modules/ai/chat", json={
        "conversation_id": conv_id, "query": "你好"})
    assert r.status_code == 200
    # answer 第 4 个位置参数 use_rag 应为 False
    assert fake_agent.answer.call_args.kwargs.get("use_rag") is False
