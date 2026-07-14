# -*- coding: utf-8 -*-
"""生成器质量防御测试：description/preconditions 空串回退。"""

from unittest.mock import MagicMock
from insight_aitest.modules.testcase.backend.generator.generator import Generator
from insight_aitest.modules.testcase.backend.generator.analyzer import TestPoint
from insight_aitest.modules.testcase.backend.persistence.models import CaseType, TestType


class _FakeLLM:
    def chat(self, messages, **kwargs):
        # 返回缺 description 的 JSON
        return '{"title":"登录测试","preconditions":"","content":{"steps":[{"no":1,"action":"输入","data":""}],"expected":"登录成功"}}'


def _gen():
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    config = MagicMock()
    config.chat_model = "test"
    config.vector_enabled = False
    return Generator(retriever, _FakeLLM(), config)


def test_description_falls_back_to_summary_when_empty():
    """LLM 返回空 description 时应回退到 point.summary。"""
    gen = _gen()
    point = TestPoint(id="tp1", summary="验证用户登录功能", suggested_type=CaseType.FUNCTIONAL, suggested_design=TestType.POSITIVE, rationale="")
    case = gen.generate(point)
    assert case.description == "验证用户登录功能"  # 回退到 summary 而非空串


def test_description_nonempty_when_llm_provides_it():
    """LLM 返回非空 description 时应直接使用。"""
    class _FakeLLM2:
        def chat(self, messages, **kwargs):
            return '{"title":"登录","description":"验证登录流程","preconditions":"无","content":{"steps":[{"no":1,"action":"输入","data":""}],"expected":"成功"}}'
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    config = MagicMock()
    config.chat_model = "test"
    config.vector_enabled = False
    gen = Generator(retriever, _FakeLLM2(), config)
    point = TestPoint(id="tp1", summary="登录", suggested_type=CaseType.FUNCTIONAL, suggested_design=TestType.POSITIVE, rationale="")
    case = gen.generate(point)
    assert case.description == "验证登录流程"


def test_preconditions_falls_back_when_empty():
    """LLM 返回空 preconditions 时应回退到'无'。"""
    gen = _gen()
    point = TestPoint(id="tp1", summary="测试", suggested_type=CaseType.FUNCTIONAL, suggested_design=TestType.POSITIVE, rationale="")
    case = gen.generate(point)
    assert case.preconditions == "无"
