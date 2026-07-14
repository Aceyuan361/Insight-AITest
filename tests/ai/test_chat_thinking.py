# -*- coding: utf-8 -*-
"""chat/stream thinking 事件 + thinking 落库测试。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeStreamLLM:
    def stream_chat_raw(self, messages, **kwargs):
        yield ("reasoning", "想")
        yield ("content", "答")

    def stream_chat(self, messages, **kwargs):
        for k, t in self.stream_chat_raw(messages):
            if k == "content":
                yield t


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
    kb_deps._config_file = None

    cfg = deps.get_config()
    cfg.db_path = str(tmp_path / "kb.db")
    cfg.docs_dir = str(tmp_path / "docs")
    deps._db = ai_db_mod.AIDatabase(str(tmp_path / "ai.db"))
    kb_deps._llm = _FakeStreamLLM()
    kb_deps._llm_config = cfg

    from insight_aitest.modules.ai.backend.agent.rag import RagAgent

    class FakeRetriever:
        def retrieve(self, q, document_ids=None):
            return []

    deps._agent = RagAgent(FakeRetriever(), kb_deps._llm, cfg)

    from insight_aitest.modules.ai.backend.routes import router as ai_router
    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    return TestClient(app)


def test_chat_stream_emits_thinking_and_persists(tmp_path, monkeypatch):
    """thinking_level != 'off' 时 SSE 含 thinking 事件 + message 落库含 thinking。"""
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/ai/conversations", json={})
    cid = r.json()["id"]

    r = c.post(
        "/api/modules/ai/chat/stream",
        json={"conversation_id": cid, "query": "q", "thinking_level": "medium"},
    )
    assert r.status_code == 200
    body = r.text
    assert "event: thinking" in body
    assert "event: token" in body

    # thinking 落库
    r = c.get(f"/api/modules/ai/conversations/{cid}")
    msgs = r.json()["messages"]
    assistant_msgs = [m for m in msgs if m["role"] == "assistant"]
    assert any(m.get("thinking") for m in assistant_msgs)
