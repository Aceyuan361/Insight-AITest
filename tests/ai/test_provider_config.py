# -*- coding: utf-8 -*-
"""Provider 多模型管理（Cursor 风格）测试。

覆盖：
- Provider CRUD（新增/更新/删除）
- 切换 active provider 时投影到扁平字段
- 第一个 provider 自动激活
- active provider 不允许删除
- 向后兼容：无 providers 时扁平字段仍可用
- load_config 从文件加载 providers + 投影
- GET /config/presets 返回预设清单
"""
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
    deps._planner = None
    kb_deps._llm_config = None
    kb_deps._kb_db = None
    kb_deps._llm = None
    kb_deps._vector_store = None
    kb_deps._retriever = None
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


# ===== T1: GET /config 默认含 providers 空列表 + active_provider_id 空串 =====
def test_get_config_has_provider_fields(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.get("/api/modules/ai/config")
    assert r.status_code == 200
    body = r.json()
    assert "providers" in body
    assert body["providers"] == []
    assert body["active_provider_id"] == ""


# ===== T2: 新建 Provider（第一个自动激活）=====
def test_create_first_provider_auto_active(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.put("/api/modules/ai/config/providers/new", json={
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-deepseek",
        "chat_model": "deepseek-chat",
    })
    assert r.status_code == 200
    body = r.json()
    assert len(body["providers"]) == 1
    p = body["providers"][0]
    assert p["name"] == "DeepSeek"
    assert p["chat_model"] == "deepseek-chat"
    assert p["api_key_set"] is True  # 脱敏，只暴露是否设置
    assert "api_key" not in p  # 明文 key 不外泄
    # 第一个 provider 自动激活
    assert body["active_provider_id"] == p["id"]
    # 激活后扁平字段被投影
    assert body["llm_base_url"] == "https://api.deepseek.com/v1"
    assert body["chat_model"] == "deepseek-chat"
    assert body["api_key_set"] is True


# ===== T3: 新建第二个 Provider 不自动激活（保持第一个 active）=====
def test_create_second_provider_no_auto_active(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    # 第一个
    c.put("/api/modules/ai/config/providers/new", json={
        "name": "DeepSeek", "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-1", "chat_model": "deepseek-chat",
    })
    # 第二个
    r = c.put("/api/modules/ai/config/providers/new", json={
        "name": "OpenAI", "base_url": "https://api.openai.com/v1",
        "api_key": "sk-2", "chat_model": "gpt-4o-mini",
    })
    body = r.json()
    assert len(body["providers"]) == 2
    # active 仍是第一个
    first_id = body["providers"][0]["id"]
    assert body["active_provider_id"] == first_id
    # 扁平字段仍是第一个 provider 的值
    assert body["chat_model"] == "deepseek-chat"


# ===== T4: 切换 active provider，扁平字段跟着变 =====
def test_switch_active_provider(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    c.put("/api/modules/ai/config/providers/new", json={
        "name": "DeepSeek", "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-1", "chat_model": "deepseek-chat",
    })
    r2 = c.put("/api/modules/ai/config/providers/new", json={
        "name": "OpenAI", "base_url": "https://api.openai.com/v1",
        "api_key": "sk-2", "chat_model": "gpt-4o-mini",
    })
    second_id = r2.json()["providers"][1]["id"]

    # 切换到第二个
    r = c.put(f"/api/modules/ai/config/activate/{second_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["active_provider_id"] == second_id
    assert body["chat_model"] == "gpt-4o-mini"
    assert body["llm_base_url"] == "https://api.openai.com/v1"


# ===== T5: active provider 不允许删除 =====
def test_cannot_delete_active_provider(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r1 = c.put("/api/modules/ai/config/providers/new", json={
        "name": "DeepSeek", "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-1", "chat_model": "deepseek-chat",
    })
    active_id = r1.json()["active_provider_id"]

    r = c.delete(f"/api/modules/ai/config/providers/{active_id}")
    assert r.status_code == 400


# ===== T6: 删除非 active provider =====
def test_delete_inactive_provider(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    c.put("/api/modules/ai/config/providers/new", json={
        "name": "DeepSeek", "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-1", "chat_model": "deepseek-chat",
    })
    r2 = c.put("/api/modules/ai/config/providers/new", json={
        "name": "OpenAI", "base_url": "https://api.openai.com/v1",
        "api_key": "sk-2", "chat_model": "gpt-4o-mini",
    })
    inactive_id = r2.json()["providers"][1]["id"]

    r = c.delete(f"/api/modules/ai/config/providers/{inactive_id}")
    assert r.status_code == 200
    assert len(r.json()["providers"]) == 1


# ===== T7: 更新 Provider（留空 api_key = 不改）=====
def test_update_provider_keep_key(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r1 = c.put("/api/modules/ai/config/providers/new", json={
        "name": "DeepSeek", "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-1", "chat_model": "deepseek-chat",
    })
    pid = r1.json()["providers"][0]["id"]

    # 更新 chat_model，不传 api_key
    r = c.put(f"/api/modules/ai/config/providers/{pid}", json={
        "name": "DeepSeek", "base_url": "https://api.deepseek.com/v1",
        "chat_model": "deepseek-reasoner",
    })
    assert r.status_code == 200
    p = r.json()["providers"][0]
    assert p["chat_model"] == "deepseek-reasoner"
    assert p["api_key_set"] is True  # key 仍在


# ===== T8: 向后兼容 —— 无 providers 时扁平字段 PUT 仍可用 =====
def test_flat_config_still_works_without_providers(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.put("/api/modules/ai/config", json={
        "chat_model": "qwen-plus",
        "llm_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["chat_model"] == "qwen-plus"
    assert body["providers"] == []  # 仍无 providers


# ===== T9: GET /config/presets 返回预设清单 =====
def test_get_presets(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.get("/api/modules/ai/config/presets")
    assert r.status_code == 200
    presets = r.json()["presets"]
    assert len(presets) >= 4
    names = [p["name"] for p in presets]
    assert "DeepSeek" in names
    assert "OpenAI" in names
    # 每个 preset 有 models 列表
    for p in presets:
        assert "base_url" in p
        assert "models" in p
        assert len(p["models"]) > 0


# ===== T10: load_config 从文件加载 providers + 投影（单元级）=====
def test_load_config_projects_active_provider(tmp_path, monkeypatch):
    # 清掉所有 LLM 环境变量（env 优先级最高，会覆盖 provider 投影）
    for k in [
        "INSIGHT_EYE_AI_LLM_API_KEY", "INSIGHT_EYE_AI_CHAT_MODEL",
        "INSIGHT_EYE_AI_LLM_BASE_URL",
    ]:
        monkeypatch.delenv(k, raising=False)
    import json
    cfg_path = tmp_path / "llm_config.json"
    cfg_data = {
        "providers": [
            {"id": "p1", "name": "A", "base_url": "http://a/v1", "api_key": "sk-a", "chat_model": "model-a"},
            {"id": "p2", "name": "B", "base_url": "http://b/v1", "api_key": "sk-b", "chat_model": "model-b"},
        ],
        "active_provider_id": "p2",
    }
    cfg_path.write_text(json.dumps(cfg_data), encoding="utf-8")

    from insight_aitest.platform.services.llm.config import load_config
    cfg = load_config(str(cfg_path))
    # 投影后扁平字段 = p2
    assert cfg.llm_base_url == "http://b/v1"
    assert cfg.llm_api_key == "sk-b"
    assert cfg.chat_model == "model-b"
    assert cfg.active_provider_id == "p2"
    assert len(cfg.providers) == 2


# ===== T11: 向后兼容 —— 旧配置文件（无 providers 节）仍能加载 =====
def test_load_config_legacy_file_without_providers(tmp_path, monkeypatch):
    for k in [
        "INSIGHT_EYE_AI_LLM_API_KEY", "INSIGHT_EYE_AI_CHAT_MODEL",
        "INSIGHT_EYE_AI_LLM_BASE_URL",
    ]:
        monkeypatch.delenv(k, raising=False)
    import json
    cfg_path = tmp_path / "llm_config.json"
    # 旧格式：只有扁平字段，无 providers
    cfg_data = {
        "llm_base_url": "https://api.openai.com/v1",
        "chat_model": "gpt-4o-mini",
        "llm_api_key": "sk-legacy",
    }
    cfg_path.write_text(json.dumps(cfg_data), encoding="utf-8")

    from insight_aitest.platform.services.llm.config import load_config
    cfg = load_config(str(cfg_path))
    assert cfg.llm_base_url == "https://api.openai.com/v1"
    assert cfg.chat_model == "gpt-4o-mini"
    assert cfg.llm_api_key == "sk-legacy"
    assert cfg.providers == []
    assert cfg.active_provider_id == ""


# ===== T12: 环境变量优先级高于 provider 投影 =====
def test_env_overrides_provider_projection(tmp_path, monkeypatch):
    """env 用于无头部署强制锁定，优先级最高。"""
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-env-override")
    monkeypatch.setenv("INSIGHT_EYE_AI_CHAT_MODEL", "env-model")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")
    import json
    cfg_path = tmp_path / "llm_config.json"
    cfg_data = {
        "providers": [
            {"id": "p1", "name": "A", "base_url": "http://a/v1", "api_key": "sk-a", "chat_model": "model-a"},
        ],
        "active_provider_id": "p1",
    }
    cfg_path.write_text(json.dumps(cfg_data), encoding="utf-8")

    from insight_aitest.platform.services.llm.config import load_config
    cfg = load_config(str(cfg_path))
    # env 覆盖 provider 投影
    assert cfg.llm_api_key == "sk-env-override"
    assert cfg.chat_model == "env-model"


# ===== T13: POST /config/test 走临时 client（不写配置）=====
def test_config_test_endpoint_no_side_effect(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    # 不连真实端点，必然失败，但不应抛 500（应返回 {ok: false, message: ...}）
    r = c.post("/api/modules/ai/config/test", json={
        "base_url": "http://127.0.0.1:1/v1",  # 必然连不上
        "api_key": "sk-test",
        "model": "test-model",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert "message" in body
    # 配置不应改变
    r2 = c.get("/api/modules/ai/config")
    assert r2.json()["providers"] == []
