# -*- coding: utf-8 -*-
"""UI 批量执行 API。

端点：
  POST   /batch/execute       批量执行（顺序跑多个 UI 用例）
  GET    /batch/runs          批量执行历史列表
  GET    /batch/runs/{id}     批量执行详情（含每个 case 的子 run）
  DELETE /batch/runs/{id}     删除批量执行记录
"""

from __future__ import annotations

import copy
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from logzero import logger
from pydantic import BaseModel

from insight_aitest.modules.ui.backend.deps import get_batch_db, get_run_db
from insight_aitest.modules.ui.backend.engine.executor import (
    VisionConfigError,
    _validate_content,
    execute,
)
from insight_aitest.modules.ui.backend.persistence.batch_database import UIBatchRunDatabase
from insight_aitest.modules.ui.backend.persistence.batch_models import (
    BatchRunStatus,
    UIBatchRun,
)
from insight_aitest.modules.ui.backend.persistence.database import UIRunDatabase
from insight_aitest.modules.ui.backend.persistence.models import RunStatus

router = APIRouter(prefix="/batch", tags=["ui"])


# ===== D 交互（与 runs.py 同模式，复制避免跨文件 import 混乱） =====


def _d_db():
    from insight_aitest.modules.testcase.backend.deps import get_tc_db
    return get_tc_db()


def _fetch_case_from_d(case_id: int) -> dict | None:
    from insight_aitest.modules.testcase.backend.routes.testcases import _out
    case = _d_db().get_case(case_id)
    if case is None:
        return None
    return _out(case).model_dump()


def _make_agent_factory():
    """生产 agent 工厂（含视觉模型前置校验）。"""
    from insight_aitest.modules.ui.backend.engine.executor import (
        _check_llm_config,
        _default_agent_factory,
    )
    _check_llm_config()
    return _default_agent_factory()


# ===== 端点 =====


class BatchExecuteRequest(BaseModel):
    case_ids: list[int]
    name: str | None = None
    base_url: str | None = None
    browser_config: dict | None = None


def _batch_out(batch: UIBatchRun) -> dict:
    return {
        "id": batch.id,
        "name": batch.name,
        "case_ids": batch.case_ids,
        "config": batch.config,
        "status": batch.status.value if hasattr(batch.status, "value") else batch.status,
        "total": batch.total,
        "passed": batch.passed,
        "failed": batch.failed,
        "error": batch.error,
        "case_run_ids": batch.case_run_ids,
        "started_at": batch.started_at.isoformat() if batch.started_at else None,
        "finished_at": batch.finished_at.isoformat() if batch.finished_at else None,
    }


async def _run_batch_task(
    batch_id: int, case_ids: list[int], base_url: str | None, browser_config: dict | None,
) -> None:
    """后台批量执行任务（不阻塞 HTTP 响应）。"""
    from insight_aitest.modules.ui.backend.deps import get_batch_db, get_run_db

    batch_db = get_batch_db()
    run_db = get_run_db()

    case_run_ids: list[int] = []
    passed = 0
    failed = 0
    error_count = 0

    # 前置校验视觉模型配置（可能抛 VisionConfigError）
    try:
        agent_factory = _make_agent_factory()
    except VisionConfigError as e:
        logger.error(f"批量执行 {batch_id} 视觉模型配置错误: {e}")
        batch_db.update(
            batch_id, status=BatchRunStatus.ERROR, passed=0, failed=0,
            error=len(case_ids), case_run_ids=[], finished_at=datetime.now(),
        )
        return

    for case_id in case_ids:
        case = _fetch_case_from_d(case_id)
        if not case:
            error_count += 1
            continue
        content = copy.deepcopy(case.get("content") or {})
        if base_url:
            content["base_url"] = base_url

        try:
            _validate_content(content)
        except ValueError:
            error_count += 1
            continue

        try:
            run = await execute(
                content,
                agent_factory=agent_factory,
                case_id=case_id,
                case_title=case.get("title", ""),
                browser_config=browser_config,
            )
            run.project_id = case.get("project_id")
            run.id = run_db.create_run(run)
            case_run_ids.append(run.id)

            if run.status == RunStatus.PASSED:
                passed += 1
            elif run.status == RunStatus.FAILED:
                failed += 1
            else:
                error_count += 1
        except VisionConfigError as e:
            logger.error(f"批量执行 {batch_id} 视觉模型配置错误: {e}")
            error_count += 1
            break  # 配置错误，没必要继续
        except Exception as e:
            logger.exception(f"批量执行 {batch_id} case {case_id} 异常")
            error_count += 1

    # 汇总状态
    if error_count > 0:
        final_status = BatchRunStatus.ERROR
    elif failed > 0:
        final_status = BatchRunStatus.FAILED
    else:
        final_status = BatchRunStatus.PASSED

    batch_db.update(
        batch_id,
        status=final_status,
        passed=passed,
        failed=failed,
        error=error_count,
        case_run_ids=case_run_ids,
        finished_at=datetime.now(),
    )


@router.post("/execute", status_code=201)
async def execute_batch(
    body: BatchExecuteRequest,
    db: UIBatchRunDatabase = Depends(get_batch_db),
) -> dict:
    if not body.case_ids:
        raise HTTPException(422, "请至少选择一个用例")

    name = body.name or f"批量执行 ({len(body.case_ids)} 用例)"
    batch = UIBatchRun(
        id=None,
        name=name,
        case_ids=body.case_ids,
        config={"base_url": body.base_url, "browser_config": body.browser_config},
        status=BatchRunStatus.RUNNING,
        total=len(body.case_ids),
        passed=0,
        failed=0,
        error=0,
        case_run_ids=[],
        started_at=datetime.now(),
        finished_at=None,
    )
    batch_id = db.create(batch)

    # 异步执行（不等待完成，立即返回）
    import asyncio
    asyncio.create_task(
        _run_batch_task(batch_id, body.case_ids, body.base_url, body.browser_config)
    )

    return _batch_out(db.get(batch_id))


@router.get("/runs")
async def list_batch_runs(
    limit: int = Query(50),
    offset: int = Query(0),
    db: UIBatchRunDatabase = Depends(get_batch_db),
) -> list[dict]:
    return db.list(limit=limit, offset=offset)


@router.get("/runs/{batch_id}")
async def get_batch_run(
    batch_id: int,
    db: UIBatchRunDatabase = Depends(get_batch_db),
    run_db: UIRunDatabase = Depends(get_run_db),
) -> dict:
    batch = db.get(batch_id)
    if not batch:
        raise HTTPException(404, "批量执行记录不存在")
    out = _batch_out(batch)
    # 附带每个 case 的子 run 摘要
    child_runs = []
    for rid in batch.case_run_ids:
        run = run_db.get_run(rid)
        if run:
            child_runs.append({
                "id": run.id,
                "case_id": run.case_id,
                "case_title": run.case_title,
                "status": run.status.value,
                "total_steps": run.total_steps,
                "passed_steps": run.passed_steps,
                "duration_ms": run.duration_ms,
            })
    out["child_runs"] = child_runs
    return out


@router.delete("/runs/{batch_id}")
async def delete_batch_run(
    batch_id: int,
    db: UIBatchRunDatabase = Depends(get_batch_db),
) -> dict:
    if not db.delete(batch_id):
        raise HTTPException(404, "批量执行记录不存在")
    return {"deleted": batch_id}
