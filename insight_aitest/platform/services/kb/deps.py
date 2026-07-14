# -*- coding: utf-8 -*-
"""平台 KB/LLM 单例（ai 和 testcase 模块都通过这里获取）。"""

from __future__ import annotations

from insight_aitest.platform.services.llm.config import LLMConfig, load_config
from insight_aitest.platform.services.llm.client import LLMClient
from insight_aitest.platform.services.kb.database import KBDatabase
from insight_aitest.platform.services.kb.vector_store import VectorStore
from insight_aitest.platform.services.kb.retriever import Retriever

_llm_config: LLMConfig | None = None
_kb_db: KBDatabase | None = None
_llm: LLMClient | None = None
_vector_store: VectorStore | None = None
_retriever: Retriever | None = None
_config_file: str | None = None


def get_llm_config() -> LLMConfig:
    global _llm_config, _config_file
    if _llm_config is None:
        _llm_config = load_config(config_file=_config_file)
    return _llm_config


def set_config_file(path: str | None) -> None:
    global _config_file
    _config_file = path


def get_kb_db() -> KBDatabase:
    global _kb_db
    if _kb_db is None:
        cfg = get_llm_config()
        _kb_db = KBDatabase(cfg.db_path, embed_dim=cfg.embed_dim, vector_enabled=cfg.vector_enabled)
    return _kb_db


def get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        _llm = LLMClient(get_llm_config())
    return _llm


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(get_kb_db(), get_llm(), get_llm_config())
    return _vector_store


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever(get_vector_store(), get_kb_db(), get_llm(), get_llm_config())
    return _retriever


def reset_llm_singletons() -> None:
    """PUT /config 后调用：重建 LLM/VectorStore/Retriever/KBDatabase（config 重新加载）。

    vector_enabled 切换会改变 KBDatabase 构造行为，故 _kb_db 也需重建。
    保留 config_file/db_path/docs_dir（运行期展开值，不入文件），避免 reload 后写错位置。
    """
    global _llm_config, _llm, _vector_store, _retriever, _kb_db
    prev_cfg = _llm_config
    _llm_config = load_config(config_file=_config_file)
    # 保留运行期路径（load_config 从文件读不到这些，因为 save_config 不写回它们）
    if prev_cfg is not None:
        _llm_config.config_file = prev_cfg.config_file
        _llm_config.db_path = prev_cfg.db_path
        _llm_config.docs_dir = prev_cfg.docs_dir
    _llm = None
    _vector_store = None
    _retriever = None
    _kb_db = None
