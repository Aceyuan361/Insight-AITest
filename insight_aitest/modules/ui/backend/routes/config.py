# -*- coding: utf-8 -*-
"""UI 自动化视觉模型独立配置 API。

端点：
  GET   /config   读取 UI 视觉模型配置（api_key mask）
  PUT   /config   更新 UI 视觉模型配置（写入 llm_config.json + reset 单例）
  POST  /config/test  测试连通性
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/config", tags=["ui"])


class UIConfigOut(BaseModel):
    base_url: str
    api_key_set: bool
    model: str
    # 全局回退值（供前端显示"当前回退到 xxx"）
    global_base_url: str
    global_model: str


class UIConfigUpdate(BaseModel):
    base_url: str | None = None
    api_key: str | None = None  # 留空 = 不修改
    model: str | None = None


class TestRequest(BaseModel):
    base_url: str
    api_key: str
    model: str


def _get_cfg():
    from insight_aitest.platform.services.kb.deps import get_llm_config
    return get_llm_config()


@router.get("")
async def get_ui_config() -> dict:
    cfg = _get_cfg()
    ui = cfg.ui_vision_config or {}
    return {
        "base_url": ui.get("base_url", ""),
        "api_key_set": bool(ui.get("api_key", "")),
        "model": ui.get("model", ""),
        "global_base_url": cfg.llm_base_url,
        "global_model": cfg.vision_model or cfg.chat_model,
    }


@router.put("")
async def update_ui_config(body: UIConfigUpdate) -> dict:
    from insight_aitest.platform.services.llm.config import save_config
    from insight_aitest.platform.services.kb.deps import reset_llm_singletons

    cfg = _get_cfg()
    ui = dict(cfg.ui_vision_config or {})

    if body.base_url is not None:
        ui["base_url"] = body.base_url.strip()
    if body.api_key is not None and body.api_key.strip():
        ui["api_key"] = body.api_key.strip()
    if body.model is not None:
        ui["model"] = body.model.strip()

    cfg.ui_vision_config = ui
    save_config(cfg)
    reset_llm_singletons()

    return await get_ui_config()


@router.post("/test")
async def test_connection(body: TestRequest) -> dict:
    """测试视觉模型连通性（发一个轻量 chat completion 请求）。"""
    import httpx

    base_url = body.base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {body.api_key}"},
                json={
                    "model": body.model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1,
                },
            )
        if r.status_code == 200:
            return {"ok": True, "message": f"连接成功（{body.model}）"}
        return {"ok": False, "message": f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}
