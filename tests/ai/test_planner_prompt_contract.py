# -*- coding: utf-8 -*-
"""Planner prompt 契约回归测试。

验证 _STRATEGY_PROMPT 里两阶段生成的引导文本不被意外删除/修改。
这些引导是 LLM 产出 extract_test_points 策略的前提，改 prompt 时容易误删。
"""
from __future__ import annotations

from insight_aitest.modules.ai.backend.agent.planner import _STRATEGY_PROMPT


def test_strategy_prompt_mentions_extract_test_points():
    """_STRATEGY_PROMPT 必须提到 extract_test_points（LLM 才知道有这个能力）。"""
    assert "extract_test_points" in _STRATEGY_PROMPT


def test_strategy_prompt_mentions_write_cases_batch():
    """_STRATEGY_PROMPT 必须提到 write_cases_batch（两阶段流程的第二步）。"""
    assert "write_cases_batch" in _STRATEGY_PROMPT


def test_strategy_prompt_has_two_stage_archetype():
    """_STRATEGY_PROMPT 必须有批量生成用例的两阶段策略原型（LLM 才会产出该策略）。

    原型必须强调"上传文档时此项为首选"——否则 LLM 可能跳过 extract_test_points
    直接用多步 write_functional_case，导致 HITL 环节缺失。
    """
    assert "批量生成" in _STRATEGY_PROMPT
    assert "首选" in _STRATEGY_PROMPT, "prompt 必须强调 extract_test_points 策略为首选"


def test_strategy_prompt_enforces_single_step_plan_for_extract():
    """C2 回归：prompt 必须说明策略 plan 只放 extract_test_points 一步。

    若把 write_cases_batch 也放进 plan，会跳过人工确认 HITL 环节。
    """
    # 关键约束文本：提示 LLM 不要把 write_cases_batch 放进 plan
    assert "只放 extract_test_points" in _STRATEGY_PROMPT or "不要把 write_cases_batch" in _STRATEGY_PROMPT, \
        "prompt 必须明确约束：策略 plan 只含 extract_test_points 单步（避免跳过 HITL）"


def test_strategy_prompt_mentions_documents_text_param():
    """extract_test_points 的 documents_text 参数必须被 prompt 提及。

    否则 LLM 产出策略时不知道把需求原文传给 documents_text。
    """
    assert "documents_text" in _STRATEGY_PROMPT
