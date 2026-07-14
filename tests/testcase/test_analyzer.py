# -*- coding: utf-8 -*-
"""分析器测试（mock LLM + retriever）。"""
from unittest.mock import MagicMock

from insight_aitest.modules.testcase.backend.generator.analyzer import (
    Analyzer, _extract_json,
)
from insight_aitest.modules.testcase.backend.persistence.models import CaseType, TestType


def _cfg():
    from insight_aitest.platform.services.llm.config import LLMConfig
    return LLMConfig(llm_api_key="k", embed_dim=4)


def test_analyze_returns_points():
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    llm = MagicMock()
    llm.chat.return_value = (
        '```json\n[{"id":"tp-1","summary":"登录正向","suggested_type":"functional",'
        '"suggested_design":"positive","rationale":"需求3.2"}]\n```')
    az = Analyzer(retriever, llm, _cfg())
    points = az.analyze("核心功能", document_ids=None)
    assert len(points) == 1
    assert points[0].summary == "登录正向"
    assert points[0].suggested_type == CaseType.FUNCTIONAL
    assert points[0].suggested_design == TestType.POSITIVE


def test_analyze_parse_fail_returns_empty():
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    llm = MagicMock()
    llm.chat.return_value = "这不是JSON"
    az = Analyzer(retriever, llm, _cfg())
    assert az.analyze("x", document_ids=None) == []


def test_analyze_retriever_error_degrades():
    retriever = MagicMock()
    retriever.retrieve.side_effect = RuntimeError("db down")
    llm = MagicMock()
    llm.chat.return_value = "[]"
    az = Analyzer(retriever, llm, _cfg())
    assert az.analyze("x", document_ids=None) == []


def test_analyze_skips_bad_entries():
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    llm = MagicMock()
    llm.chat.return_value = (
        '[{"id":"tp-1","summary":"好的","suggested_type":"functional","suggested_design":"positive"},'
        '{"summary":"无id但有summary","suggested_type":"bad_type"},'  # bad_type → ValueError 跳过
        '"not_a_dict"]')
    az = Analyzer(retriever, llm, _cfg())
    points = az.analyze("x", document_ids=None)
    assert len(points) == 1
    assert points[0].summary == "好的"


def test_extract_json_clean_array():
    assert _extract_json('[{"a":1}]') == [{"a": 1}]


def test_extract_json_code_block():
    assert _extract_json('```\n[1,2,3]\n```') == [1, 2, 3]


def test_extract_json_embedded_in_prose():
    assert _extract_json('结果是 [{"x":true}] 完成') == [{"x": True}]


def test_extract_json_garbage():
    assert _extract_json("完全没有结构的内容") is None


def test_extract_json_object():
    assert _extract_json('{"a":1}') == {"a": 1}
