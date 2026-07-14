# -*- coding: utf-8 -*-
"""执行引擎测试（FakeAgent，无浏览器/无 LLM，spec F §10）。"""
import pytest

from insight_aitest.modules.ui.backend.engine.executor import (
    _normalize_step, _validate_content, _classify_error, _parse_browser_config,
    VisionConfigError,
)


def test_validate_content_ok():
    _validate_content({"base_url": "http://x", "steps": [{"kind": "action", "action": "点击"}]})


def test_validate_content_missing_base_url():
    with pytest.raises(ValueError):
        _validate_content({"steps": [{"kind": "action", "action": "x"}]})


def test_validate_content_steps_not_list():
    with pytest.raises(ValueError):
        _validate_content({"base_url": "http://x", "steps": "nope"})


def test_validate_content_empty_steps():
    """空 steps 数组应报错（P0-2 边界值增强）。"""
    with pytest.raises(ValueError, match="没有任何步骤"):
        _validate_content({"base_url": "http://x", "steps": []})


def test_validate_content_invalid_url():
    """base_url 不是合法 URL 应报错（P0-2）。"""
    with pytest.raises(ValueError, match="合法 URL"):
        _validate_content({"base_url": "not-a-url", "steps": [{"kind": "action", "action": "x"}]})


def test_classify_error_timeout():
    import asyncio
    assert "超时" in _classify_error(asyncio.TimeoutError())


def test_classify_error_timeout_str():
    assert "超时" in _classify_error(RuntimeError("operation timed out after 30s"))


def test_classify_error_auth():
    assert "认证失败" in _classify_error(RuntimeError("invalid api_key"))


def test_classify_error_not_found():
    assert "元素未找到" in _classify_error(RuntimeError("element not found"))


def test_classify_error_rate_limit():
    assert "频率超限" in _classify_error(RuntimeError("rate limit exceeded"))


def test_classify_error_network():
    assert "网络连接" in _classify_error(RuntimeError("connection reset"))


def test_classify_error_generic():
    assert "步骤执行异常" in _classify_error(ValueError("something else"))


def test_parse_browser_config_defaults():
    cfg = _parse_browser_config(None)
    assert cfg["headless"] is True
    assert cfg["viewport_width"] == 1280
    assert cfg["viewport_height"] == 720
    assert cfg["timeout"] == 30000
    assert cfg["retry"] == 0
    assert cfg["screenshot_on_failure"] is True


def test_parse_browser_config_clamp():
    """超范围值应被钳制到合法区间。"""
    cfg = _parse_browser_config({"viewport_width": 100, "viewport_height": 99999, "timeout": 10, "retry": 99})
    assert cfg["viewport_width"] == 320  # min 320
    assert cfg["viewport_height"] == 3840  # max 3840
    assert cfg["timeout"] == 1000  # min 1000
    assert cfg["retry"] == 5  # max 5


def test_normalize_triple_to_sentence():
    """D 三元组 {action,target,value} 归一化成自然语言整句。"""
    step = {"kind": "action", "action": "click", "target": "登录按钮", "value": ""}
    out = _normalize_step(step)
    assert isinstance(out, dict)
    assert out["kind"] == "action"
    # 归一化后 prompt 是整句，含 target
    assert "登录按钮" in out["prompt"]


def test_normalize_keeps_explicit_prompt():
    """F 编辑器直接写的整句 kind+prompt 不被破坏。"""
    step = {"kind": "action", "action": "在用户名框输入 admin 后点登录"}
    out = _normalize_step(step)
    assert out["prompt"] == "在用户名框输入 admin 后点登录"


def test_normalize_extract_dict():
    """extract 步的 extract dict 保留。"""
    step = {"kind": "extract", "extract": {"username": "当前登录用户名"}}
    out = _normalize_step(step)
    assert out["kind"] == "extract"
    assert out["extract"] == {"username": "当前登录用户名"}


def test_normalize_assert_prompt():
    step = {"kind": "assert", "assert": "页面显示欢迎"}
    out = _normalize_step(step)
    assert out["kind"] == "assert"
    assert out["prompt"] == "页面显示欢迎"


