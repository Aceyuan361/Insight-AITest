# tests/ai/test_skills_batch.py
# -*- coding: utf-8 -*-
"""extract_test_points / write_cases_batch skill 测试。"""
from unittest.mock import MagicMock

from insight_aitest.modules.ai.backend.agent.skills import SKILLS, SkillContext


class FakeLLM:
    def __init__(self, response: str = ""):
        self._response = response
        self.calls = []
    def chat(self, messages, **kwargs):
        self.calls.append(messages)
        return self._response


def _make_ctx(llm_response: str = "") -> SkillContext:
    return SkillContext(
        llm=FakeLLM(llm_response),
        config=MagicMock(chat_model="fake-model"),
        retriever=MagicMock(),
        generator=MagicMock(),
        case_db=MagicMock(),
        project_id=1,
        version_id=2,
    )


def test_extract_test_points_uses_analyzer(monkeypatch):
    """_extract_test_points 统一走 Analyzer.analyze()（删除分叉 prompt 后）。

    旧测试直接喂 FakeLLM JSON；现在 skill 改为调 get_analyzer().analyze()，
    故 mock get_analyzer 返回 TestPoint 列表，验证序列化输出。
    """
    from insight_aitest.modules.testcase.backend.generator.analyzer import TestPoint
    from insight_aitest.modules.testcase.backend.persistence.models import CaseType, TestType

    fake_analyzer = MagicMock()
    fake_analyzer.analyze.return_value = [
        TestPoint(id="tp1", summary="正确账密登录", suggested_type=CaseType.FUNCTIONAL,
                  suggested_design=TestType.POSITIVE, rationale="登录正向"),
        TestPoint(id="tp2", summary="空密码登录", suggested_type=CaseType.FUNCTIONAL,
                  suggested_design=TestType.NEGATIVE, rationale="异常分支"),
    ]
    monkeypatch.setattr(
        "insight_aitest.modules.testcase.backend.deps.get_analyzer",
        lambda: fake_analyzer,
    )

    ctx = _make_ctx()
    skill = SKILLS["extract_test_points"]
    result = skill.execute({"query": "登录功能", "document_ids": [1]}, ctx)
    assert result["count"] == 2
    assert result["test_points"][0]["summary"] == "正确账密登录"
    # 字段统一为新结构（不应有旧字段）
    assert "suggested_type" in result["test_points"][0]
    assert "description" not in result["test_points"][0]
    fake_analyzer.analyze.assert_called_once_with("登录功能", document_ids=[1])


def test_extract_test_points_empty_on_no_points(monkeypatch):
    """Analyzer 返回空 → count=0 + 空 test_points（无 error 键，统一走 analyze）。"""
    fake_analyzer = MagicMock()
    fake_analyzer.analyze.return_value = []
    monkeypatch.setattr(
        "insight_aitest.modules.testcase.backend.deps.get_analyzer",
        lambda: fake_analyzer,
    )

    ctx = _make_ctx()
    skill = SKILLS["extract_test_points"]
    result = skill.execute({"query": "登录功能"}, ctx)
    assert result["count"] == 0
    assert result["test_points"] == []


def test_write_cases_batch_generates_all(tmp_path):
    """分批生成：每个测试点生成一条用例。"""
    from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase
    from insight_aitest.modules.testcase.backend.persistence.models import TestCase, CaseType, CaseStatus, CasePriority, TestType

    case_db = TestCaseDatabase(str(tmp_path / "tc.db"))

    def fake_generate(point, **kwargs):
        return TestCase(
            title=f"用例-{point}", type=CaseType.FUNCTIONAL, description="用例描述",
            priority=CasePriority.P1, status=CaseStatus.DRAFT, test_design=TestType.POSITIVE,
            preconditions="无", content={"steps": [{"no": 1, "action": "操作", "data": ""}], "expected": "预期"}, tags=[],
        )

    ctx = SkillContext(
        llm=FakeLLM(), config=MagicMock(chat_model="fake-model"),
        retriever=MagicMock(), generator=MagicMock(generate=fake_generate),
        case_db=case_db, project_id=1, version_id=2,
    )

    test_points = [
        {"id": "tp1", "description": "登录", "type_hint": "functional", "design_hint": "positive"},
        {"id": "tp2", "description": "登出", "type_hint": "functional", "design_hint": "positive"},
        {"id": "tp3", "description": "锁定", "type_hint": "functional", "design_hint": "negative"},
    ]
    skill = SKILLS["write_cases_batch"]
    result = skill.execute({"test_points": test_points, "task_id": 42}, ctx)

    assert result["generated"] == 3
    assert result["failed"] == 0
    assert len(result["case_ids"]) == 3
    assert result["batch_id"].startswith("batch-42-")
    cases = case_db.list_cases_by_batch(result["batch_id"])
    assert len(cases) == 3
    assert all(c.task_id == 42 for c in cases)
    # 质量自检后合格用例被标记为 ai:validated:（原 ai:batch: 被 update_case 覆盖）
    assert all(c.source.startswith("ai:validated:") for c in cases)


def test_write_cases_batch_skips_failed(tmp_path):
    """单个生成失败不中断，记录 failed。"""
    from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase
    from insight_aitest.modules.testcase.backend.persistence.models import TestCase, CaseType, CaseStatus, CasePriority

    case_db = TestCaseDatabase(str(tmp_path / "tc.db"))
    call_count = {"n": 0}

    def fake_generate(point, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("LLM 返回非法 content")
        return TestCase(
            title="用例", type=CaseType.FUNCTIONAL, description="",
            priority=CasePriority.P1, status=CaseStatus.DRAFT, test_design="positive",
            preconditions="", content={"steps": []}, tags=[],
        )

    ctx = SkillContext(
        llm=FakeLLM(), config=MagicMock(chat_model="fake"),
        retriever=MagicMock(), generator=MagicMock(generate=fake_generate),
        case_db=case_db, project_id=1, version_id=2,
    )
    skill = SKILLS["write_cases_batch"]
    result = skill.execute({
        "test_points": [
            {"id": "tp1", "description": "a", "type_hint": "functional", "design_hint": "positive"},
            {"id": "tp2", "description": "b", "type_hint": "functional", "design_hint": "positive"},
            {"id": "tp3", "description": "c", "type_hint": "functional", "design_hint": "positive"},
        ],
        "task_id": 7,
    }, ctx)
    assert result["generated"] == 2
    assert result["failed"] == 1
