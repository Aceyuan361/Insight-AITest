# -*- coding: utf-8 -*-
"""套件执行引擎（spec E.1 §3）。

execute_suite(suite, cases_provider, run_saver, transport, environment, on_case_done) → result dict。
流程：setup（注入环境变量）→ 顺序跑 cases（遇错不中断）→ teardown。
变量优先级：case step 提取 > setup 提取 > 环境变量。

setup/teardown 的 step path 若为相对路径，用环境或首条 case 的 base_url 拼接。
"""

from __future__ import annotations

import copy
from typing import Any, Callable

import httpx

from insight_aitest.modules.api.backend.engine.executor import _run_step, execute
from insight_aitest.modules.api.backend.persistence.models import RunRecord, RunStatus
from insight_aitest.modules.api.backend.persistence.suite_models import SuiteRunStatus


def execute_suite(
    *,
    suite: dict,
    cases_provider: Callable[[int], dict | None],
    run_saver: Callable[[RunRecord], int],
    transport: httpx.BaseTransport | None,
    environment: Any | None,
    on_case_done: Callable[[int, int], None] | None = None,
) -> dict:
    """执行套件。返回 {status, done, case_run_ids, setup_status, error}。

    - suite: {id, name, case_ids, setup, teardown}
    - cases_provider(case_id) → {title, content} | None（None=case 不存在）
    - run_saver(run) → run_id（落库 + 回填 D 由调用方做）
    - environment: Environment | None
    - on_case_done(done_count, run_id): 每条 case 跑完后的进度回调（可选）
    """
    client_kw: dict[str, Any] = {"timeout": 30, "verify": True}
    if transport is not None:
        client_kw["transport"] = transport

    case_run_ids: list[int] = []
    run_statuses: list[RunStatus] = []
    errors: list[str] = []

    # 1. 基础 context（环境变量在底）
    context: dict[str, Any] = {}
    if environment is not None:
        context.update(environment.variables or {})

    # setup/teardown 的 base_url：优先环境，否则取首条 case 的 base_url
    setup_base_url = environment.base_url if environment is not None else None

    with httpx.Client(**client_kw) as client:
        # 2. SETUP
        setup_status: str | None = None
        if suite.get("setup"):
            base = setup_base_url or _first_case_base_url(suite["case_ids"], cases_provider)
            setup_status, setup_extracts = _run_steps(client, suite["setup"], context, base)
            if setup_status != "passed":
                return {
                    "status": SuiteRunStatus.FAILED,
                    "done": 0,
                    "case_run_ids": [],
                    "setup_status": setup_status,
                    "error": "setup 失败，未执行 case",
                }
            context.update(setup_extracts)  # setup 提取覆盖环境变量

        # 3. CASES（顺序，遇错不中断）
        done = 0
        for cid in suite["case_ids"]:
            case = cases_provider(cid)
            if case is None:
                errors.append(f"case {cid} 不存在，已跳过")
                continue
            content = copy.deepcopy(case["content"])
            if environment is not None:
                content["base_url"] = environment.base_url
            run = execute(
                content,
                transport=transport,
                case_id=cid,
                case_title=case.get("title", ""),
                initial_vars=context,
            )
            run_statuses.append(run.status)
            run_id = run_saver(run)
            case_run_ids.append(run_id)
            done += 1
            if on_case_done:
                on_case_done(done, run_id)

        # 4. TEARDOWN（失败不影响结果）
        if suite.get("teardown"):
            base = setup_base_url or _first_case_base_url(suite["case_ids"], cases_provider)
            _run_steps(client, suite["teardown"], context, base)

    has_non_pass = any(s != RunStatus.PASSED for s in run_statuses)
    status = SuiteRunStatus.FAILED if has_non_pass else SuiteRunStatus.COMPLETED
    return {
        "status": status,
        "done": done,
        "case_run_ids": case_run_ids,
        "setup_status": setup_status,
        "error": "; ".join(errors) if errors else None,
    }


def _first_case_base_url(case_ids: list[int], cases_provider: Callable[[int], dict | None]) -> str:
    """从第一条存在的 case 取 base_url（setup/teardown 相对路径拼接用）。"""
    for cid in case_ids:
        case = cases_provider(cid)
        if case and case.get("content", {}).get("base_url"):
            return case["content"]["base_url"]
    return ""


def _run_steps(
    client: httpx.Client, steps: list[dict], variables: dict[str, Any], base_url: str = ""
) -> tuple[str, dict]:
    """跑一组 steps（setup/teardown），返回 (status, extracts)。

    status: passed | failed | error。extracts: 累积的提取变量。
    注：_run_step 签名是 (client, base_url, step, idx, variables)。step path 若为
    绝对路径（以 http 开头）则忽略 base_url；相对路径用 base_url 拼接。
    """
    vars_ctx = dict(variables)
    extracts: dict[str, Any] = {}
    has_error = False
    has_failed = False
    for idx, step in enumerate(steps):
        sr = _run_step(client, base_url, step, idx, vars_ctx)
        if sr.error is not None:
            has_error = True
        elif not sr.passed:
            has_failed = True
        extracts.update(sr.extracts)
        vars_ctx.update(sr.extracts)
    if has_error:
        return "error", extracts
    if has_failed:
        return "failed", extracts
    return "passed", extracts
