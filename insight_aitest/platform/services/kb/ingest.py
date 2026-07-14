# -*- coding: utf-8 -*-
"""文档处理流水线（平台共享服务）：parse → chunk → embed。

状态机：pending → parsing → chunking → embedding → ready
失败分支：parse_failed / embed_failed / embed_partial
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from insight_aitest.platform.services.kb.chunker import ChunkConfig, Chunker, SemanticChunker
from insight_aitest.platform.services.kb.loader import get_loader
from insight_aitest.platform.services.kb.loader.base import DocumentLoadError, UnsupportedFormatError
from insight_aitest.platform.services.kb.models import DocumentStatus, EmbedStatus

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from insight_aitest.platform.services.llm.config import LLMConfig
    from insight_aitest.platform.services.kb.vector_store import VectorStore
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.kb.database import KBDatabase


def _make_chunker(config: "LLMConfig", llm: "LLMClient") -> Chunker | SemanticChunker:
    """根据 config.chunk_strategy 选择分块器。

    semantic 策略需 embedding 可用（vector_enabled=True 且 llm 存在），否则回退 recursive。
    回退在工厂层做粗判；SemanticChunker.split 内部对 embed 调用失败再 try/except 细判（双层保护）。
    """
    if (
        getattr(config, "chunk_strategy", "recursive") == "semantic"
        and getattr(config, "vector_enabled", False)
        and llm is not None
    ):
        return SemanticChunker(
            ChunkConfig(
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap,
                strategy="semantic",
                semantic_breakpoint=getattr(config, "semantic_breakpoint", 2.58),
                embed_batch_size=getattr(config, "embed_batch_size", 64),
            ),
            llm=llm,
        )
    if getattr(config, "chunk_strategy", "recursive") == "semantic":
        logger.warning(
            "请求语义分块但 embedding 不可用（vector_enabled=False 或 llm 缺失），回退递归字符分块"
        )
    return Chunker(ChunkConfig(chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap))


def process_document(
    document_id: int,
    db: "KBDatabase",
    vector_store: "VectorStore",
    llm: "LLMClient",
    config: "LLMConfig",
) -> None:
    """处理单个文档的全链路。在后台线程中运行。异常被捕获并写入文档状态。"""
    doc = db.get_document(document_id)
    if doc is None:
        return

    # 1. 解析
    db.update_document_status(document_id, DocumentStatus.PARSING)
    try:
        loader = get_loader(doc.filename)
        parsed = loader.load(Path(doc.storage_path))
    except (UnsupportedFormatError, DocumentLoadError) as e:
        db.update_document_status(document_id, DocumentStatus.PARSE_FAILED, error_message=str(e))
        return
    except Exception as e:
        db.update_document_status(
            document_id, DocumentStatus.PARSE_FAILED, error_message=f"解析异常: {e}"
        )
        return

    # 2. 分块
    db.update_document_status(document_id, DocumentStatus.CHUNKING, char_count=len(parsed.content))
    chunker = _make_chunker(config, llm)
    raw_chunks = chunker.split(parsed)
    if len(raw_chunks) > config.max_chunks_per_doc:
        db.update_document_status(
            document_id,
            DocumentStatus.PARSE_FAILED,
            error_message=f"分块数 {len(raw_chunks)} 超过上限 {config.max_chunks_per_doc}，请切分文档。",
        )
        return
    # 写入 chunks 表
    for c in raw_chunks:
        c.document_id = document_id
    db.insert_chunks(document_id, raw_chunks)
    db.update_document_status(document_id, DocumentStatus.EMBEDDING, chunk_count=len(raw_chunks))

    # 3. 向量化（VectorStore 内部从 DB 读 chunks 拿 id）
    #    向量检索关闭时跳过向量化：文档仍可分块存储/查阅，仅不做向量召回
    if not getattr(config, "vector_enabled", False):
        db.update_document_status(document_id, DocumentStatus.READY)
        return

    try:
        vector_store.upsert_chunks(document_id, raw_chunks)
    except Exception as e:
        db.update_document_status(
            document_id, DocumentStatus.EMBED_FAILED, error_message=f"向量化失败: {e}"
        )
        return

    # 4. 判定终态
    db_chunks = db.get_chunks_by_document(document_id)
    ok = sum(1 for c in db_chunks if c.embed_status == EmbedStatus.OK)
    failed = sum(1 for c in db_chunks if c.embed_status == EmbedStatus.FAILED)
    if failed == 0:
        db.update_document_status(document_id, DocumentStatus.READY)
    elif ok == 0:
        db.update_document_status(
            document_id, DocumentStatus.EMBED_FAILED, error_message=f"全部 {failed} 块向量化失败"
        )
    else:
        db.update_document_status(
            document_id, DocumentStatus.EMBED_PARTIAL, error_message=f"{ok} 块成功，{failed} 块失败"
        )
