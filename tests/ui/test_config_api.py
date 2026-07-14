# -*- coding: utf-8 -*-
"""UI 视觉模型配置 API 测试。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_app():
    app = FastAPI()
    from insight_aitest.modules.ui.backend.routes.config import router
    app.include_router(router, prefix="/api/modules/ui")
    return TestClient(app)


def _patch_config(monkeypatch, ui_vision_config=None, llm_base_url="https://global.local/v1",
                  llm_api_key="global-key", vision_model="", chat_model="global-chat"):
    """Mock get_llm_config + save_config + reset_llm_singletons。"""
    from dataclasses import dataclass, field

    @dataclass
    class FakeCfg:
        ui_vision_config: dict = field(default_factory=dict)
        llm_base_url: str = "https://global.local/v1"
        llm_api_key: str = "global-key"
        vision_model: str = ""
        chat_model: str = "global-chat"

    cfg = FakeCfg(ui_vision_config=ui_vision_config or {},
                  llm_base_url=llm_base_url, llm_api_key=llm_api_key,
                  vision_model=vision_model, chat_model=chat_model)

    import insight_aitest.modules.ui.backend.routes.config as config_mod
    config_mod._get_cfg = lambda: cfg

    # Mock save_config / reset
    import insight_aitest.platform.services.llm.config as llm_config
    monkeypatch.setattr(llm_config, "save_config", lambda c: None)

    import insight_aitest.platform.services.kb.deps as kb_deps
    monkeypatch.setattr(kb_deps, "reset_llm_singletons", lambda: None)

    return cfg


def test_get_config_empty(monkeypatch):
    """无 UI 专用配置 → 全部回退全局值。"""
    _patch_config(monkeypatch, ui_vision_config={})
    c = _setup_app()
    r = c.get("/api/modules/ui/config")
    assert r.status_code == 200
    data = r.json()
    assert data["base_url"] == ""
    assert data["api_key_set"] is False
    assert data["model"] == ""
    assert data["global_base_url"] == "https://global.local/v1"
    assert data["global_model"] == "global-chat"


def test_get_config_with_ui_config(monkeypatch):
    """有 UI 专用配置 → 返回 UI 值。"""
    _patch_config(monkeypatch, ui_vision_config={
        "base_url": "https://ui.local/v1", "api_key": "ui-key", "model": "gpt-4o",
    })
    c = _setup_app()
    data = c.get("/api/modules/ui/config").json()
    assert data["base_url"] == "https://ui.local/v1"
    assert data["api_key_set"] is True
    assert data["model"] == "gpt-4o"


def test_put_config(monkeypatch):
    """PUT 更新写入 + reset。"""
    cfg = _patch_config(monkeypatch, ui_vision_config={})
    c = _setup_app()
    r = c.put("/api/modules/ui/config", json={
        "base_url": "https://new.local/v1", "api_key": "new-key", "model": "claude-3.5",
    })
    assert r.status_code == 200
    assert cfg.ui_vision_config["base_url"] == "https://new.local/v1"
    assert cfg.ui_vision_config["api_key"] == "new-key"
    assert cfg.ui_vision_config["model"] == "claude-3.5"


def test_put_config_preserve_api_key(monkeypatch):
    """PUT 不传 api_key → 保留已有 key。"""
    cfg = _patch_config(monkeypatch, ui_vision_config={
        "base_url": "", "api_key": "old-key", "model": "",
    })
    c = _setup_app()
    c.put("/api/modules/ui/config", json={"base_url": "https://new.local", "model": "gpt-4o"})
    assert cfg.ui_vision_config["api_key"] == "old-key"  # 保留
    assert cfg.ui_vision_config["base_url"] == "https://new.local"
    assert cfg.ui_vision_config["model"] == "gpt-4o"


# ===== _resolve_vision_config 单元测试 =====


def test_resolve_fallback_to_global(monkeypatch):
    """UI 配置为空 → 回退全局。"""
    from insight_aitest.modules.ui.backend.engine import executor as exe

    class FakeCfg:
        ui_vision_config = {}
        llm_base_url = "https://global.local/v1"
        llm_api_key = "global-key"
        vision_model = ""
        chat_model = "global-chat"

    import insight_aitest.platform.services.kb.deps as kb_deps
    monkeypatch.setattr(kb_deps, "get_llm_config", lambda: FakeCfg())

    resolved = exe._resolve_vision_config()
    assert resolved["base_url"] == "https://global.local/v1"
    assert resolved["api_key"] == "global-key"
    assert resolved["model"] == "global-chat"


def test_resolve_ui_overrides_global(monkeypatch):
    """UI 配置非空 → 覆盖全局。"""
    from insight_aitest.modules.ui.backend.engine import executor as exe

    class FakeCfg:
        ui_vision_config = {
            "base_url": "https://ui.local/v1", "api_key": "ui-key", "model": "gpt-4o",
        }
        llm_base_url = "https://global.local/v1"
        llm_api_key = "global-key"
        vision_model = ""
        chat_model = "global-chat"

    import insight_aitest.platform.services.kb.deps as kb_deps
    monkeypatch.setattr(kb_deps, "get_llm_config", lambda: FakeCfg())

    resolved = exe._resolve_vision_config()
    assert resolved["base_url"] == "https://ui.local/v1"
    assert resolved["api_key"] == "ui-key"
    assert resolved["model"] == "gpt-4o"


def test_resolve_partial_override(monkeypatch):
    """UI 只配了 model，base_url 和 api_key 回退全局（字段级回退）。"""
    from insight_aitest.modules.ui.backend.engine import executor as exe

    class FakeCfg:
        ui_vision_config = {"model": "gpt-4o"}  # 只配 model
        llm_base_url = "https://global.local/v1"
        llm_api_key = "global-key"
        vision_model = ""
        chat_model = "deepseek-chat"

    import insight_aitest.platform.services.kb.deps as kb_deps
    monkeypatch.setattr(kb_deps, "get_llm_config", lambda: FakeCfg())

    resolved = exe._resolve_vision_config()
    assert resolved["base_url"] == "https://global.local/v1"  # 回退
    assert resolved["api_key"] == "global-key"  # 回退
    assert resolved["model"] == "gpt-4o"  # UI 值
