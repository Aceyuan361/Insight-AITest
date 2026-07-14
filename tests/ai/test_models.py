# -*- coding: utf-8 -*-
from datetime import datetime

# KB 模型已上提为平台服务
from insight_aitest.platform.services.kb.models import (
    Document, DocumentStatus, Chunk, EmbedStatus, ParsedDocument,
)
# 会话/消息模型仍在 ai 模块
from insight_aitest.modules.ai.backend.persistence.models import (
    Citation,
)


def test_document_status_enum():
    assert DocumentStatus.PENDING.value == "pending"
    assert DocumentStatus.READY.value == "ready"
    assert DocumentStatus.PARSE_FAILED.value == "parse_failed"
    assert DocumentStatus.EMBED_PARTIAL.value == "embed_partial"


def test_chunk_defaults():
    c = Chunk(document_id=1, chunk_index=0, text="hi",
              char_start=0, char_end=2)
    assert c.id is None
    assert c.embed_status == EmbedStatus.PENDING


def test_parsed_document_is_not_db_document():
    """ParsedDocument（解析结果）与 Document（DB 行）是两个类型。"""
    pd = ParsedDocument(filename="a.md", content="xxx", meta={})
    assert not hasattr(pd, "storage_path")
    d = Document(filename="a.md", storage_path="/p", mime_type=None,
                 char_count=0, chunk_count=0, status=DocumentStatus.PENDING,
                 error_message=None, content_hash=None,
                 created_at=datetime.now(), updated_at=datetime.now())
    assert hasattr(d, "storage_path")


def test_citation_fields():
    c = Citation(document_id=1, document_name="a.pdf", chunk_index=2,
                 snippet="...", score=0.8)
    assert c.document_name == "a.pdf"
