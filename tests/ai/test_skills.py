# -*- coding: utf-8 -*-
"""_extract_test_points / _write_cases_batch 统一 prompt 后的字段结构测试。

Task 1（用例生成统一）：_extract_test_points 改为调用 Analyzer.analyze()，
输出字段统一为 summary/suggested_type/suggested_design/rationale（不再有
description/type_hint/design_hint）。_write_cases_batch 同时兼容新旧两种结构。
"""
from __future__ import annotations

from unittest.mock import MagicMock

from insight_aitest.modules.ai.backend.agent.skills import SKILLS, SkillContext


class _FakeLLM:
    def __init__(self, response: str = ""):
        self._response = response
        self.calls: list = []

    def chat(self, messages, **kwargs):
        self.calls.append(messages)
        return self._response


def _make_ctx(llm_response: str = "") -> SkillContext:
    return SkillContext(
        llm=_FakeLLM(llm_response),
        config=MagicMock(chat_model="fake-model"),
        retriever=MagicMock(),
        generator=MagicMock(),
        case_db=MagicMock(),
        project_id=1,
        version_id=2,
    )


def _fake_points():
    """构造 Analyzer.analyze() 返回的 TestPoint 列表。"""
    from insight_aitest.modules.testcase.backend.generator.analyzer import TestPoint
    from insight_aitest.modules.testcase.backend.persistence.models import CaseType, TestType

    return [
        TestPoint(
            id="tp1", summary="正确账密登录", suggested_type=CaseType.FUNCTIONAL,
            suggested_design=TestType.POSITIVE, rationale="需求3.2 登录正向"),
        TestPoint(
            id="tp2", summary="空密码登录", suggested_type=CaseType.FUNCTIONAL,
            suggested_design=TestType.NEGATIVE, rationale="需求3.2 异常分支"),
    ]


# ===== _extract_test_points：统一走 Analyzer.analyze() =====


def test_extract_test_points_returns_unified_fields(monkeypatch):
    """_extract_test_points 通过 Analyzer.analyze() 提取，输出 summary/suggested_type/suggested_design/rationale。"""
    fake_analyzer = MagicMock()
    fake_analyzer.analyze.return_value = _fake_points()
    monkeypatch.setattr(
        "insight_aitest.modules.testcase.backend.deps.get_analyzer",
        lambda: fake_analyzer,
    )

    ctx = _make_ctx()
    skill = SKILLS["extract_test_points"]
    result = skill.execute({"query": "登录功能", "document_ids": [1, 2]}, ctx)

    assert result["count"] == 2
    # 验证 Analyzer.analyze 被正确调用（query + document_ids）
    fake_analyzer.analyze.assert_called_once_with("登录功能", document_ids=[1, 2])

    tp0 = result["test_points"][0]
    # 统一字段（不应再有 description/type_hint/design_hint）
    assert tp0["summary"] == "正确账密登录"
    assert tp0["suggested_type"] == "functional"
    assert tp0["suggested_design"] == "positive"
    assert "rationale" in tp0
    assert "description" not in tp0
    assert "type_hint" not in tp0
    assert "design_hint" not in tp0


def test_extract_test_points_passes_query_without_document_ids(monkeypatch):
    """无 document_ids 时 analyze 收到 document_ids=None。"""
    fake_analyzer = MagicMock()
    fake_analyzer.analyze.return_value = _fake_points()
    monkeypatch.setattr(
        "insight_aitest.modules.testcase.backend.deps.get_analyzer",
        lambda: fake_analyzer,
    )

    ctx = _make_ctx()
    skill = SKILLS["extract_test_points"]
    skill.execute({"query": "登录功能"}, ctx)

    fake_analyzer.analyze.assert_called_once_with("登录功能", document_ids=None)


def test_extract_test_points_empty(monkeypatch):
    """Analyzer 返回空 → count=0 + 空 test_points。"""
    fake_analyzer = MagicMock()
    fake_analyzer.analyze.return_value = []
    monkeypatch.setattr(
        "insight_aitest.modules.testcase.backend.deps.get_analyzer",
        lambda: fake_analyzer,
    )

    ctx = _make_ctx()
    skill = SKILLS["extract_test_points"]
    result = skill.execute({"query": "空需求"}, ctx)

    assert result["count"] == 0
    assert result["test_points"] == []


def test_extract_points_prompt_deleted():
    """_EXTRACT_POINTS_PROMPT 已删除（统一 prompt 源）。"""
    import insight_aitest.modules.ai.backend.agent.skills as skills_mod

    assert not hasattr(skills_mod, "_EXTRACT_POINTS_PROMPT")


# ===== _write_cases_batch：兼容新/旧字段结构 =====


def _fake_generate_factory():
    from insight_aitest.modules.testcase.backend.persistence.models import (
        CaseStatus, CasePriority, CaseType, TestCase, TestType,
    )

    def _fake_generate(point, **kwargs):
        return TestCase(
            title=f"用例-{getattr(point, 'summary', '')}", type=CaseType.FUNCTIONAL,
            description="", priority=CasePriority.P2, status=CaseStatus.DRAFT,
            test_design=TestType.POSITIVE, preconditions="",
            content={"steps": []}, tags=[],
        )

    return _fake_generate


def test_write_cases_batch_accepts_unified_fields(tmp_path):
    """write_cases_batch 接收新结构 summary/suggested_type/suggested_design/rationale。"""
    from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase

    case_db = TestCaseDatabase(str(tmp_path / "tc.db"))
    ctx = SkillContext(
        llm=_FakeLLM(), config=MagicMock(chat_model="fake-model"),
        retriever=MagicMock(),
        generator=MagicMock(generate=_fake_generate_factory()),
        case_db=case_db, project_id=1, version_id=2,
    )

    test_points = [
        {"id": "tp1", "summary": "登录", "suggested_type": "functional",
         "suggested_design": "positive", "rationale": "正向"},
        {"id": "tp2", "summary": "登出", "suggested_type": "functional",
         "suggested_design": "negative", "rationale": "异常"},
    ]
    skill = SKILLS["write_cases_batch"]
    result = skill.execute({"test_points": test_points, "task_id": 42}, ctx)

    assert result["generated"] == 2
    assert result["failed"] == 0


def test_write_cases_batch_backward_compat_old_fields(tmp_path):
    """write_cases_batch 仍兼容旧结构 description/type_hint/design_hint（历史数据）。"""
    from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase

    case_db = TestCaseDatabase(str(tmp_path / "tc.db"))
    ctx = SkillContext(
        llm=_FakeLLM(), config=MagicMock(chat_model="fake-model"),
        retriever=MagicMock(),
        generator=MagicMock(generate=_fake_generate_factory()),
        case_db=case_db, project_id=1, version_id=2,
    )

    test_points = [
        {"id": "tp1", "description": "登录", "type_hint": "functional", "design_hint": "positive"},
        {"id": "tp2", "description": "锁定", "type_hint": "functional", "design_hint": "negative"},
    ]
    skill = SKILLS["write_cases_batch"]
    result = skill.execute({"test_points": test_points, "task_id": 7}, ctx)

    assert result["generated"] == 2
    assert result["failed"] == 0
