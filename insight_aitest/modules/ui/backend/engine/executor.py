# -*- coding: utf-8 -*-
"""UI 执行引擎（spec F §3/§4）。

execute(content, agent_factory=) → RunRecord。
顺序执行 steps，维护 context（累积变量），逐步：
  归一化（三元组→整句）→ 注入变量 → 调对应 ai 方法 → 记 UIStepResult。
前一步失败不中断后续步。status 优先级 error > failed > passed。

agent_factory(page) 是可测注入点（对应 E 的 transport=）：
  生产传真 PlaywrightAgent（pymidscene 0.3.0：ai_action / ai_assert / ai_query），
  测试传返回 FakeAgent 的工厂（忽略 page）。
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime
from typing import Any, Callable
from urllib.parse import urlparse

from insight_aitest.modules.ui.backend.persistence.models import (
    RunRecord,
    RunStatus,
    UIStepResult,
)

# 复用 E 的变量注入（{{var}} 占位符替换，避免重复造轮子）
from insight_aitest.modules.api.backend.engine.variables import (
    UndefinedVariableError,
    inject_variables,
)

SCREENSHOT_DIR = os.path.expanduser("~/.insight_eye/ui_screenshots")


class VisionConfigError(Exception):
    """视觉模型未正确配置（API key 或模型名为空）。"""


def _resolve_vision_config() -> dict:
    """解析最终生效的视觉模型配置。

    优先级：UI 专用配置（非空字段）→ 全局 vision_model → 全局 chat_model。
    返回 {"base_url", "api_key", "model"}，每个字段独立回退（粒度到字段级）。
    """
    from insight_aitest.platform.services.kb.deps import get_llm_config

    cfg = get_llm_config()
    ui = cfg.ui_vision_config or {}

    return {
        "base_url": (ui.get("base_url") or "").strip() or cfg.llm_base_url,
        "api_key": (ui.get("api_key") or "").strip() or cfg.llm_api_key,
        "model": (ui.get("model") or "").strip() or (cfg.vision_model or "").strip() or cfg.chat_model,
    }


def _check_llm_config() -> None:
    """前置校验：视觉模型配置是否就绪。不通过抛 VisionConfigError。

    仅检查配置字段非空（不发连通性请求），避免给用户底层 pymidscene 报错。
    """
    resolved = _resolve_vision_config()
    if not resolved["api_key"]:
        raise VisionConfigError(
            "视觉模型未配置：请在「UI 自动化 → 设置」中填写 API Key。"
            "UI 自动化需要多模态视觉模型（如 gpt-4o）来分析页面截图。"
        )
    if not resolved["model"]:
        raise VisionConfigError(
            "视觉模型未配置：请在「UI 自动化 → 设置」中配置模型名称（如 gpt-4o）。"
            "UI 自动化需要多模态视觉模型来分析页面截图。"
        )


def _validate_content(content: dict) -> None:
    if not isinstance(content, dict):
        raise ValueError("用例 content 不是合法对象")
    base_url = content.get("base_url")
    if not base_url or not isinstance(base_url, str):
        raise ValueError("用例 content 缺少 base_url")
    # 校验 base_url 是合法 URL（含 scheme）
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"base_url 不是合法 URL（需含 http:// 或 https://）: {base_url}")
    steps = content.get("steps")
    if not isinstance(steps, list):
        raise ValueError("用例 content 缺少合法的 steps 数组")
    if len(steps) == 0:
        raise ValueError("用例没有任何步骤，请先添加至少一个操作步骤")


def _normalize_step(step: dict) -> dict:
    """把 D 的三元组 {action,target,value} 归一化为 {kind, prompt/extract/...}。

    - D 三元组：{"action":"click","target":"登录按钮","value":""} → prompt 整句
    - F 整句：{"kind":"action","action":"..."} → prompt 保留原句
    - 三元组无 kind 时默认 kind=action
    """
    kind = step.get("kind", "action")
    out: dict[str, Any] = {"kind": kind}

    if kind == "assert":
        # assert 用 "assert" 字段 或 target 拼接
        prompt = step.get("assert") or step.get("target") or ""
        out["prompt"] = prompt
        return out

    if kind == "extract":
        # extract 保留 dict（自然语言描述，非 JSONPath）
        out["extract"] = step.get("extract") or {}
        out["prompt"] = step.get("prompt", "")
        return out

    # action：优先用已写好的整句（action 字段含完整句），否则三元组拼接
    action = step.get("action", "")
    target = step.get("target", "")
    value = step.get("value", "")
    # 启发式：三元组模式（有 target 或 value）→ 拼接；纯整句 → 直接用
    if target or value:
        parts = [p for p in [action, target, value] if p]
        out["prompt"] = " ".join(parts)
    else:
        out["prompt"] = action
    return out


def _classify_error(e: Exception) -> str:
    """把底层异常分类为用户可读的中文错误消息。"""
    msg = str(e).lower()
    if isinstance(e, asyncio.TimeoutError) or "timeout" in msg or "timed out" in msg:
        return f"操作超时（模型响应或页面加载）: {e}"
    if "api_key" in msg or "apikey" in msg or " 401" in msg or " 403" in msg or "unauthorized" in msg or "forbidden" in msg:
        return f"AI 模型认证失败，请检查 API Key 配置: {e}"
    if "not found" in msg or "找不到" in msg or "无法定位" in msg or "no element" in msg:
        return f"目标元素未找到: {e}"
    if "rate limit" in msg or " 429" in msg or "quota" in msg:
        return f"AI 模型请求频率超限，请稍后重试: {e}"
    if "connection" in msg or "network" in msg or "econnreset" in msg or "enotfound" in msg:
        return f"网络连接异常: {e}"
    return f"步骤执行异常: {e}"


def _parse_browser_config(config: dict | None) -> dict:
    """解析并校验浏览器执行配置，返回带默认值的 dict。"""
    cfg = config or {}
    return {
        "headless": bool(cfg.get("headless", True)),
        "viewport_width": max(320, min(3840, int(cfg.get("viewport_width", 1280)))),
        "viewport_height": max(240, min(3840, int(cfg.get("viewport_height", 720)))),
        "timeout": max(1000, min(300000, int(cfg.get("timeout", 30000)))),
        "retry": max(0, min(5, int(cfg.get("retry", 0)))),
        "screenshot_on_failure": bool(cfg.get("screenshot_on_failure", True)),
    }


def _launch_browser(headless: bool = True, viewport: dict | None = None, timeout: int = 30000):
    """启动真 Playwright 浏览器，返回异步上下文管理器（yield page）。
    测试 monkeypatch 替换为 no-op。生产用 async_playwright（pymidscene 的
    PlaywrightAgent 是 async API，必须用 async_playwright 配合）。

    viewport: {"width": int, "height": int}，None 用默认值。
    timeout: 导航超时（ms）。
    """
    from playwright.async_api import async_playwright

    vp = viewport or {"width": 1280, "height": 720}

    class _BrowserCtx:
        def __init__(self):
            self._pw = None

        async def __aenter__(self):
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(headless=headless)
            self._page = await self._browser.new_page(viewport=vp)
            self._page.set_default_timeout(timeout)
            return self._page

        async def __aexit__(self, *a):
            try:
                if self._browser:
                    await self._browser.close()
            finally:
                if self._pw:
                    await self._pw.stop()
            return False

    return _BrowserCtx()


def _default_agent_factory():
    """生产 agent 工厂：用真 PlaywrightAgent + LLMConfig。
    PyMidscene 的 model_config 用 MIDSCENE_* 环境变量风格的键（已验证 pymidscene 0.3.0）。

    优先使用 UI 专用视觉模型配置（ui_vision_config），空字段回退全局。"""
    resolved = _resolve_vision_config()
    model_config = {
        "MIDSCENE_MODEL_NAME": resolved["model"],
        "MIDSCENE_MODEL_API_KEY": resolved["api_key"],
        "MIDSCENE_MODEL_BASE_URL": resolved["base_url"],
    }

    def factory(page):
        from pymidscene import PlaywrightAgent  # 已验证路径：pymidscene.PlaywrightAgent

        return PlaywrightAgent(page, model_config=model_config)

    return factory


async def execute(
    content: dict,
    *,
    agent_factory: Callable | None = None,
    case_id: int = 0,
    case_title: str = "",
    base_url_override: str | None = None,
    browser_config: dict | None = None,
) -> RunRecord:
    """执行一条 UI 用例。返回 RunRecord。协程——调用方需 await。

    agent_factory(page): 可注入（测试传 FakeAgent 工厂）；None 用真 Midscene。
    base_url_override: 覆盖 content 的 base_url（轻量环境切换）。
    browser_config: 浏览器执行配置（headless/viewport/timeout/retry/screenshot_on_failure）。

    注：pymidscene PlaywrightAgent 是 async API，故 execute 为协程，
    浏览器用 async_playwright（与 agent 的 await 调用匹配）。
    """
    _validate_content(content)
    base_url = base_url_override or content["base_url"]
    steps = content["steps"]

    # 前置校验：视觉模型配置是否就绪（仅在使用真 agent 时校验）
    if agent_factory is None:
        _check_llm_config()
        agent_factory = _default_agent_factory()

    bc = _parse_browser_config(browser_config)

    started_at = datetime.now()
    t0 = time.monotonic()
    variables: dict[str, Any] = {}
    step_results: list[UIStepResult] = []
    has_error = False
    has_failed = False

    async with _launch_browser(
        headless=bc["headless"],
        viewport={"width": bc["viewport_width"], "height": bc["viewport_height"]},
        timeout=bc["timeout"],
    ) as page:
        await page.goto(base_url)
        agent = agent_factory(page)
        for idx, raw_step in enumerate(steps):
            sr = await _run_step(
                agent, raw_step, idx, variables,
                run_case_id=case_id,
                retry=bc["retry"],
                screenshot_on_failure=bc["screenshot_on_failure"],
            )
            step_results.append(sr)
            if sr.error is not None:
                has_error = True
            elif not sr.passed:
                has_failed = True
            variables.update(sr.extracts)

    finished_at = datetime.now()
    duration_ms = int((time.monotonic() - t0) * 1000)
    passed_steps = sum(1 for s in step_results if s.passed)

    if has_error:
        status = RunStatus.ERROR
    elif has_failed:
        status = RunStatus.FAILED
    else:
        status = RunStatus.PASSED

    return RunRecord(
        id=None,
        case_id=case_id,
        case_title=case_title,
        case_snapshot=dict(content),
        status=status,
        total_steps=len(step_results),
        passed_steps=passed_steps,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        steps=step_results,
        base_url_used=base_url,
    )


async def _run_step(
    agent, raw_step: dict, idx: int, variables: dict[str, Any],
    run_case_id: int = 0, retry: int = 0, screenshot_on_failure: bool = True,
) -> UIStepResult:
    """执行单步（协程）。任何异常都不向上抛（记录为 error）。

    retry: 失败时重试次数（0=不重试）。每次重试间隔 1s。
    screenshot_on_failure: 失败步是否截图。
    """
    t0 = time.monotonic()
    norm = _normalize_step(raw_step)
    kind = norm["kind"]

    # 变量注入到 prompt（仅 prompt，extract schema 不注入——是自然语言非 JSONPath）
    try:
        prompt = inject_variables(norm.get("prompt", ""), variables) if norm.get("prompt") else ""
        extract_schema = norm.get("extract", {})
    except UndefinedVariableError as e:
        return _err_step(idx, kind, str(norm.get("prompt", "")), str(e))

    # 空 prompt 警告（不阻断执行，但标记）
    if not prompt and kind != "extract":
        return _err_step(idx, kind, "", "步骤操作描述为空，请填写自然语言操作指令")

    screenshot: str | None = None
    action_log: str | None = None
    assert_passed: bool | None = None
    extracts: dict = {}
    error: str | None = None

    for attempt in range(retry + 1):
        try:
            error = None
            if kind == "action":
                action_log = await agent.ai_action(prompt)
            elif kind == "assert":
                # pymidscene 0.3.0：ai_assert 返回 bool（True=断言通过），不抛 AssertionError
                assert_passed = bool(await agent.ai_assert(prompt))
            elif kind == "extract":
                result = await agent.ai_query(extract_schema)
                # pymidscene ai_query 返回 {data: {...}, thought: "..."}，取 data
                extracts = result.get("data", result) if isinstance(result, dict) else {}
            else:
                error = f"未知 step kind: {kind}"
            break  # 成功则跳出重试循环
        except Exception as e:
            if attempt < retry:
                await asyncio.sleep(1)  # 重试间隔
            else:
                error = _classify_error(e)

    # 失败步截图（生产路径，测试 FakeAgent 不截图）
    if screenshot_on_failure and (error is not None or assert_passed is False):
        screenshot = await _try_screenshot(agent, run_case_id, idx)

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    passed = error is None and (kind != "assert" or assert_passed is not False)

    return UIStepResult(
        step_index=idx,
        kind=kind,
        prompt=prompt,
        screenshot=screenshot,
        action_log=action_log,
        assert_passed=assert_passed,
        extracts=extracts,
        elapsed_ms=elapsed_ms,
        error=error,
        passed=passed,
    )


def _err_step(idx, kind, prompt, err) -> UIStepResult:
    return UIStepResult(
        step_index=idx,
        kind=kind,
        prompt=prompt,
        screenshot=None,
        action_log=None,
        assert_passed=None,
        extracts={},
        elapsed_ms=0,
        error=err,
        passed=False,
    )


async def _try_screenshot(agent, run_case_id: int, idx: int) -> str | None:
    """尝试截图（生产路径，协程）。FakeAgent 无截图能力，返回 None。"""
    try:
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        path = os.path.join(SCREENSHOT_DIR, f"case{run_case_id}-step{idx}.png")
        # 真 agent 持有的 page 有 screenshot；优先用 agent.page，回退 agent 暴露的
        page = getattr(agent, "page", None) or getattr(agent, "_page", None)
        if page is not None and hasattr(page, "screenshot"):
            await page.screenshot(path=path)
            return path
    except Exception:
        pass
    return None
