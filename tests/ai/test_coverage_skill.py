# -*- coding: utf-8 -*-
"""需求覆盖度分析 skill 测试。"""

from unittest.mock import MagicMock
from insight_aitest.modules.testcase.backend.persistence.models import (
    CaseType, CaseStatus, CasePriority, TestType, TestCase,
)


def test_analyze_coverage_finds_missing_points(tmp_path, monkeypatch):
    """analyze_coverage 应识别未被用例覆盖的需求点。"""
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    import insight_aitest.modules.testcase.backend.deps as tc_deps
    import insight_aitest.modules.testcase.backend.persistence.database as tc_db_mod
    tc_deps._tc_db = tc_db_mod.TestCaseDatabase(str(tmp_path / "tc.db"))

    # 插入 1 条用例（只覆盖"登录"）
    case = TestCase(
        title="登录测试", type=CaseType.FUNCTIONAL, description="验证登录",
        priority=CasePriority.P2, status=CaseStatus.DRAFT, test_design=TestType.POSITIVE,
        preconditions="无", content={"steps": [], "expected": "成功"},
    )
    case.batch_id = "batch-cov-1"
    tc_deps._tc_db.create_case(case)

    # mock analyzer: 返回 2 个需求点（登录+注册）
    from insight_aitest.modules.testcase.backend.generator.analyzer import TestPoint
    def _fake_analyze(query, document_ids=None, project_id=None):
        return [
            TestPoint(id="tp1", summary="登录功能", suggested_type=CaseType.FUNCTIONAL, suggested_design=TestType.POSITIVE, rationale=""),
            TestPoint(id="tp2", summary="注册功能", suggested_type=CaseType.FUNCTIONAL, suggested_design=TestType.POSITIVE, rationale=""),
        ]
    monkeypatch.setattr(
        "insight_aitest.modules.testcase.backend.deps.get_analyzer",
        lambda: MagicMock(analyze=_fake_analyze),
    )

    # mock LLM: 匹配结果
    def _fake_chat(messages, **kwargs):
        return '[{"requirement_id": "tp1", "requirement_summary": "登录", "case_ids": [1], "match_reason": "标题匹配"}, {"requirement_id": "tp2", "requirement_summary": "注册", "case_ids": [], "match_reason": "无匹配"}]'
    mock_llm = MagicMock()
    mock_llm.chat = _fake_chat

    from insight_aitest.modules.ai.backend.agent.coverage import analyze_coverage
    from insight_aitest.modules.ai.backend.agent.skills import SkillContext
    from insight_aitest.platform.services.kb.retriever import NullRetriever
    config = MagicMock()
    config.chat_model = "test"
    ctx = SkillContext(
        llm=mock_llm, config=config,
        retriever=NullRetriever(), generator=MagicMock(), case_db=tc_deps._tc_db,
    )
    result = analyze_coverage("batch-cov-1", [1], ctx, supplement=False)
    assert result["coverage_rate"] == 0.5  # 2个需求点，1个被覆盖
    assert "注册功能" in result["missing_points"]


def test_analyze_coverage_with_supplement(tmp_path, monkeypatch):
    """analyze_coverage supplement=True 时应为遗漏需求点补生成用例。"""
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    import insight_aitest.modules.testcase.backend.deps as tc_deps
    import insight_aitest.modules.testcase.backend.persistence.database as tc_db_mod
    tc_deps._tc_db = tc_db_mod.TestCaseDatabase(str(tmp_path / "tc.db"))

    case = TestCase(
        title="登录测试", type=CaseType.FUNCTIONAL, description="验证登录",
        priority=CasePriority.P2, status=CaseStatus.DRAFT, test_design=TestType.POSITIVE,
        preconditions="无", content={"steps": [], "expected": "成功"},
    )
    case.batch_id = "batch-cov-2"
    tc_deps._tc_db.create_case(case)

    from insight_aitest.modules.testcase.backend.generator.analyzer import TestPoint
    def _fake_analyze(query, document_ids=None, project_id=None):
        return [
            TestPoint(id="tp1", summary="登录", suggested_type=CaseType.FUNCTIONAL, suggested_design=TestType.POSITIVE, rationale=""),
            TestPoint(id="tp2", summary="注册", suggested_type=CaseType.FUNCTIONAL, suggested_design=TestType.POSITIVE, rationale=""),
        ]
    monkeypatch.setattr(
        "insight_aitest.modules.testcase.backend.deps.get_analyzer",
        lambda: MagicMock(analyze=_fake_analyze),
    )

    def _fake_chat(messages, **kwargs):
        return '[{"requirement_id": "tp1", "requirement_summary": "登录", "case_ids": [1], "match_reason": "匹配"}, {"requirement_id": "tp2", "requirement_summary": "注册", "case_ids": [], "match_reason": "无匹配"}]'
    mock_llm = MagicMock()
    mock_llm.chat = _fake_chat

    # mock generator for supplement
    def _fake_generate(point, **kwargs):
        return TestCase(
            title=f"补充-{point.summary}", type=CaseType.FUNCTIONAL, description="补充用例",
            priority=CasePriority.P2, status=CaseStatus.DRAFT, test_design=TestType.POSITIVE,
            preconditions="无", content={"steps": [], "expected": "成功"},
        )
    mock_gen = MagicMock()
    mock_gen.generate = _fake_generate

    from insight_aitest.modules.ai.backend.agent.coverage import analyze_coverage
    from insight_aitest.modules.ai.backend.agent.skills import SkillContext
    from insight_aitest.platform.services.kb.retriever import NullRetriever
    config = MagicMock()
    config.chat_model = "test"
    ctx = SkillContext(
        llm=mock_llm, config=config,
        retriever=NullRetriever(), generator=mock_gen, case_db=tc_deps._tc_db,
    )
    result = analyze_coverage("batch-cov-2", [1], ctx, supplement=True)
    assert len(result["supplemented_case_ids"]) == 1  # 补充了1条
    assert result["coverage_rate"] == 0.5  # 补充前覆盖率
