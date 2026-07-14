# -*- coding: utf-8 -*-
"""thinking_level 字段测试（会话级，替代旧的全局 enable_thinking）。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_app(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")
    import insight_aitest.modules.ai.backend.deps as deps
    import insight_aitest.platform.services.kb.deps as kb_deps
    import insight_aitest.modules.ai.backend.persistence.database as ai_db_mod
    deps._db = None
    kb_deps._llm_config = None
    kb_deps._llm = None
    kb_deps._config_file = None
    cfg_path = str(tmp_path / "ai_config.json")
    kb_deps.set_config_file(cfg_path)
    cfg = deps.get_config()
    cfg.db_path = str(tmp_path / "kb.db")
    cfg.docs_dir = str(tmp_path / "docs")
    cfg.config_file = cfg_path
    deps._db = ai_db_mod.AIDatabase(str(tmp_path / "ai.db"))
    kb_deps._llm_config = cfg

    from insight_aitest.modules.ai.backend.routes import router as ai_router
    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    return TestClient(app)


def test_config_get_includes_thinking_level_default_off(tmp_path, monkeypatch):
    """新建会话 thinking_level 默认 'off'（替代旧的 enable_thinking=False）。"""
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/ai/conversations", json={})
    assert r.status_code == 200
    data = r.json()
    assert "thinking_level" in data
    assert data["thinking_level"] == "off"


def test_config_update_thinking_level(tmp_path, monkeypatch):
    """PATCH 会话可把 thinking_level 改为 'medium'（替代旧的 enable_thinking=True）。"""
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/ai/conversations", json={})
    cid = r.json()["id"]
    r = c.patch(f"/api/modules/ai/conversations/{cid}", json={"thinking_level": "medium"})
    assert r.status_code == 200
    assert r.json()["thinking_level"] == "medium"
