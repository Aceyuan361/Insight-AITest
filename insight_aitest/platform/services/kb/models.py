# -*- coding: utf-8 -*-
"""知识库数据模型（平台共享服务 + P0-1 ORM 迁移）。

从 ai 模块上提：KB 相关的 Document/Chunk/ParsedDocument/ScoredChunk + 枚举。
ai 模块保留 Conversation/Message/Role/Citation（对话专属）。

P0-1：Document/Chunk 从手写 dataclass 改为 ``MappedAsDataclass`` ORM 模型，
同名同字段替换——业务层（routes/vector_store/retriever/ingest/tests）用法不变。
- 枚举字段（DocumentStatus/EmbedStatus）Python 侧仍是枚举，存 ``.value`` TEXT。
- chunk_embeddings（vec0 虚拟表）不入 ORM，由 KBDatabase 原生 sqlite3 通道管理。
- ParsedDocument/ScoredChunk 是内存流水线模型（非持久化），保持 dataclass。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from insight_aitest.platform.persistence import Base
from insight_aitest.platform.persistence.types import enum_values

# ============ 枚举 ============


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    READY = "ready"
    PARSE_FAILED = "parse_failed"
    EMBED_FAILED = "embed_failed"
    EMBED_PARTIAL = "embed_partial"

    @property
    def is_terminal(self) -> bool:
        return self in (
            DocumentStatus.READY,
            DocumentStatus.PARSE_FAILED,
            DocumentStatus.EMBED_FAILED,
            DocumentStatus.EMBED_PARTIAL,
        )


class EmbedStatus(str, Enum):
    PENDING = "pending"
    OK = "ok"
    FAILED = "failed"


# ============ DB 行模型（ORM）============
# 所有模型的 id 默认 None（插入前构造，DB 回填 id）。


class Document(MappedAsDataclass, Base):
    """文档（ORM 模型，即业务层 DTO）。

    ``id`` 进 __init__（默认 None）：vector_store 从原生 SQL 结果行构造 Document 时
    传 id=（带 DB id 的已读回对象），与新建（id=None 由 DB 回填）两种用法都要支持。

    project_id/version_id：可空逻辑外键（跨 DB 文件，不加 FK 约束）。
    旧数据 NULL = 未分类。ensure_schema 幂等补列。

    KB 升级新增（幂等 ALTER TABLE 补列，旧数据 NULL/空）：
    - tags：JSON 数组字符串，如 '["登录","接口"]'，支持多词标签（CommaList 无法表达含逗号的标签）
    - doc_type：文档类型（需求/设计/接口/测试/其他）
    - description：一句话描述
    """

    __tablename__ = "documents"
    __table_args__ = (Index("idx_documents_status", "status"),)

    id: Mapped[int | None] = mapped_column(
        Integer, primary_key=True, autoincrement=True, default=None
    )
    filename: Mapped[str] = mapped_column(Text, default="")
    storage_path: Mapped[str] = mapped_column(Text, default="")
    mime_type: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus, values_callable=enum_values), default=DocumentStatus.PENDING
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    content_hash: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    version_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    # KB 升级：标签与元数据（幂等补列，旧数据为空）
    tags: Mapped[str] = mapped_column(Text, default="")  # JSON 数组字符串
    doc_type: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)


class Chunk(MappedAsDataclass, Base):
    """分块（ORM 模型，即业务层 DTO）。chunk_embeddings（vec0）不入 ORM。

    ``id`` 进 __init__（默认 None）：chunker 构造时传 id=None/document_id=0，
    由 DB 回填。与 TestCase 的 init=False 不同，因 chunker 显式传 id。
    """

    __tablename__ = "chunks"
    __table_args__ = (Index("idx_chunks_document", "document_id"),)

    id: Mapped[int | None] = mapped_column(
        Integer, primary_key=True, autoincrement=True, default=None
    )
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), default=0
    )
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text, default="")
    char_start: Mapped[int] = mapped_column(Integer, default=0)
    char_end: Mapped[int] = mapped_column(Integer, default=0)
    embed_status: Mapped[EmbedStatus] = mapped_column(
        SAEnum(EmbedStatus, values_callable=enum_values), default=EmbedStatus.PENDING
    )


class DocumentVersion(MappedAsDataclass, Base):
    """文档历史版本快照（KB 升级新增）。

    每次编辑保存 / 重新上传覆盖时，旧内容写入此表作为快照。
    documents 表始终持有「当前版本」；本表保存历史版本（is_current 标记最新回滚点）。
    storage_path 指向旧版本原始文件的独立副本（回滚时直接复用，不依赖 documents.storage_path）。
    """

    __tablename__ = "document_versions"
    __table_args__ = (Index("idx_doc_versions_doc", "document_id"),)

    id: Mapped[int | None] = mapped_column(
        Integer, primary_key=True, autoincrement=True, default=None
    )
    document_id: Mapped[int] = mapped_column(Integer, default=0)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    storage_path: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(Text, default="")
    is_current: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)


# ============ 内存流水线模型（非持久化，保持 dataclass）===========


@dataclass
class ParsedDocument:
    """Loader 输出 / Chunker 输入（≠ DB 的 Document）。"""

    filename: str
    content: str
    meta: dict = field(default_factory=dict)


@dataclass
class ScoredChunk:
    """Retriever 输出：命中的 chunk + 分数 + 所属文档。"""

    chunk: Chunk
    score: float
    document: Document
