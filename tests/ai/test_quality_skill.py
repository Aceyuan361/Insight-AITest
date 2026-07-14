# -*- coding: utf-8 -*-
"""用例质量自检修复 skill 测试。"""

from unittest.mock import MagicMock
from insight_aitest.modules.testcase.backend.persistence.models import (
    CaseType, CaseStatus, CasePriority, TestType, TestCase,
)


def _make_case(title="测试用例", description="", preconditions="", content=None):
    """构造 TestCase（id 为 ORM 自增列 init=False，不可通过构造传入）。"""
    return TestCase(
        title=title, type=CaseType.FUNCTIONAL,
        description=description, priority=CasePriority.P2, status=CaseStatus.DRAFT,
        test_design=TestType.POSITIVE, preconditions=preconditions,
        content=content or {"steps": [{"no": 1, "action": "操作", "data": ""}], "expected": "预期"},
    )


def test_validate_case_detects_empty_description():
    """校验应检测出空 description。"""
    from insight_aitest.modules.ai.backend.agent.quality import validate_case
    case = _make_case(description="")
    issues = validate_case(case)
    assert "description_empty" in issues


def test_validate_case_detects_empty_preconditions():
    """校验应检测出空 preconditions。"""
    from insight_aitest.modules.ai.backend.agent.quality import validate_case
    case = _make_case(description="有描述", preconditions="")
    issues = validate_case(case)
    assert "preconditions_empty" in issues


def test_validate_case_passes_valid_case():
    """完整用例应无问题。"""
    from insight_aitest.modules.ai.backend.agent.quality import validate_case
    case = _make_case(
        description="验证登录",
        preconditions="无",
        content={"steps": [{"no": 1, "action": "输入", "data": ""}], "expected": "成功"},
    )
    issues = validate_case(case)
    assert len(issues) == 0


def test_validate_and_fix_cases_repairs_empty_description(tmp_path, monkeypatch):
    """validate_and_fix_cases 应修复空 description 用例。"""
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    import insight_aitest.modules.testcase.backend.deps as tc_deps
    import insight_aitest.modules.testcase.backend.persistence.database as tc_db_mod
    tc_deps._tc_db = tc_db_mod.TestCaseDatabase(str(tmp_path / "tc.db"))

    # 插入一条空 description 用例
    case = _make_case(description="")
    case.batch_id = "batch-test-1"
    case_id = tc_deps._tc_db.create_case(case)

    # mock generator：重试时返回有 description 的用例
    def _fake_generate(point, **kwargs):
        return TestCase(
            title=f"修复-{point.summary}", type=CaseType.FUNCTIONAL,
            description="修复后的描述", priority=CasePriority.P2, status=CaseStatus.DRAFT,
            test_design=TestType.POSITIVE, preconditions="无",
            content={"steps": [{"no": 1, "action": "操作", "data": ""}], "expected": "预期"},
        )
    mock_gen = MagicMock()
    mock_gen.generate = _fake_generate

    from insight_aitest.modules.ai.backend.agent.quality import validate_and_fix_cases
    from insight_aitest.modules.ai.backend.agent.skills import SkillContext
    from insight_aitest.platform.services.kb.retriever import NullRetriever
    config = MagicMock()
    config.chat_model = "test"
    ctx = SkillContext(
        llm=MagicMock(), config=config,
        retriever=NullRetriever(), generator=mock_gen, case_db=tc_deps._tc_db,
    )
    stats = validate_and_fix_cases("batch-test-1", [1], ctx)
    assert stats["total"] == 1
    assert stats["fixed"] == 1
    assert stats["invalid"] == 0
