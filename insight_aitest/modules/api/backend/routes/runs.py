# -*- coding: utf-8 -*-
"""执行 / 历史 / 详情 / 统计 API（spec E §5）。"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from logzero import logger
from pydantic import BaseModel

from insight_aitest.modules.api.backend.deps import get_run_db
from insight_aitest.modules.api.backend.engine.executor import _validate_content, execute
from insight_aitest.modules.api.backend.persistence.database import RunDatabase
from insight_aitest.modules.api.backend.persistence.models import RunRecord, RunStatus

router = APIRouter(prefix="/runs", tags=["api"])


class ExecuteRequest(BaseModel):
    case_id: int


# ===== D 交互（可被测试 monkeypatch 替换） =====
#
# 注意：E 与 D 同进程，不能用 HTTP 自调用（127.0.0.1:8001 → 自己），
# 单 worker 下 /execute 占住工作线程，D 子请求无法被处理 → 死锁。
# 因此直接复用 D 的 TestCaseDatabase（只读取/回填，不触碰 D 内部逻辑）。


def _d_db():
    """获取 D 的 TestCaseDatabase 单例（延迟 import 避免循环依赖）。"""
    from insight_aitest.modules.testcase.backend.deps import get_tc_db

    return get_tc_db()


def _fetch_case_from_d(case_id: int) -> dict | None:
    """从 D 读 API 用例（含 content）。不存在返回 None。"""
    from insight_aitest.modules.testcase.backend.routes.testcases import _out

    case = _d_db().get_case(case_id)
    if case is None:
        return None
    return _out(case).model_dump()


def _patch_result_to_d(case_id: int, result: str, run_at: str) -> bool:
    """回填 D 的 last_result/last_run_at。失败抛异常（调用方吞掉）。"""
    run_at_dt = None
    if run_at:
        try:
            run_at_dt = datetime.fromisoformat(run_at)
        except ValueError:
            run_at_dt = None
    _d_db().update_result(case_id, result, run_at_dt)
    return True


def _make_transport() -> httpx.BaseTransport | None:
    """生产环境返回 None（用默认 httpx.Client）。测试 monkeypatch 注入 MockTransport。"""
    return None


# ===== 端点 =====


def _run_out(run: RunRecord) -> dict:
    d = asdict(run)
    d["status"] = run.status.value
    d["id"] = run.id
    return d


@router.post("/execute")
async def execute_case(
    body: ExecuteRequest,
    environment_id: int | None = Query(None),
    db: RunDatabase = Depends(get_run_db),
) -> dict:
    case = _fetch_case_from_d(body.case_id)
    if not case:
        raise HTTPException(404, f"用例 {body.case_id} 不存在")
    content = case.get("content") or {}

    env = None
    initial_vars: dict | None = None
    if environment_id is not None:
        from insight_aitest.modules.api.backend.deps import get_env_db

        env = get_env_db().get(environment_id)
        if not env:
            raise HTTPException(404, "环境不存在")
        import copy

        content = copy.deepcopy(content)
        content["base_url"] = env.base_url
        initial_vars = env.variables or {}
    else:
        # 无指定环境时自动使用默认环境
        from insight_aitest.modules.api.backend.deps import get_env_db

        default_env = get_env_db().get_default()
        if default_env:
            import copy
            content = copy.deepcopy(content)
            content["base_url"] = default_env.base_url
            initial_vars = default_env.variables or {}

    try:
        _validate_content(content)
    except ValueError as e:
        raise HTTPException(422, f"用例 content 非合法 API schema: {e}")

    transport = _make_transport()
    run = execute(
        content,
        transport=transport,
        case_id=body.case_id,
        case_title=case.get("title", ""),
        initial_vars=initial_vars,
    )
    run.project_id = case.get("project_id")  # 从 case 冗余（snapshot 语义）
    run.id = db.create_run(run)

    # 回填 D（失败不阻断）
    try:
        _patch_result_to_d(body.case_id, run.status.value, run.finished_at.isoformat())
    except Exception as e:
        logger.warning(f"回填 D 用例 {body.case_id} 结果失败（已存执行历史）: {e}")

    return _run_out(run)


@router.get("")
async def list_runs(
    case_id: int | None = Query(None),
    status: str | None = Query(None),
    project_id: int | None = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    db: RunDatabase = Depends(get_run_db),
) -> list[dict]:
    sf = RunStatus(status) if status else None
    return db.list_runs(
        case_id=case_id, status=sf, project_id=project_id, limit=limit, offset=offset
    )


@router.get("/stats")
async def stats(case_id: int | None = Query(None), db: RunDatabase = Depends(get_run_db)) -> dict:
    rows = db.list_runs(case_id=case_id, limit=1000)
    total = len(rows)
    by = {"passed": 0, "failed": 0, "error": 0}
    for r in rows:
        by[r["status"]] = by.get(r["status"], 0) + 1
    last = rows[0] if rows else None

    # 近 30 天每日通过率趋势
    from collections import defaultdict
    from datetime import datetime, timedelta

    now = datetime.now()
    daily_data = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "error": 0})
    for r in rows:
        sa = r["started_at"]
        if sa is None:
            continue
        if isinstance(sa, str):
            try:
                sa = datetime.fromisoformat(sa)
            except (ValueError, TypeError):
                continue
        if (now - sa).days > 30:
            continue
        day_key = sa.strftime("%m-%d")
        daily_data[day_key]["total"] += 1
        daily_data[day_key][r["status"]] = daily_data[day_key].get(r["status"], 0) + 1

    # 补全缺失天数
    trend = []
    for i in range(29, -1, -1):
        d = (now - timedelta(days=i)).strftime("%m-%d")
        dd = daily_data.get(d, {"total": 0, "passed": 0, "failed": 0, "error": 0})
        rate = round(dd["passed"] / dd["total"] * 100, 1) if dd["total"] > 0 else 0
        trend.append({"date": d, "total": dd["total"], "passed": dd["passed"], "failed": dd["failed"], "error": dd["error"], "pass_rate": rate})

    # 失败 TOP5 用例
    fail_counts = defaultdict(lambda: {"case_title": "", "case_id": 0, "failed": 0, "error": 0, "total": 0})
    for r in rows:
        key = r["case_id"]
        fail_counts[key]["case_title"] = r["case_title"]
        fail_counts[key]["case_id"] = r["case_id"]
        fail_counts[key]["total"] += 1
        if r["status"] in ("failed", "error"):
            fail_counts[key][r["status"]] += 1
    top_failures = sorted(fail_counts.values(), key=lambda x: x["failed"] + x["error"], reverse=True)[:5]

    # 平均耗时
    durations = [r["duration_ms"] for r in rows if r.get("duration_ms")]
    avg_duration = round(sum(durations) / len(durations)) if durations else 0

    return {
        "total": total,
        "passed": by["passed"],
        "failed": by["failed"],
        "error": by["error"],
        "last_run_at": last["started_at"] if last else None,
        "last_status": last["status"] if last else None,
        "avg_duration_ms": avg_duration,
        "pass_rate": round(by["passed"] / total * 100, 1) if total > 0 else 0,
        "trend": trend,
        "top_failures": top_failures,
    }


@router.get("/{run_id}")
async def get_run(run_id: int, db: RunDatabase = Depends(get_run_db)) -> dict:
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "执行记录不存在")
    return _run_out(run)


@router.delete("/{run_id}")
async def delete_run(run_id: int, db: RunDatabase = Depends(get_run_db)) -> dict:
    if not db.delete_run(run_id):
        raise HTTPException(404, "执行记录不存在")
    return {"deleted": run_id}
