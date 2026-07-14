# -*- coding: utf-8 -*-
from pathlib import Path
from unittest.mock import MagicMock

from insight_aitest.platform.services.llm.config import AIConfig
from insight_aitest.platform.services.kb.ingest import process_document
from insight_aitest.platform.services.kb.vector_store import VectorStore
from insight_aitest.platform.services.llm.client import LLMClient
from insight_aitest.platform.services.kb.database import KBDatabase
from insight_aitest.platform.services.kb.models import DocumentStatus

FIXTURES = Path(__file__).parent / "fixtures"


def test_process_markdown_success(tmp_path):
    db = KBDatabase(str(tmp_path / "ai.db"), embed_dim=4)
    cfg = AIConfig(
        llm_api_key="k", embed_dim=4, chunk_size=100, chunk_overlap=10, vector_enabled=True
    )
    llm = MagicMock(spec=LLMClient)
    llm.embed.side_effect = lambda texts: [[0.1] * 4 for _ in texts]
    vs = MagicMock(spec=VectorStore)
    # 准备：复制 fixture 到 storage
    storage = tmp_path / "store"
    storage.mkdir()
    src = FIXTURES / "sample.md"
    dst = storage / "a.md"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    doc_id = db.create_document("a.md", str(dst), "hash", "text/markdown")
    process_document(doc_id, db, vs, llm, cfg)

    doc = db.get_document(doc_id)
    assert doc.status == DocumentStatus.READY
    assert doc.char_count > 0
    assert doc.chunk_count > 0
    vs.upsert_chunks.assert_called_once()


def test_process_vector_disabled_skips_embed(tmp_path):
    """vector_enabled=False：文档仍解析+分块+存储，但跳过向量化直接 READY。"""
    db = KBDatabase(str(tmp_path / "ai.db"), embed_dim=4)
    cfg = AIConfig(
        llm_api_key="k", embed_dim=4, chunk_size=100, chunk_overlap=10, vector_enabled=False
    )
    llm = MagicMock(spec=LLMClient)
    vs = MagicMock(spec=VectorStore)
    storage = tmp_path / "store"
    storage.mkdir()
    src = FIXTURES / "sample.md"
    dst = storage / "a.md"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    doc_id = db.create_document("a.md", str(dst), "hash", "text/markdown")
    process_document(doc_id, db, vs, llm, cfg)

    doc = db.get_document(doc_id)
    assert doc.status == DocumentStatus.READY
    assert doc.chunk_count > 0  # 仍分块存储
    vs.upsert_chunks.assert_not_called()  # 但不向量化
    llm.embed.assert_not_called()


def test_process_parse_failure(tmp_path):
    db = KBDatabase(str(tmp_path / "ai.db"), embed_dim=4)
    cfg = AIConfig(llm_api_key="k", embed_dim=4)
    llm = MagicMock(spec=LLMClient)
    vs = MagicMock(spec=VectorStore)
    # 指向不存在的文件
    doc_id = db.create_document("x.pdf", "/nonexistent/x.pdf", "h", "application/pdf")
    process_document(doc_id, db, vs, llm, cfg)
    doc = db.get_document(doc_id)
    assert doc.status == DocumentStatus.PARSE_FAILED
    assert doc.error_message is not None
