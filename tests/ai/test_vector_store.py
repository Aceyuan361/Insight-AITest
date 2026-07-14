# -*- coding: utf-8 -*-
from unittest.mock import MagicMock

from insight_aitest.platform.services.llm.config import AIConfig
from insight_aitest.platform.services.kb.vector_store import VectorStore
from insight_aitest.platform.services.kb.models import ScoredChunk
from insight_aitest.platform.services.llm.client import LLMClient
from insight_aitest.platform.services.kb.database import KBDatabase
from insight_aitest.platform.services.kb.models import Chunk


def _setup(tmp_path):
    db = KBDatabase(str(tmp_path / "ai.db"), embed_dim=4)
    cfg = AIConfig(llm_api_key="k", embed_dim=4, embed_batch_size=2)
    llm = MagicMock(spec=LLMClient)
    # embed 返回可预测的向量：第 i 个文本返回首维=i%4
    def fake_embed(texts):
        return [[float(i % 4), 0.0, 0.0, 0.0] for i in range(len(texts))]
    llm.embed.side_effect = fake_embed
    return db, cfg, llm


def test_upsert_and_search(tmp_path):
    db, cfg, llm = _setup(tmp_path)
    vs = VectorStore(db, llm, cfg)
    doc_id = db.create_document("a.pdf", "/p", "h", "application/pdf")
    chunks = [
        Chunk(document_id=doc_id, chunk_index=0, text="aaa", char_start=0, char_end=3),
        Chunk(document_id=doc_id, chunk_index=1, text="bbb", char_start=3, char_end=6),
    ]
    db.insert_chunks(doc_id, chunks)
    vs.upsert_chunks(doc_id, chunks)
    # 搜索：query 向量首维=0，应命中 chunk_index=0（向量首维=0）
    results = vs.search([0.0, 0.0, 0.0, 0.0], top_k=2, document_ids=None)
    assert len(results) >= 1
    assert all(isinstance(r, ScoredChunk) for r in results)


def test_delete_document_removes_vectors(tmp_path):
    db, cfg, llm = _setup(tmp_path)
    vs = VectorStore(db, llm, cfg)
    doc_id = db.create_document("a.pdf", "/p", "h", "application/pdf")
    db.insert_chunks(doc_id, [Chunk(document_id=doc_id, chunk_index=0,
                                    text="x", char_start=0, char_end=1)])
    vs.upsert_chunks(doc_id, [])
    vs.delete_document(doc_id)
    results = vs.search([0.0, 0.0, 0.0, 0.0], top_k=5, document_ids=None)
    assert all(r.chunk.document_id != doc_id for r in results)


def test_search_empty_when_no_data(tmp_path):
    db, cfg, llm = _setup(tmp_path)
    vs = VectorStore(db, llm, cfg)
    results = vs.search([0.0, 0.0, 0.0, 0.0], top_k=5, document_ids=None)
    assert results == []


def test_search_filtered_by_document_ids(tmp_path):
    db, cfg, llm = _setup(tmp_path)
    vs = VectorStore(db, llm, cfg)
    doc1 = db.create_document("a.pdf", "/p1", "h1", "application/pdf")
    doc2 = db.create_document("b.pdf", "/p2", "h2", "application/pdf")
    db.insert_chunks(doc1, [Chunk(document_id=doc1, chunk_index=0, text="a", char_start=0, char_end=1)])
    db.insert_chunks(doc2, [Chunk(document_id=doc2, chunk_index=0, text="b", char_start=0, char_end=1)])
    vs.upsert_chunks(doc1, [])
    vs.upsert_chunks(doc2, [])
    # 只在 doc1 范围搜
    results = vs.search([0.0, 0.0, 0.0, 0.0], top_k=5, document_ids=[doc1])
    assert all(r.chunk.document_id == doc1 for r in results)