from insight_aitest.modules.ui.backend.engine.executor import execute  # noqa: E402
from insight_aitest.modules.ui.backend.persistence.models import RunStatus  # noqa: E402


class FakeAgent:
    """预设每步返回的假 agent（spy + stub）。无浏览器/无 LLM。
    calls 记录每次调用的 (method, arg)，供 dispatch 断言。
    契约对齐 pymidscene 0.3.0 真实 API：ai_action / ai_assert / ai_query 均为
    async 方法（返回协程），ai_assert 返回 bool（True=通过），不抛 AssertionError。"""

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
        # 对齐 pymidscene 真实返回结构 {data, thought}，executor 取 .data
        result = self.script.pop(0) if self.script else {}
        return {"data": result} if isinstance(result, dict) else result


def _factory(script):
    """返回忽略 page 的 FakeAgent 工厂。"""
    def factory(page):
        return FakeAgent(script)
    return factory


def _patch_launch(monkeypatch):
    """把 executor 的浏览器启动 monkeypatch 成 no-op（返回假 page，异步上下文）。"""
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


async def test_pass_chain(monkeypatch):
    _patch_launch(monkeypatch)
    content = {"base_url": BASE, "steps": [
        {"kind": "action", "action": "点击登录按钮"},
        {"kind": "assert", "assert": "显示欢迎"},
        {"kind": "extract", "extract": {"username": "用户名"}},
    ]}
    run = await execute(content, agent_factory=_factory(["ok", True, {"username": "alice"}]))
    assert run.status == RunStatus.PASSED
    assert run.total_steps == 3
    assert run.passed_steps == 3
    assert run.base_url_used == BASE


async def test_three_kind_dispatch(monkeypatch):
    """action/assert/extract 各调对应 ai 方法（通过 run.steps 字段验证分发正确）。"""
    _patch_launch(monkeypatch)
    content = {"base_url": BASE, "steps": [
        {"kind": "action", "action": "点X"},
        {"kind": "assert", "assert": "显示Y"},
        {"kind": "extract", "extract": {"u": "用户"}},
    ]}
    run = await execute(content, agent_factory=_factory(["ok", True, {"u": "a"}]))
    # 通过 run.steps 的 kind + 返回字段验证分发正确
    assert [s.kind for s in run.steps] == ["action", "assert", "extract"]
    assert run.steps[0].action_log == "ok"      # action → ai_action 返回值
    assert run.steps[1].assert_passed is True    # assert → ai_assert 通过
    assert run.steps[2].extracts == {"u": "a"}   # extract → ai_query 取 .data


async def test_assertion_fail_marks_failed(monkeypatch):
    _patch_launch(monkeypatch)
    content = {"base_url": BASE, "steps": [
        {"kind": "assert", "assert": "显示欢迎"},
    ]}
    run = await execute(content, agent_factory=_factory([False]))
    assert run.status == RunStatus.FAILED
    assert run.passed_steps == 0
    assert run.steps[0].passed is False
    assert run.steps[0].assert_passed is False


async def test_error_does_not_short_circuit(monkeypatch):
    """action 步异常 → error，后续步照跑。"""
    _patch_launch(monkeypatch)

    class BoomAgent(FakeAgent):
        async def ai_action(self, prompt):
            self.calls.append(("ai_action", prompt))
            raise RuntimeError("LLM 挂了")

    def factory(page):
        return BoomAgent([])

    content = {"base_url": BASE, "steps": [
        {"kind": "action", "action": "会失败的步"},
        {"kind": "assert", "assert": "这步照跑"},
    ]}
    run = await execute(content, agent_factory=factory)
    assert run.status == RunStatus.ERROR  # 任一步 error → error
    assert run.steps[0].error is not None
    assert run.steps[1].passed is True  # 后续步照跑


