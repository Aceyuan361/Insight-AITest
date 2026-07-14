# -*- coding: utf-8 -*-
"""配置读写 API。GET 脱敏，PUT 写文件 + 重建单例。embed_dim 不允许热更新。

扩展（Cursor 风格模型管理）：
- GET /config          返回配置（含 providers 列表 + active_provider_id，key 脱敏）
- PUT /config          写扁平字段（向后兼容）+ 可选切换 active provider
- POST /config/test    临时 client 连通性探测（不写配置）
- GET /config/presets  返回内置 Provider 预设
- PUT /config/providers/{id}   新增/更新单个 Provider
- DELETE /config/providers/{id} 删除 Provider（active 不允许删）
- PUT /config/activate/{id}     切换 active provider（投影到扁平字段 + 重建单例）
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from insight_aitest.platform.services.llm.config import AIConfig, save_config, apply_provider
from insight_aitest.platform.services.llm.client import test_connection
from insight_aitest.modules.ai.backend.deps import get_config, reset_singletons

router = APIRouter(prefix="/config", tags=["ai-config"])


# ===== 内置 Provider 预设（前端切换面板用，不在后端硬编码锁定）=====
PROVIDER_PRESETS = [
    {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner", "deepseek-v4-flash"],
    },
    {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "o1-mini", "o3-mini"],
    },
    {
        "name": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4-plus", "glm-4-air", "glm-4-flash", "glm-4v"],
    },
    {
        "name": "通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-plus", "qwen-turbo", "qwen-max", "qwen-vl-max"],
    },
    {
        "name": "Ollama（本地）",
        "base_url": "http://localhost:11434/v1",
        "models": ["llama3.1", "qwen2.5", "gemma2"],
    },
]


class ProviderOut(BaseModel):
    """对外 Provider（api_key 脱敏为 api_key_set）。"""

    id: str
    name: str
    base_url: str
    chat_model: str
    vision_model: str = ""
    api_key_set: bool = False


class ConfigOut(BaseModel):
    llm_base_url: str
    chat_model: str
    vision_model: str
    embed_model: str
    embed_dim: int
    api_key_set: bool
    chunk_size: int
    chunk_overlap: int
    chunk_strategy: str
    semantic_breakpoint: float
    top_k: int
    min_score: float
    rerank_enabled: bool
    rerank_fetch_k: int
    history_turns: int
    ocr_enabled: bool
    vector_enabled: bool
    embed_base_url: str
    embed_api_key_set: bool
    # 多 Provider
    providers: list[ProviderOut] = []
    active_provider_id: str = ""


class ConfigUpdate(BaseModel):
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    chat_model: str | None = None
    vision_model: str | None = None
    embed_model: str | None = None
    embed_dim: int | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    chunk_strategy: str | None = None
    semantic_breakpoint: float | None = None
    top_k: int | None = None
    min_score: float | None = None
    rerank_enabled: bool | None = None
    rerank_fetch_k: int | None = None
    history_turns: int | None = None
    ocr_enabled: bool | None = None
    vector_enabled: bool | None = None
    embed_base_url: str | None = None
    embed_api_key: str | None = None


class ProviderUpsert(BaseModel):
    """新增/更新 Provider 的请求体。id 可选（缺省自动生成）。"""

    id: str | None = None
    name: str
    base_url: str
    api_key: str = ""  # 空串 = 不修改（更新时）
    chat_model: str = ""
    vision_model: str = ""


class TestRequest(BaseModel):
    """连通性探测请求（临时 client，不写配置）。"""

    base_url: str
    api_key: str
    model: str


def _provider_to_out(p: dict) -> ProviderOut:
    """Provider dict → ProviderOut（脱敏）。"""
    return ProviderOut(
        id=p.get("id", ""),
        name=p.get("name", ""),
        base_url=p.get("base_url", ""),
        chat_model=p.get("chat_model", ""),
        vision_model=p.get("vision_model", ""),
        api_key_set=bool(p.get("api_key")),
    )


def _to_config_out(cfg: AIConfig) -> ConfigOut:
    return ConfigOut(
        llm_base_url=cfg.llm_base_url,
        chat_model=cfg.chat_model,
        vision_model=cfg.vision_model,
        embed_model=cfg.embed_model,
        embed_dim=cfg.embed_dim,
        api_key_set=cfg.api_key_set,
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
        chunk_strategy=cfg.chunk_strategy,
        semantic_breakpoint=cfg.semantic_breakpoint,
        top_k=cfg.top_k,
        min_score=cfg.min_score,
        rerank_enabled=cfg.rerank_enabled,
        rerank_fetch_k=cfg.rerank_fetch_k,
        history_turns=cfg.history_turns,
        ocr_enabled=cfg.ocr_enabled,
        vector_enabled=cfg.vector_enabled,
        embed_base_url=cfg.embed_base_url,
        embed_api_key_set=bool(cfg.embed_api_key),
        providers=[_provider_to_out(p) for p in (cfg.providers or [])],
        active_provider_id=cfg.active_provider_id or "",
    )


@router.get("/presets")
async def get_presets() -> dict:
    """返回内置 Provider 预设（前端面板快捷填充）。"""
    return {"presets": PROVIDER_PRESETS}


@router.get("", response_model=ConfigOut)
async def get_config_route(cfg: AIConfig = Depends(get_config)) -> ConfigOut:
    return _to_config_out(cfg)


@router.put("", response_model=ConfigOut)
async def update_config(body: ConfigUpdate, cfg: AIConfig = Depends(get_config)) -> ConfigOut:
    # embed_dim 不允许热更新（维度变 = 向量表失效）
    if body.embed_dim is not None and body.embed_dim != cfg.embed_dim:
        raise HTTPException(400, "embed_dim 不支持热更新，需重新索引所有文档")

    for field in (
        "llm_base_url",
        "llm_api_key",
        "chat_model",
        "vision_model",
        "embed_model",
        "chunk_size",
        "chunk_overlap",
        "chunk_strategy",
        "semantic_breakpoint",
        "top_k",
        "min_score",
        "rerank_enabled",
        "rerank_fetch_k",
        "history_turns",
        "ocr_enabled",
        "vector_enabled",
        "embed_base_url",
        "embed_api_key",
    ):
        val = getattr(body, field)
        if val is not None:
            setattr(cfg, field, val)
    # 若有 active provider，把扁平字段同步回该 provider（保持一致性）
    if cfg.active_provider_id and cfg.providers:
        for p in cfg.providers:
            if isinstance(p, dict) and p.get("id") == cfg.active_provider_id:
                p["base_url"] = cfg.llm_base_url
                p["chat_model"] = cfg.chat_model
                p["vision_model"] = cfg.vision_model
                if body.llm_api_key:  # key 改了才同步
                    p["api_key"] = cfg.llm_api_key
                break
    save_config(cfg)
    reset_singletons()
    new_cfg = get_config()
    return _to_config_out(new_cfg)


@router.post("/test")
async def test_provider(body: TestRequest) -> dict:
    """临时 client 探测连通性（不写配置、不动单例）。"""
    ok, msg = test_connection(body.base_url, body.api_key, body.model)
    return {"ok": ok, "message": msg}


@router.put("/providers/{provider_id}", response_model=ConfigOut)
async def upsert_provider(
    provider_id: str,
    body: ProviderUpsert,
    cfg: AIConfig = Depends(get_config),
) -> ConfigOut:
    """新增或更新单个 Provider。provider_id 为 "new" 时新建（忽略 body.id）。"""
    if not cfg.providers:
        cfg.providers = []
    # 查找现有
    target = None
    if provider_id != "new":
        for p in cfg.providers:
            if isinstance(p, dict) and p.get("id") == provider_id:
                target = p
                break
        if target is None:
            raise HTTPException(404, f"Provider {provider_id} 不存在")
    if target is None:
        # 新建
        pid = body.id or provider_id
        if pid == "new" or not pid:
            pid = f"p{uuid.uuid4().hex[:8]}"
        target = {"id": pid}
        cfg.providers.append(target)
        # 第一个 provider 自动设为 active（方便首次配置）
        if not cfg.active_provider_id:
            cfg.active_provider_id = pid
    # 更新字段（api_key 空串 = 不改）
    target["name"] = body.name
    target["base_url"] = body.base_url
    target["chat_model"] = body.chat_model
    target["vision_model"] = body.vision_model
    if body.api_key:
        target["api_key"] = body.api_key
    save_config(cfg)
    reset_singletons()
    return _to_config_out(get_config())


@router.delete("/providers/{provider_id}", response_model=ConfigOut)
async def delete_provider(
    provider_id: str,
    cfg: AIConfig = Depends(get_config),
) -> ConfigOut:
    """删除 Provider。active provider 不允许删除（需先切换到其他）。"""
    if cfg.active_provider_id == provider_id:
        raise HTTPException(400, "不能删除当前生效的 Provider，请先切换到其他 Provider")
    before = len(cfg.providers or [])
    cfg.providers = [
        p for p in (cfg.providers or []) if not (isinstance(p, dict) and p.get("id") == provider_id)
    ]
    if len(cfg.providers) == before:
        raise HTTPException(404, f"Provider {provider_id} 不存在")
    save_config(cfg)
    reset_singletons()
    return _to_config_out(get_config())


@router.put("/activate/{provider_id}", response_model=ConfigOut)
async def activate_provider(
    provider_id: str,
    cfg: AIConfig = Depends(get_config),
) -> ConfigOut:
    """切换 active provider：投影到扁平字段 + 重建单例。"""
    target = None
    for p in cfg.providers or []:
        if isinstance(p, dict) and p.get("id") == provider_id:
            target = p
            break
    if target is None:
        raise HTTPException(404, f"Provider {provider_id} 不存在")
    apply_provider(cfg, provider_id)
    save_config(cfg)
    reset_singletons()
    return _to_config_out(get_config())
