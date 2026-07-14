# -*- coding: utf-8 -*-
"""套件管理 + 执行 API（spec E.1 §4）。

路由顺序：/runs 系列静态端点必须在 /{suite_id} 动态端点之前注册，
否则 /suites/runs 会被 /suites/{suite_id} 捕获成 suite_id="runs"。
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from logzero import logger
from pydantic import BaseModel

from insight_aitest.modules.api.backend.deps import (
    get_env_db,
    get_run_db,
    get_suite_db,
    get_suite_run_db,
)
from insight_aitest.modules.api.backend.engine.suite_executor import execute_suite
from insight_aitest.modules.api.backend.persistence.database import RunDatabase
from insight_aitest.modules.api.backend.persistence.suite_database import (
    SuiteDatabase,
    SuiteRunDatabase,
)
from insight_aitest.modules.api.backend.persistence.suite_models import (
    Suite,
    SuiteRunRecord,
    SuiteRunStatus,
)
from insight_aitest.modules.api.backend.routes.runs import (
    _fetch_case_from_d,
    _make_transport,
    _patch_result_to_d,
)

router = APIRouter(prefix="/suites", tags=["api"])


class SuiteCreate(BaseModel):
    name: str
    description: str = ""
    case_ids: list[int]
    setup: list[dict] = []
    teardown: list[dict] = []


class SuiteUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    case_ids: list[int] | None = None
    setup: list[dict] | None = None
    teardown: list[dict] | None = None


def _suite_out(s: Suite) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "case_ids": s.case_ids,
        "setup": s.setup,
        "teardown": s.teardown,
        "case_count": len(s.case_ids),
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


# ===== 套件执行历史（静态路径，必须在 /{suite_id} 之前）=====


class ExecuteResponse(BaseModel):
    suite_run_id: int
    status: str


@router.post("/{suite_id}/execute", response_model=ExecuteResponse)
async def execute_suite_endpoint(
    suite_id: int,
    background_tasks: BackgroundTasks,
    environment_id: int | None = Query(None),
    db: SuiteDatabase = Depends(get_suite_db),
    suite_run_db: SuiteRunDatabase = Depends(get_suite_run_db),
) -> dict:
    suite = db.get(suite_id)
    if not suite:
        raise HTTPException(404, "套件不存在")
    env = None
    if environment_id is not None:
        env = get_env_db().get(environment_id)
        if not env:
            raise HTTPException(404, "环境不存在")
    else:
        # 无指定环境时自动使用默认环境
        env = get_env_db().get_default()
        environment_id = env.id if env else None

    # 立即写一条 running 的 suite_run（快照冻结当时定义）
    now = datetime.now()
    sr = SuiteRunRecord(
        id=None,
        suite_id=suite.id,
        suite_name=suite.name,
        suite_snapshot={
            "case_ids": suite.case_ids,
            "setup": suite.setup,
            "teardown": suite.teardown,
        },
        environment_id=environment_id,
        environment_name=env.name if env else None,
        status=SuiteRunStatus.RUNNING,
        total=len(suite.case_ids),
        done=0,
        case_run_ids=[],
        setup_status=None,
        started_at=now,
        finished_at=None,
        error=None,
    )
    srid = suite_run_db.create(sr)

    suite_def = {
        "id": suite.id,
        "name": suite.name,
        "case_ids": suite.case_ids,
        "setup": suite.setup,
        "teardown": suite.teardown,
    }
    background_tasks.add_task(_run_suite_task, srid, suite_def, env, suite_run_db)
    return {"suite_run_id": srid, "status": "running"}


def _run_suite_task(srid: int, suite_def: dict, env, suite_run_db: SuiteRunDatabase) -> None:
    """后台 task：跑套件，更新进度 + 最终状态。"""
    run_db = get_run_db()
    transport = _make_transport()
    try:
        result = execute_suite(
            suite=suite_def,
            cases_provider=_fetch_case_from_d,
            run_saver=lambda run: _save_run_and_backfill(run_db, run),
            transport=transport,
            environment=env,
            on_case_done=lambda done, rid: suite_run_db.update_progress(
                srid, done=done, case_run_id=rid
            ),
        )
        suite_run_db.update_setup_status(srid, result["setup_status"])
        suite_run_db.finish(srid, status=result["status"], error=result.get("error"))
    except Exception as e:
        logger.exception(f"套件执行 task 异常 suite_run={srid}")
        suite_run_db.finish(srid, status=SuiteRunStatus.FAILED, error=str(e))


def _save_run_and_backfill(run_db: RunDatabase, run) -> int:
    """落库单条 run + 回填 D（每条 case 的 run 独立存 runs 表）。"""
    run.id = run_db.create_run(run)
    try:
        _patch_result_to_d(run.case_id, run.status.value, run.finished_at.isoformat())
    except Exception as e:
        logger.warning(f"回填 D 用例 {run.case_id} 失败（已存 run）: {e}")
    return run.id


def _fetch_child_runs(case_run_ids: list[int]) -> list:
    """从 RunDatabase 拉取子 run 详情（报告生成用）。"""
    run_db = get_run_db()
    runs = []
    for rid in case_run_ids:
        r = run_db.get_run(rid)
        if r:
            runs.append(r)
    return runs


@router.get("/runs")
async def list_suite_runs(
    suite_id: int | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    db: SuiteRunDatabase = Depends(get_suite_run_db),
) -> list[dict]:
    sf = SuiteRunStatus(status) if status else None
    return db.list(suite_id=suite_id, status=sf, limit=limit, offset=offset)


@router.get("/runs/{run_id}")
async def get_suite_run(run_id: int, db: SuiteRunDatabase = Depends(get_suite_run_db)) -> dict:
    sr = db.get(run_id)
    if not sr:
        raise HTTPException(404, "套件执行记录不存在")
    return {
        "id": sr.id,
        "suite_id": sr.suite_id,
        "suite_name": sr.suite_name,
        "status": sr.status.value,
        "total": sr.total,
        "done": sr.done,
        "case_run_ids": sr.case_run_ids,
        "setup_status": sr.setup_status,
        "environment_name": sr.environment_name,
        "started_at": sr.started_at.isoformat(),
        "finished_at": sr.finished_at.isoformat() if sr.finished_at else None,
        "error": sr.error,
    }


@router.delete("/runs/{run_id}")
async def delete_suite_run(run_id: int, db: SuiteRunDatabase = Depends(get_suite_run_db)) -> dict:
    if not db.delete(run_id):
        raise HTTPException(404, "套件执行记录不存在")
    return {"deleted": run_id}


def _suite_run_to_dict(sr) -> dict:
    """SuiteRunRecord → API dict。"""
    return {
        "id": sr.id,
        "suite_id": sr.suite_id,
        "suite_name": sr.suite_name,
        "status": sr.status.value,
        "total": sr.total,
        "done": sr.done,
        "case_run_ids": sr.case_run_ids,
        "setup_status": sr.setup_status,
        "environment_name": sr.environment_name,
        "started_at": sr.started_at.isoformat() if sr.started_at else None,
        "finished_at": sr.finished_at.isoformat() if sr.finished_at else None,
        "error": sr.error,
    }


@router.get("/runs/{run_id}/report.html")
async def suite_run_report_html(run_id: int, suite_run_db: SuiteRunDatabase = Depends(get_suite_run_db)) -> Response:
    """套件聚合 HTML 报告。"""
    from insight_aitest.modules.api.backend.report.html_report import render_suite_html

    sr = suite_run_db.get(run_id)
    if not sr:
        raise HTTPException(404, "套件执行记录不存在")
    child_runs = _fetch_child_runs(sr.case_run_ids)
    html = render_suite_html(_suite_run_to_dict(sr), child_runs)
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/runs/{run_id}/report.junit.xml")
async def suite_run_report_junit(run_id: int, suite_run_db: SuiteRunDatabase = Depends(get_suite_run_db)) -> Response:
    """套件 JUnit XML 报告（CI/CD 集成）。"""
    from insight_aitest.modules.api.backend.report.html_report import render_junit_xml

    sr = suite_run_db.get(run_id)
    if not sr:
        raise HTTPException(404, "套件执行记录不存在")
    child_runs = _fetch_child_runs(sr.case_run_ids)
    xml = render_junit_xml(_suite_run_to_dict(sr), child_runs)
    return Response(content=xml, media_type="application/xml; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="suite-{run_id}-junit.xml"'})


# ===== 套件 CRUD（动态路径 /{suite_id}）=====
@router.post("", status_code=201)
async def create_suite(body: SuiteCreate, db: SuiteDatabase = Depends(get_suite_db)) -> dict:
    sid = db.create(
        Suite(
            name=body.name,
            description=body.description,
            case_ids=body.case_ids,
            setup=body.setup,
            teardown=body.teardown,
        )
    )
    return _suite_out(db.get(sid))


@router.get("")
async def list_suites(db: SuiteDatabase = Depends(get_suite_db)) -> list[dict]:
    return [_suite_out(s) for s in db.list()]


@router.get("/{suite_id}")
async def get_suite(suite_id: int, db: SuiteDatabase = Depends(get_suite_db)) -> dict:
    s = db.get(suite_id)
    if not s:
        raise HTTPException(404, "套件不存在")
    return _suite_out(s)


@router.put("/{suite_id}")
async def update_suite(
    suite_id: int, body: SuiteUpdate, db: SuiteDatabase = Depends(get_suite_db)
) -> dict:
    if not db.get(suite_id):
        raise HTTPException(404, "套件不存在")
    db.update(suite_id, **body.model_dump(exclude_none=True))
    return _suite_out(db.get(suite_id))


@router.delete("/{suite_id}")
async def delete_suite(suite_id: int, db: SuiteDatabase = Depends(get_suite_db)) -> dict:
    if not db.delete(suite_id):
        raise HTTPException(404, "套件不存在")
    return {"deleted": suite_id}
