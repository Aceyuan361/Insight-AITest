# tests/ai/test_fix_ui_case.py
# -*- coding: utf-8 -*-
"""fix_ui_case skill 测试。"""
from unittest.mock import MagicMock

from insight_aitest.modules.ai.backend.agent.skills import SKILLS, SkillContext
from insight_aitest.modules.testcase.backend.persistence.models import TestCase, CaseType, CaseStatus, CasePriority


class FakeLLM:
    def __init__(self, response: str = ""):
        self._response = response
    def chat(self, messages, **kwargs):
        return self._response


def _make_ctx(case, llm_response):
    case_db = MagicMock()
    case_db.get_case.return_value = case
    return SkillContext(
        llm=FakeLLM(llm_response), config=MagicMock(chat_model="fake"),
        retriever=MagicMock(), generator=MagicMock(), case_db=case_db,
        project_id=None, version_id=None,
    )


def _ui_case(content):
    return TestCase(
        title="UI用例", type=CaseType.UI, description="", priority=CasePriority.P1,
        status=CaseStatus.DRAFT, test_design="positive", preconditions="",
        content=content, tags=[], source="ai:agent",
    )


def test_fix_ui_case_success():
    original = _ui_case({"base_url": "https://x.com", "steps": [{"kind": "action", "action": "点击登录"}]})
    fixed_content = '{"base_url": "https://x.com", "steps": [{"kind": "action", "action": "点击登录按钮"}]}'
    ctx = _make_ctx(original, fixed_content)
    result = SKILLS["fix_ui_case"].execute({"case_id": 1, "analysis": {"root_cause": "元素定位不准"}}, ctx)
    assert result["fixed"] is True
    ctx.case_db.update_case.assert_called_once()
    _, kwargs = ctx.case_db.update_case.call_args
    assert kwargs["content"]["steps"][0]["action"] == "点击登录按钮"


def test_fix_ui_case_rejects_invalid_content():
    original = _ui_case({"base_url": "https://x.com", "steps": []})
    bad_content = '{"steps": []}'  # missing base_url
    ctx = _make_ctx(original, bad_content)
    result = SKILLS["fix_ui_case"].execute({"case_id": 1, "analysis": {}}, ctx)
    assert result["fixed"] is False
    ctx.case_db.update_case.assert_not_called()


def test_fix_ui_case_fallback_on_bad_llm():
    original = _ui_case({"base_url": "https://x.com", "steps": []})
    ctx = _make_ctx(original, "这不是 JSON")
    result = SKILLS["fix_ui_case"].execute({"case_id": 1, "analysis": {}}, ctx)
    assert result["fixed"] is False
    ctx.case_db.update_case.assert_not_called()


def test_fix_ui_case_registered():
    """fix_ui_case 注册进 SKILLS，进 catalog。"""
    assert "fix_ui_case" in SKILLS
    from insight_aitest.modules.ai.backend.agent.skills import get_skill_catalog
    assert "fix_ui_case" in get_skill_catalog()
