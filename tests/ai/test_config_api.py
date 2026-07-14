# -*- coding: utf-8 -*-
"""配置 API 集成测试。"""
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
    # 先指向 tmp 配置文件，再 get_config()，避免读取真实 ~/.insight_eye/llm_config.json
    # （否则测试依赖开发者本机配置，non-hermetic）
    cfg_path = str(tmp_path / "ai_config.json")
    kb_deps.set_config_file(cfg_path)
    cfg = deps.get_config()
    cfg.db_path = str(tmp_path / "kb.db")
    cfg.docs_dir = str(tmp_path / "docs")
    cfg.config_file = cfg_path
    deps._db = _ai_db_mod.AIDatabase(str(tmp_path / "ai.db"))
    from insight_aitest.modules.ai.backend.routes import router as ai_router
    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    return TestClient(app)


def test_get_config_redacts_key(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.get("/api/modules/ai/config")
    assert r.status_code == 200
    body = r.json()
    assert "api_key" not in body
    assert "api_key_set" in body


def test_put_config_updates(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.put("/api/modules/ai/config", json={
        "llm_api_key": "sk-new", "chat_model": "qwen-plus"})
    assert r.status_code == 200
    r = c.get("/api/modules/ai/config")
    assert r.json()["chat_model"] == "qwen-plus"
    assert r.json()["api_key_set"] is True


def test_put_config_embed_dim_rejected(tmp_path, monkeypatch):
    """embed_dim 不允许热更新（维度变 = 向量表失效）。"""
    c = _setup_app(tmp_path, monkeypatch)
    r = c.put("/api/modules/ai/config", json={"embed_dim": 999})
    assert r.status_code == 400


def test_config_new_fields_roundtrip(tmp_path, monkeypatch):
    """P1-C / 向量开关：新增字段（vector_enabled/ocr_enabled/embed_base_url）可读写往返。"""
    c = _setup_app(tmp_path, monkeypatch)
    # GET 默认值
    r = c.get("/api/modules/ai/config")
    body = r.json()
    assert body["ocr_enabled"] is True  # 默认开
    assert body["vector_enabled"] is False  # 默认关
    assert body["embed_base_url"] == ""
    assert body["embed_api_key_set"] is False

    # PUT 写入
    r = c.put("/api/modules/ai/config", json={
        "vector_enabled": True,
        "ocr_enabled": False,
        "embed_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "embed_api_key": "sk-embed",
        "embed_model": "embedding-3",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["vector_enabled"] is True
    assert body["ocr_enabled"] is False
    assert body["embed_base_url"] == "https://open.bigmodel.cn/api/paas/v4"
    assert body["embed_api_key_set"] is True  # key 脱敏，只暴露是否设置
