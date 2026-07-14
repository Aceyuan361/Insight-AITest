# -*- coding: utf-8 -*-
"""Planner 两阶段策略引导测试。

验证 _STRATEGY_PROMPT 引导 LLM 产出的 extract_test_points / write_cases_batch
策略能被 _validate_plan 保留（不因 skill 校验被丢弃）。
"""
from __future__ import annotations

from insight_aitest.modules.ai.backend.agent.planner import Planner
from insight_aitest.platform.services.llm.config import LLMConfig


class _ScriptedLLM:
    """返回预设 JSON 的假 LLM。"""

    def __init__(self, raw: str):
        self._raw = raw
        self.calls: list[str] = []

    def chat(self, messages, **kwargs):
        self.calls.append(messages[0].get("content", "") if messages else "")
        return self._raw

    def stream_chat(self, messages, **kwargs):
        # thinking_level=off 时 planner 走 stream_chat，把 raw 整块吐出
        yield self._raw

    def stream_chat_raw(self, messages, thinking_level="off", **kwargs):
        yield ("content", self._raw)


_TWO_STAGE_STRATEGY_JSON = """[
  {
    "id": "E",
    "label": "批量生成用例",
    "description": "从需求文档提取测试点，确认范围后批量生成",
    "plan": [
      {"skill": "extract_test_points", "desc": "提取测试点", "params": {"query": "登录功能", "documents_text": "需求文档内容"}}
    ]
  }
]"""


def test_validate_plan_keeps_two_stage_skills():
    """_validate_plan 必须保留 extract_test_points / write_cases_batch step。

    这两个 skill 已在 SKILLS 注册表里，_validate_plan 只过滤未知 skill，
    不应丢弃它们。这是两阶段闭环的前提：planner 产出的策略能原样通过校验。
    """
    cfg = LLMConfig(llm_api_key="fake")
    planner = Planner(_ScriptedLLM("[]"), cfg)
    plan = planner._validate_plan([
        {"skill": "extract_test_points", "desc": "提取测试点",
         "params": {"query": "登录", "documents_text": "..."}},
        {"skill": "write_cases_batch", "desc": "批量生成",
         "params": {"test_points": [{"id": "tp1"}]}},
        {"skill": "nonexistent_skill", "desc": "应被过滤", "params": {}},
    ])
    skills = [s["skill"] for s in plan]
    assert "extract_test_points" in skills
    assert "write_cases_batch" in skills
    # 未知 skill 被过滤
    assert "nonexistent_skill" not in skills
    assert len(plan) == 2


def test_propose_strategies_accepts_two_stage_from_llm():
    """LLM 返回含 extract_test_points 的两阶段策略时，propose_strategies 保留它。

    策略 E 必须是单步 extract_test_points（阶段2 write_cases_batch 由前端确认后
    经 generate-batch 端点触发，不放进 plan —— 否则会跳过人工确认 HITL 环节）。
    """
    cfg = LLMConfig(llm_api_key="fake")
    planner = Planner(_ScriptedLLM(_TWO_STAGE_STRATEGY_JSON), cfg)
    strategies = planner.propose_strategies({"summary": "登录功能测试", "scope": ["登录"]})

    assert len(strategies) >= 1
    strat = strategies[0]
    assert strat["id"] == "E"
    # E 只含 extract_test_points 单步（阶段2 不在 plan 里）
    assert len(strat["plan"]) == 1
    assert strat["plan"][0]["skill"] == "extract_test_points"


def test_validate_plan_still_accepts_write_cases_batch():
    """write_cases_batch 本身仍在 SKILLS 注册表里，_validate_plan 接受它。

    它不进策略 plan（阶段2 走 generate-batch 端点构造），但 skill 本身合法。
    """
    cfg = LLMConfig(llm_api_key="fake")
    planner = Planner(_ScriptedLLM("[]"), cfg)
    plan = planner._validate_plan([
        {"skill": "write_cases_batch", "desc": "批量生成",
         "params": {"test_points": [{"id": "tp1"}]}},
    ])
    assert len(plan) == 1
    assert plan[0]["skill"] == "write_cases_batch"


def test_propose_strategies_stream_yields_result_with_strategies():
    """propose_strategies_stream 的 (result, data) 里 data 必须是策略列表。

    回归测试：tasks.py create_task_stream 的 _produce 回调依赖
    kind=="result" 时 data 为最终策略列表来回填 DB。若 stream 不 yield result
    或 data 为空，DB 里 strategies 会是空列表 → 前端卡在"待选择"无卡片。
    """
    cfg = LLMConfig(llm_api_key="fake")
    planner = Planner(_ScriptedLLM(_TWO_STAGE_STRATEGY_JSON), cfg)
    items = list(planner.propose_strategies_stream({"summary": "登录", "scope": ["登录"]}))
    result_items = [d for k, d in items if k == "result"]
    assert len(result_items) == 1, "stream 必须恰好 yield 一次 result"
    strategies = result_items[0]
    assert isinstance(strategies, list) and len(strategies) >= 1
    assert strategies[0]["plan"][0]["skill"] == "extract_test_points"


def test_understand_stream_yields_result_with_context():
    """understand_stream 的 (result, data) 里 data 必须是 context dict。

    同上：create_task_stream 依赖此回填 context 到 DB。
    """
    llm = _ScriptedLLM('{"summary": "登录功能", "scope": ["账密登录", "验证码登录"]}')
    cfg = LLMConfig(llm_api_key="fake")
    planner = Planner(llm, cfg)
    items = list(planner.understand_stream("测登录", [{"filename": "r.md", "content": "需求"}], "off"))
    result_items = [d for k, d in items if k == "result"]
    assert len(result_items) == 1
    ctx = result_items[0]
    assert ctx["summary"] == "登录功能"
    assert "账密登录" in ctx["scope"]
