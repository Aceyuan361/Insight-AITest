# -*- coding: utf-8 -*-
from unittest.mock import MagicMock

from insight_aitest.platform.services.llm.config import AIConfig
from insight_aitest.platform.services.kb.retriever import Retriever
from insight_aitest.platform.services.kb.models import ScoredChunk
from insight_aitest.platform.services.kb.models import Chunk, Document, DocumentStatus


def _chunk(idx, score):
    import datetime
    return ScoredChunk(
        chunk=Chunk(id=idx, document_id=1, chunk_index=idx, text=f"t{idx}",
                    char_start=0, char_end=2),
        score=score,
        document=Document(id=1, filename="a.pdf", storage_path="/p", mime_type=None,
                          char_count=0, chunk_count=0, status=DocumentStatus.READY,
                          error_message=None, content_hash=None,
                          created_at=datetime.datetime.now(),
                          updated_at=datetime.datetime.now()),
    )


def test_retrieve_filters_by_min_score():
    vs = MagicMock()
    cfg = AIConfig(llm_api_key="k", embed_dim=4, top_k=4, min_score=0.5, vector_enabled=True)
    llm = MagicMock()
    llm.embed_query.return_value = [0.1, 0.2, 0.3, 0.4]
    vs.search.return_value = [_chunk(0, 0.8), _chunk(1, 0.3), _chunk(2, 0.6)]
    r = Retriever(vs, None, llm, cfg)
    results = r.retrieve("query")
    assert len(results) == 2  # 0.3 被过滤
    assert results[0].score == 0.8


def test_retrieve_empty_when_no_hits():
    vs = MagicMock()
    cfg = AIConfig(llm_api_key="k", embed_dim=4, top_k=4, min_score=0.3, vector_enabled=True)
    llm = MagicMock()
    llm.embed_query.return_value = [0.1] * 4
    vs.search.return_value = []
    r = Retriever(vs, None, llm, cfg)
    assert r.retrieve("query") == []


def test_retrieve_embed_failure_returns_empty():
    """embedding 失败时降级为空检索（不抛异常）。"""
    vs = MagicMock()
    cfg = AIConfig(llm_api_key="k", embed_dim=4, top_k=4, min_score=0.3, vector_enabled=True)
    llm = MagicMock()
    llm.embed_query.side_effect = Exception("network")
    vs.search.return_value = []
    r = Retriever(vs, None, llm, cfg)
    assert r.retrieve("query") == []


def test_retrieve_vector_disabled_returns_empty():
    """vector_enabled=False：不调 embedding，直接返回空（个人版默认）。"""
    vs = MagicMock()
    cfg = AIConfig(llm_api_key="k", embed_dim=4, top_k=4, min_score=0.3, vector_enabled=False)
    llm = MagicMock()
    r = Retriever(vs, None, llm, cfg)
    assert r.retrieve("query") == []
    llm.embed_query.assert_not_called()  # 不调 embedding
    vs.search.assert_not_called()  # 不查向量库


# ===== P1-C: LLM-as-reranker =====


def test_rerank_disabled_no_llm_call():
    """rerank 关闭时：不调 LLM chat，按向量排序返回 top_k。"""
    vs = MagicMock()
    cfg = AIConfig(
        llm_api_key="k", embed_dim=4, top_k=2, min_score=0.0,
        rerank_enabled=False, vector_enabled=True,
    )
    llm = MagicMock()
    llm.embed_query.return_value = [0.1] * 4
    vs.search.return_value = [_chunk(0, 0.9), _chunk(1, 0.8), _chunk(2, 0.7)]
    r = Retriever(vs, None, llm, cfg)
    results = r.retrieve("query")
    assert len(results) == 2
    llm.chat.assert_not_called()  # 未启用 rerank，不应调 chat
    # search 时取 top_k=2（不放大）
    assert vs.search.call_args.kwargs["top_k"] == 2


def test_rerank_enabled_expands_fetch_k():
    """rerank 开启时：search 放大到 rerank_fetch_k，再用 LLM 重排。"""
    vs = MagicMock()
    cfg = AIConfig(
        llm_api_key="k", embed_dim=4, top_k=2, min_score=0.0,
        rerank_enabled=True, rerank_fetch_k=12, vector_enabled=True,
    )
    llm = MagicMock()
    llm.embed_query.return_value = [0.1] * 4
    vs.search.return_value = [_chunk(i, 0.9 - i * 0.1) for i in range(12)]
    # LLM 打分：让索引 5 最高，索引 0 最低
    llm.chat.return_value = "[1,1,1,1,1,10,1,1,1,1,1,1]"
    r = Retriever(vs, None, llm, cfg)
    results = r.retrieve("query")
    assert vs.search.call_args.kwargs["top_k"] == 12  # 放大召回
    assert llm.chat.call_count == 1  # 单次批量打分
    assert len(results) == 2  # 最终 top_k=2
    assert results[0].chunk.id == 5  # LLM 给最高分的排第一


def test_rerank_llm_failure_falls_back_to_vector_order():
    """LLM 打分异常时静默回退向量排序（不阻断检索）。"""
    vs = MagicMock()
    cfg = AIConfig(
        llm_api_key="k", embed_dim=4, top_k=2, min_score=0.0,
        rerank_enabled=True, rerank_fetch_k=5, vector_enabled=True,
    )
    llm = MagicMock()
    llm.embed_query.return_value = [0.1] * 4
    vs.search.return_value = [_chunk(0, 0.9), _chunk(1, 0.8), _chunk(2, 0.7)]
    llm.chat.side_effect = Exception("LLM 挂了")
    r = Retriever(vs, None, llm, cfg)
    results = r.retrieve("query")
    assert len(results) == 2
    # 回退向量排序：0.9 > 0.8
    assert results[0].chunk.id == 0


def test_rerank_skipped_when_candidates_le_top_k():
    """候选数 ≤ top_k 时不触发 rerank（没必要重排）。"""
    vs = MagicMock()
    cfg = AIConfig(
        llm_api_key="k", embed_dim=4, top_k=4, min_score=0.0,
        rerank_enabled=True, rerank_fetch_k=12, vector_enabled=True,
    )
    llm = MagicMock()
    llm.embed_query.return_value = [0.1] * 4
    vs.search.return_value = [_chunk(0, 0.9), _chunk(1, 0.8)]  # 只有 2 个
    r = Retriever(vs, None, llm, cfg)
    results = r.retrieve("query")
    llm.chat.assert_not_called()  # 候选 ≤ top_k，跳过 rerank
    assert len(results) == 2


def test_parse_score_array_valid():
    assert Retriever._parse_score_array("[8, 3, 10]", 3) == [8.0, 3.0, 10.0]


def test_parse_score_array_with_noise():
    # LLM 可能带前后文字
    raw = "好的，分数如下：\n[9, 2, 5]\n以上。"
    assert Retriever._parse_score_array(raw, 3) == [9.0, 2.0, 5.0]


def test_parse_score_array_pads_short():
    # 返回不足时补 0
    assert Retriever._parse_score_array("[9, 2]", 3) == [9.0, 2.0, 0.0]


def test_parse_score_array_invalid_returns_zeros():
    assert Retriever._parse_score_array("无法解析", 3) == [0.0, 0.0, 0.0]
