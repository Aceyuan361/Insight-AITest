# -*- coding: utf-8 -*-
"""Agent execute_ui_case skill 测试：asyncio.run 桥接 + FakeAgent。

复用 tests/ui/test_executor.py 的 FakeAgent + _patch_launch 模式。
验证 skill 能把异步 UI 引擎桥接到同步签名，并返回 pass/fail。
"""
from __future__ import annotations

from unittest.mock import MagicMock

from insight_aitest.modules.ai.backend.agent.skills import (
    SKILLS,
    SkillContext,
    _execute_ui_case,
)
from insight_aitest.modules.testcase.backend.persistence.models import (
    CaseStatus,
    CaseType,
    TestCase,
    TestType,
)


# ===== FakeAgent + 浏览器桩（对齐 tests/ui/test_executor.py） =====


class FakeAgent:
    """预设每步返回的假 agent。async 方法对齐 pymidscene 0.3.0。"""

    def __init__(self, script):
        self.calls = []
        self.script = list(script)

    async def ai_action(self, prompt):
        self.calls.append(("ai_action", prompt))
        return self.script.pop(0) if self.script else "ok"

    async def ai_assert(self, prompt):
        self.calls.append(("ai_assert", prompt))
        ok = self.script.pop(0) if self.script else True
        return bool(ok)

    async def ai_query(self, schema):
        self.calls.append(("ai_query", schema))
        result = self.script.pop(0) if self.script else {}
        return {"data": result} if isinstance(result, dict) else result


def _factory(script):
    """返回忽略 page 的 FakeAgent 工厂。"""
    def factory(page):
        return FakeAgent(script)
    return factory


def _patch_launch(monkeypatch):
    """把 executor 的浏览器启动 monkeypatch 成 no-op。"""
    from insight_aitest.modules.ui.backend.engine import executor as exe

    class FakePage:
        async def goto(self, url):
            pass

    class FakeCtx:
        async def __aenter__(self):
            return FakePage()

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(exe, "_launch_browser", lambda headless=True, viewport=None, timeout=30000: FakeCtx())


BASE = "http://test.local"


def _make_ctx(tmp_path, case: TestCase, agent_factory) -> tuple[SkillContext, MagicMock]:
    """构造带 Mock ui_run_db + case_db 的 SkillContext。"""
    case_db = MagicMock()
    case_db.get_case.return_value = case
    case_db.update_result = MagicMock()

    ui_run_db = MagicMock()
    ui_run_db.create_run.return_value = 7

    ctx = SkillContext(
        llm=MagicMock(),
        config=MagicMock(chat_model="fake"),
        retriever=MagicMock(),
        generator=MagicMock(),
        case_db=case_db,
        project_id=None,
        version_id=None,
        ui_run_db=ui_run_db,
        ui_agent_factory=agent_factory,
    )
    return ctx, case_db


# ===== 测试 =====


def test_execute_ui_case_pass(tmp_path, monkeypatch):
    """UI 用例全步通过 → status=passed。"""
    _patch_launch(monkeypatch)
    case = TestCase(
        title="登录流程",
        type=CaseType.UI,
        status=CaseStatus.DRAFT,
        test_design=TestType.POSITIVE,
        content={
            "base_url": BASE,
            "steps": [
                {"kind": "action", "action": "点击登录按钮"},
                {"kind": "assert", "assert": "显示欢迎"},
            ],
        },
    )
    ctx, case_db = _make_ctx(tmp_path, case, _factory(["ok", True]))

    result = _execute_ui_case({"case_id": 1}, ctx)

    assert result["status"] == "passed"
    assert result["passed_steps"] == 2
    assert result["total_steps"] == 2
    assert result["run_id"] == 7
    assert result["case_id"] == 1
    assert result["failures"] == []
    case_db.update_result.assert_called_once()


def test_execute_ui_case_fail(tmp_path, monkeypatch):
    """UI 断言失败 → status=failed（不抛异常），failures 非空。"""
    _patch_launch(monkeypatch)
    case = TestCase(
        title="失败流程",
        type=CaseType.UI,
        status=CaseStatus.DRAFT,
        test_design=TestType.NEGATIVE,
        content={
            "base_url": BASE,
            "steps": [
                {"kind": "assert", "assert": "显示欢迎"},
            ],
        },
    )
    ctx, _ = _make_ctx(tmp_path, case, _factory([False]))  # assert 返回 False

    result = _execute_ui_case({"case_id": 2}, ctx)

    assert result["status"] == "failed"
    assert result["passed_steps"] == 0
    assert len(result["failures"]) == 1
    assert result["failures"][0]["kind"] == "assert"


def test_execute_ui_case_no_run_db(tmp_path, monkeypatch):
    """ui_run_db 未注入 → 抛 RuntimeError。"""
    _patch_launch(monkeypatch)
    case = TestCase(
        title="x", type=CaseType.UI, content={"base_url": BASE, "steps": [{"kind": "action", "action": "点x"}]}
    )
    ctx, _ = _make_ctx(tmp_path, case, _factory(["ok"]))
    ctx.ui_run_db = None
    try:
        _execute_ui_case({"case_id": 1}, ctx)
        assert False, "应抛 RuntimeError"
    except RuntimeError:
        pass


def test_execute_ui_case_missing_case(tmp_path, monkeypatch):
    """用例不存在 → 抛 ValueError。"""
    _patch_launch(monkeypatch)
    case = TestCase(title="x", type=CaseType.UI, content={"base_url": BASE, "steps": [{"kind": "action", "action": "点x"}]})
    ctx, case_db = _make_ctx(tmp_path, case, _factory(["ok"]))
    case_db.get_case.return_value = None
    try:
        _execute_ui_case({"case_id": 999}, ctx)
        assert False, "应抛 ValueError"
    except ValueError:
        pass


def test_execute_ui_case_registered():
    """execute_ui_case 注册进 SKILLS，进 catalog。"""
    assert "execute_ui_case" in SKILLS
    from insight_aitest.modules.ai.backend.agent.skills import get_skill_catalog
    assert "execute_ui_case" in get_skill_catalog()