async def test_extract_chains_to_next(monkeypatch):
    """extract 提取的变量注入后续 step 的 prompt（{{username}}）。"""
    _patch_launch(monkeypatch)
    content = {"base_url": BASE, "steps": [
        {"kind": "extract", "extract": {"username": "用户名"}},
        {"kind": "action", "action": "点击 {{username}} 的头像"},
    ]}
    run = await execute(content, agent_factory=_factory([{"username": "alice"}, "ok"]))
    # 第二步 prompt 应已注入变量
    assert run.steps[1].prompt == "点击 alice 的头像"


async def test_base_url_override(monkeypatch):
    _patch_launch(monkeypatch)
    content = {"base_url": BASE, "steps": [
        {"kind": "action", "action": "x"}]}
    run = await execute(content, agent_factory=_factory(["ok"]),
                        base_url_override="http://staging.local")
    assert run.base_url_used == "http://staging.local"


async def test_invalid_schema_raises(monkeypatch):
    _patch_launch(monkeypatch)
    # _validate_content 在协程体内同步抛 ValueError（agent_factory=None 会触发真浏览器，
    # 但校验先于浏览器启动，故校验失败不会启动浏览器）
    with pytest.raises(ValueError):
        await execute({"no_base_url": True, "steps": [{"kind": "action", "action": "x"}]},
                      agent_factory=_factory([]))
    with pytest.raises(ValueError):
        await execute({"base_url": BASE, "steps": "nope"},
                      agent_factory=_factory([]))


async def test_empty_steps_raises(monkeypatch):
    """空 steps 数组应报错。"""
    _patch_launch(monkeypatch)
    with pytest.raises(ValueError, match="没有任何步骤"):
        await execute({"base_url": BASE, "steps": []}, agent_factory=_factory([]))


async def test_empty_prompt_action_step(monkeypatch):
    """action 步 prompt 为空应标记为 error（不阻断，但不 passed）。"""
    _patch_launch(monkeypatch)
    content = {"base_url": BASE, "steps": [
        {"kind": "action", "action": ""},  # 空 prompt
    ]}
    run = await execute(content, agent_factory=_factory(["ok"]))
    assert run.status == RunStatus.ERROR
    assert run.steps[0].error is not None
    assert "为空" in run.steps[0].error


async def test_retry_on_failure(monkeypatch):
    """retry=1 时失败步重试一次。"""
    _patch_launch(monkeypatch)
    call_count = [0]

    class RetryAgent(FakeAgent):
        async def ai_action(self, prompt):
            call_count[0] += 1
            if call_count[0] < 2:
                raise RuntimeError("transient")
            return "ok after retry"

    def factory(page):
        return RetryAgent([])

    content = {"base_url": BASE, "steps": [
        {"kind": "action", "action": "点X"},
    ]}
    run = await execute(content, agent_factory=factory, browser_config={"retry": 1})
    assert run.status == RunStatus.PASSED
    assert call_count[0] == 2  # 第一次失败 + 重试成功


async def test_browser_config_passed(monkeypatch):
    """browser_config 应传到 _launch_browser。"""
    _patch_launch(monkeypatch)
    captured = {}

    from insight_aitest.modules.ui.backend.engine import executor as exe

    class FakePage:
        async def goto(self, url):
            pass

    class FakeCtx:
        async def __aenter__(self):
            return FakePage()

        async def __aexit__(self, *a):
            return False

    def capture_launch(headless=True, viewport=None, timeout=30000):
        captured["headless"] = headless
        captured["viewport"] = viewport
        captured["timeout"] = timeout
        return FakeCtx()

    monkeypatch.setattr(exe, "_launch_browser", capture_launch)

    content = {"base_url": BASE, "steps": [{"kind": "action", "action": "x"}]}
    await execute(content, agent_factory=_factory(["ok"]),
                  browser_config={"headless": False, "viewport_width": 1920, "viewport_height": 1080, "timeout": 60000})
    assert captured["headless"] is False
    assert captured["viewport"] == {"width": 1920, "height": 1080}
    assert captured["timeout"] == 60000


def test_vision_config_error_is_exception():
    """VisionConfigError 应是 Exception 子类。"""
    assert issubclass(VisionConfigError, Exception)
    e = VisionConfigError("test")
    assert "test" in str(e)
