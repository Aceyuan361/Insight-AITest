# -*- coding: utf-8 -*-
"""核心执行引擎（spec E §4）。

execute(content, transport=None) → RunRecord。
顺序执行 steps，维护 ExecutionContext（累积变量），逐步：
  注入变量 → 发请求 → 解析响应 → 跑断言 → 提取变量。
前一步失败不中断后续步。status 优先级 error > failed > passed。
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

import httpx

from insight_aitest.modules.api.backend.engine.assertions import check_assertion
from insight_aitest.modules.api.backend.engine.variables import (
    UndefinedVariableError,
    extract_variables,
    inject_variables,
)
from insight_aitest.modules.api.backend.persistence.models import (
    RunRecord,
    RunStatus,
    StepResult,
)

DEFAULT_TIMEOUT = 30
MAX_RESPONSE_BODY_BYTES = 64_000
VERIFY_SSL = True


def _validate_content(content: dict) -> None:
    if not isinstance(content, dict):
        raise ValueError("用例 content 不是合法对象")
    if not content.get("base_url"):
        raise ValueError("用例 content 缺少 base_url")
    if not isinstance(content.get("steps"), list):
        raise ValueError("用例 content 缺少合法的 steps 数组")


def _truncate_body(body: Any) -> Any:
    """响应体超阈值截断（spec E §7）：防止巨响爆库。

    str: 按字符截断；dict/list: 序列化后超阈值则降级为截断的字符串（保留可读性）。
    """
    if isinstance(body, str):
        if len(body) > MAX_RESPONSE_BODY_BYTES:
            return body[:MAX_RESPONSE_BODY_BYTES] + "...[truncated]"
        return body
    if isinstance(body, (dict, list)):
        s = json.dumps(body, ensure_ascii=False)
        if len(s) > MAX_RESPONSE_BODY_BYTES:
            return s[:MAX_RESPONSE_BODY_BYTES] + "...[truncated]"
    return body


def execute(
    content: dict,
    *,
    transport: httpx.BaseTransport | None = None,
    case_id: int = 0,
    case_title: str = "",
    initial_vars: dict | None = None,
) -> RunRecord:
    """执行一条 API 用例。返回 RunRecord。

    transport: 可注入（测试用 MockTransport）；None 则默认 httpx.Client。
    initial_vars: context 变量初始值（环境变量 + setup 提取注入）；None=原行为。
    """
    _validate_content(content)
    base_url = content["base_url"]
    steps = content["steps"]

    started_at = datetime.now()
    t0 = time.monotonic()
    variables: dict[str, Any] = dict(initial_vars) if initial_vars else {}
    step_results: list[StepResult] = []
    has_error = False
    has_failed = False

    client_kw: dict[str, Any] = {"timeout": DEFAULT_TIMEOUT, "verify": VERIFY_SSL}
    if transport is not None:
        client_kw["transport"] = transport

    with httpx.Client(**client_kw) as client:
        for idx, step in enumerate(steps):
            sr = _run_step(client, base_url, step, idx, variables)
            step_results.append(sr)
            if sr.error is not None:
                has_error = True
            elif not sr.passed:
                has_failed = True
            # 提取成功的变量累积进 context
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
    )


def _run_step(
    client: httpx.Client, base_url: str, step: dict, idx: int, variables: dict[str, Any]
) -> StepResult:
    """执行单步。任何异常都不向上抛（记录为 error）。"""
    t0 = time.monotonic()
    method = str(step.get("method", "GET")).upper()
    raw_path = step.get("path", "")
    raw_headers = step.get("headers") or {}
    raw_body = step.get("body")
    assertions = step.get("assertions") or []
    extract_spec = step.get("extract") or {}

    def empty_result(err, req):
        return StepResult(
            step_index=idx,
            request=req,
            status_code=None,
            response_body=None,
            response_headers={},
            elapsed_ms=0,
            assertions=[],
            extracts={},
            error=err,
            passed=False,
        )

    # 1. 变量注入
    try:
        path = inject_variables(raw_path, variables)
        headers = inject_variables(raw_headers, variables)
        body = inject_variables(raw_body, variables)
    except UndefinedVariableError as e:
        return empty_result(
            str(e), {"method": method, "url": raw_path, "headers": raw_headers, "body": raw_body}
        )

    url = path if path.startswith("http") else base_url.rstrip("/") + "/" + path.lstrip("/")
    req_snapshot = {"method": method, "url": url, "headers": headers, "body": body}

    # 2. 发请求
    try:
        kw: dict[str, Any] = {}
        if body not in (None, "", {}):
            kw["json"] = body
        r = client.request(method, url, headers=headers, **kw)
        status_code = r.status_code
        resp_headers = dict(r.headers)
        raw_text = r.text
    except httpx.HTTPError as e:
        return empty_result(f"请求异常: {e}", req_snapshot)

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    # 3. 解析响应
    response_body: Any = raw_text
    try:
        response_body = json.loads(raw_text)
    except (ValueError, TypeError):
        pass  # 非 JSON，保留原始文本
    response_body = _truncate_body(response_body)

    # 4. 跑断言
    assertion_results = [
        check_assertion(
            a,
            status_code=status_code,
            headers=resp_headers,
            body=response_body,
            elapsed_ms=elapsed_ms,
        )
        for a in assertions
    ]
    passed = all(a["passed"] for a in assertion_results) if assertion_results else True

    # 5. 提取变量（提取失败 → 本步 error，但请求结果仍保留）
    extracts: dict[str, Any] = {}
    extract_err: str | None = None
    if extract_spec:
        try:
            extracts = extract_variables(extract_spec, response_body)
        except UndefinedVariableError as e:
            extract_err = str(e)

    error = extract_err  # 注入/网络错误已在前面 early-return
    return StepResult(
        step_index=idx,
        request=req_snapshot,
        status_code=status_code,
        response_body=response_body,
        response_headers=resp_headers,
        elapsed_ms=elapsed_ms,
        assertions=assertion_results,
        extracts=extracts,
        error=error,
        passed=(passed and error is None),
    )
