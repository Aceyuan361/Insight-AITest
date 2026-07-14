# -*- coding: utf-8 -*-
"""测试 ingest 的分块器工厂 + 回退逻辑。"""
from unittest.mock import MagicMock

from insight_aitest.platform.services.kb.chunker import Chunker, SemanticChunker
from insight_aitest.platform.services.kb.ingest import _make_chunker
from insight_aitest.platform.services.llm.config import LLMConfig


def _cfg(strategy: str, vector: bool) -> LLMConfig:
    cfg = LLMConfig()
    cfg.chunk_strategy = strategy
    cfg.vector_enabled = vector
    return cfg


def test_make_chunker_recursive():
    """strategy=recursive 总是返回 Chunker。"""
    llm = MagicMock()
    chunker = _make_chunker(_cfg("recursive", True), llm)
    assert isinstance(chunker, Chunker)


def test_make_chunker_semantic_with_vector():
    """strategy=semantic + vector_enabled=True + llm 存在 → SemanticChunker。"""
    llm = MagicMock()
    chunker = _make_chunker(_cfg("semantic", True), llm)
    assert isinstance(chunker, SemanticChunker)


def test_make_chunker_semantic_fallback_no_vector():
    """strategy=semantic + vector_enabled=False → 回退 Chunker。"""
    llm = MagicMock()
    chunker = _make_chunker(_cfg("semantic", False), llm)
    assert isinstance(chunker, Chunker)
    assert not isinstance(chunker, SemanticChunker)


def test_make_chunker_semantic_fallback_no_llm():
    """strategy=semantic + llm=None → 回退 Chunker。"""
    chunker = _make_chunker(_cfg("semantic", True), None)
    assert isinstance(chunker, Chunker)
