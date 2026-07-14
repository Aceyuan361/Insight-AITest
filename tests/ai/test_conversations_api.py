# -*- coding: utf-8 -*-
"""会话 API 集成测试。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_app(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")
    import insight_aitest.modules.ai.backend.deps as deps
    import insight_aitest.platform.services.kb.deps as kb_deps
    import insight_aitest.modules.ai.backend.persistence.database as _ai_db_mod
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
    cfg.config_file = str(tmp_path / "ai_config.json")
    kb_deps.set_config_file(cfg.config_file)
    deps._db = _ai_db_mod.AIDatabase(str(tmp_path / "ai.db"))
    from insight_aitest.modules.ai.backend.routes import router as ai_router
    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    return TestClient(app)


def test_create_list_get_rename_delete(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/ai/conversations")
    assert r.status_code == 200
    conv_id = r.json()["id"]
    assert r.json()["title"] == "新会话"

    r = c.get("/api/modules/ai/conversations")
    assert len(r.json()) >= 1

    r = c.get(f"/api/modules/ai/conversations/{conv_id}")
    assert r.json()["id"] == conv_id

    r = c.patch(f"/api/modules/ai/conversations/{conv_id}",
                json={"title": "新名字"})
    assert r.status_code == 200

    r = c.delete(f"/api/modules/ai/conversations/{conv_id}")
    assert r.status_code == 200


def test_create_default_rag_enabled(tmp_path, monkeypatch):
    """新建会话默认 rag_enabled=True。"""
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/ai/conversations")
    assert r.json()["rag_enabled"] is True


def test_create_rag_disabled(tmp_path, monkeypatch):
    """新建时可指定关闭 RAG。"""
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/ai/conversations", json={"rag_enabled": False})
    assert r.json()["rag_enabled"] is False


def test_toggle_rag(tmp_path, monkeypatch):
    """PATCH 切换 rag_enabled。"""
    c = _setup_app(tmp_path, monkeypatch)
    cid = c.post("/api/modules/ai/conversations").json()["id"]

    r = c.patch(f"/api/modules/ai/conversations/{cid}", json={"rag_enabled": False})
    assert r.status_code == 200
    assert r.json()["rag_enabled"] is False

    # 切回来
    r = c.patch(f"/api/modules/ai/conversations/{cid}", json={"rag_enabled": True})
    assert r.json()["rag_enabled"] is True

    # 详情接口也带上
    r = c.get(f"/api/modules/ai/conversations/{cid}")
    assert r.json()["rag_enabled"] is True


def test_patch_empty_body_400(tmp_path, monkeypatch):
    """PATCH 既不带 title 也不带 rag_enabled → 400。"""
    c = _setup_app(tmp_path, monkeypatch)
    cid = c.post("/api/modules/ai/conversations").json()["id"]
    r = c.patch(f"/api/modules/ai/conversations/{cid}", json={})
    assert r.status_code == 400
