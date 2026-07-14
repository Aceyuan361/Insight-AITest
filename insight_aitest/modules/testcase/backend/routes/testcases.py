# -*- coding: utf-8 -*-
"""测试用例 CRUD + 状态切换 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from insight_aitest.modules.testcase.backend.deps import get_tc_db
from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase
from insight_aitest.modules.testcase.backend.persistence.models import (
    CasePriority,
    CaseStatus,
    CaseType,
    TestCase,
    TestType,
)

router = APIRouter(prefix="/testcases", tags=["testcase"])


class CaseOut(BaseModel):
    id: int
    title: str
    type: str
    description: str
    priority: str
    status: str
    test_design: str
    preconditions: str
    content: dict
    tags: list[str]
    source: str
    project_id: int | None = None
    version_id: int | None = None
    last_run_at: str | None
    last_result: str | None
    created_at: str
    updated_at: str


class CaseCreate(BaseModel):
    title: str
    type: str = "functional"
    description: str = ""
    priority: str = "p2"
    test_design: str = "positive"
    preconditions: str = ""
    content: dict = {}
    tags: list[str] = []
    source: str = "manual"
    project_id: int | None = None
    version_id: int | None = None


class CaseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    test_design: str | None = None
    preconditions: str | None = None
    content: dict | None = None
    tags: list[str] | None = None
    version_id: int | None = None


class StatusUpdate(BaseModel):
    status: str


class ResultUpdate(BaseModel):
    result: str
    run_at: str | None = None


class BatchSyncRequest(BaseModel):
    """批次同步请求：把选中用例置 ready + 绑定 version_id，删除未选中（可选）。"""

    case_ids: list[int]
    version_id: int
    delete_unselected: bool = True
    batch_id: str | None = None


def _out(case: TestCase) -> CaseOut:
    return CaseOut(
        id=case.id,
        title=case.title,
        type=case.type.value,
        description=case.description,
        priority=case.priority.value,
        status=case.status.value,
        test_design=case.test_design.value,
        preconditions=case.preconditions,
        content=case.content,
        tags=case.tags,
        source=case.source,
        project_id=case.project_id,
        version_id=case.version_id,
        last_run_at=case.last_run_at.isoformat() if case.last_run_at else None,
        last_result=case.last_result,
        created_at=case.created_at.isoformat(),
        updated_at=case.updated_at.isoformat(),
    )


@router.get("", response_model=list[CaseOut])
async def list_cases(
    type: str | None = None,
    status: str | None = None,
    project_id: int | None = None,
    version_id: int | None = None,
    source: str | None = None,
    task_id: int | None = None,
    db: TestCaseDatabase = Depends(get_tc_db),
) -> list[CaseOut]:
    tf = CaseType(type) if type else None
    sf = CaseStatus(status) if status else None
    return [
        _out(c)
        for c in db.list_cases(
            type_filter=tf,
            status_filter=sf,
            project_id=project_id,
            version_id=version_id,
            source=source,
            task_id=task_id,
        )
    ]


@router.post("", response_model=CaseOut, status_code=201)
async def create_case(body: CaseCreate, db: TestCaseDatabase = Depends(get_tc_db)) -> CaseOut:
    case = TestCase(
        title=body.title,
        type=CaseType(body.type),
        description=body.description,
        priority=CasePriority(body.priority),
        status=CaseStatus.DRAFT,
        test_design=TestType(body.test_design),
        preconditions=body.preconditions,
        content=body.content,
        tags=body.tags,
        source=body.source,
        project_id=body.project_id,
        version_id=body.version_id,
    )
    cid = db.create_case(case)
    return _out(db.get_case(cid))


class AssignmentUpdate(BaseModel):
    project_id: int | None = None
    version_id: int | None = None


class BatchAssignRequest(BaseModel):
    case_ids: list[int]
    project_id: int | None = None
    version_id: int | None = None


def _validate_version_belongs_to_project(project_id: int, version_id: int) -> bool:
    """校验 version 属于 project（跨 DB 查询 projects.db）。

    复用平台 ``get_project_db`` 单例（已按 ~/.insight_eye/projects.db 初始化，
    避免这里误用无参 ``ProjectDatabase()``——其构造需 db_path）。
    """
    try:
        from insight_aitest.platform.api.projects import get_project_db

        version = get_project_db().get_version(version_id)
        return version is not None and version.project_id == project_id
    except Exception:
        return False


@router.post("/batch-assign")
async def batch_assign(body: BatchAssignRequest, db: TestCaseDatabase = Depends(get_tc_db)) -> dict:
    """批量修改用例项目/版本归属。

    注册在 ``/{case_id}`` 之前，避免 "batch-assign" 被当作 case_id。
    """
    if body.project_id is not None and body.version_id is not None:
        if not _validate_version_belongs_to_project(body.project_id, body.version_id):
            raise HTTPException(400, "版本不属于所选项目")
    fields = {}
    if body.project_id is not None:
        fields["project_id"] = body.project_id
    if body.version_id is not None:
        fields["version_id"] = body.version_id
    updated = 0
    for cid in body.case_ids:
        if db.get_case(cid):
            db.update_case(cid, **fields)
            updated += 1
    return {"updated": updated, "total": len(body.case_ids)}


@router.post("/batch-sync")
async def batch_sync_cases(
    req: BatchSyncRequest, db: TestCaseDatabase = Depends(get_tc_db)
) -> dict:
    """批次同步：选中用例 → ready + 绑定 version_id；未选中可删（安全护栏见下）。

    安全护栏：``batch_id`` 必填。batch-sync 会按 batch 维度删除未选中用例，
    缺少 batch_id 时无法界定删除范围，必须拒绝并提示在用例管理模块逐条处理，
    避免误删跨批次/手工用例。
    """
    if not req.batch_id:
        raise HTTPException(
            400,
            "缺少 batch_id，无法安全执行批量同步。请在用例管理模块逐条处理。",
        )
    # defense-in-depth：update 也限定 batch_id，避免 case_ids 跨批次时误改批次外用例
    synced = db.update_cases_in_batch(
        req.case_ids, req.batch_id, status=CaseStatus.READY, version_id=req.version_id
    )
    deleted = 0
    if req.delete_unselected:
        unselected = db.list_case_ids_by_batch_excluding(req.batch_id, req.case_ids)
        if unselected:
            deleted = db.delete_cases_batch(unselected)
    return {"synced": synced, "deleted": deleted}


@router.get("/batch/{batch_id}", response_model=list[CaseOut])
async def get_batch_cases(
    batch_id: str, db: TestCaseDatabase = Depends(get_tc_db)
) -> list[CaseOut]:
    """按 batch_id 列出同批次用例（用例审阅面板批次视图用）。"""
    return [_out(c) for c in db.list_cases_by_batch(batch_id)]


@router.get("/{case_id}", response_model=CaseOut)
async def get_case(case_id: int, db: TestCaseDatabase = Depends(get_tc_db)) -> CaseOut:
    case = db.get_case(case_id)
    if not case:
        raise HTTPException(404, "用例不存在")
    return _out(case)


@router.put("/{case_id}", response_model=CaseOut)
async def update_case(
    case_id: int, body: CaseUpdate, db: TestCaseDatabase = Depends(get_tc_db)
) -> CaseOut:
    if not db.get_case(case_id):
        raise HTTPException(404, "用例不存在")
    fields = body.model_dump(exclude_none=True)
    if "priority" in fields:
        fields["priority"] = CasePriority(fields["priority"])
    if "test_design" in fields:
        fields["test_design"] = TestType(fields["test_design"])
    db.update_case(case_id, **fields)
    return _out(db.get_case(case_id))


@router.patch("/{case_id}/assignment", response_model=CaseOut)
async def update_assignment(
    case_id: int, body: AssignmentUpdate, db: TestCaseDatabase = Depends(get_tc_db)
) -> CaseOut:
    """修改用例的项目/版本归属（归属迁移）。"""
    if not db.get_case(case_id):
        raise HTTPException(404, "用例不存在")
    if body.project_id is not None and body.version_id is not None:
        if not _validate_version_belongs_to_project(body.project_id, body.version_id):
            raise HTTPException(400, "版本不属于所选项目")
    fields = {}
    if body.project_id is not None:
        fields["project_id"] = body.project_id
    if body.version_id is not None:
        fields["version_id"] = body.version_id
    db.update_case(case_id, **fields)
    return _out(db.get_case(case_id))


@router.patch("/{case_id}/status", response_model=CaseOut)
async def update_status(
    case_id: int, body: StatusUpdate, db: TestCaseDatabase = Depends(get_tc_db)
) -> CaseOut:
    if not db.get_case(case_id):
        raise HTTPException(404, "用例不存在")
    db.update_status(case_id, CaseStatus(body.status))
    return _out(db.get_case(case_id))


@router.delete("/{case_id}")
async def delete_case(case_id: int, db: TestCaseDatabase = Depends(get_tc_db)) -> dict:
    if not db.delete_case(case_id):
        raise HTTPException(404, "用例不存在")
    return {"deleted": case_id}


@router.patch("/{case_id}/result", response_model=CaseOut)
async def update_result(
    case_id: int, body: ResultUpdate, db: TestCaseDatabase = Depends(get_tc_db)
) -> CaseOut:
    """E/F 执行后回填 last_result / last_run_at（闭环支撑）。"""
    if not db.get_case(case_id):
        raise HTTPException(404, "用例不存在")
    from datetime import datetime

    run_at = None
    if body.run_at:
        try:
            run_at = datetime.fromisoformat(body.run_at)
        except ValueError:
            run_at = None
    db.update_result(case_id, body.result, run_at)
    return _out(db.get_case(case_id))


@router.get("/documents/all")
async def list_kb_documents():
    """代理平台 KB 文档列表（生成向导选文档范围用）。

    路径用 /documents/all 避免与 /{case_id} 混淆（case_id 是 int，静态段不会撞）。
    """
    from insight_aitest.platform.services.kb.deps import get_kb_db

    kb = get_kb_db()
    return [
        {"id": d.id, "filename": d.filename, "status": d.status.value} for d in kb.list_documents()
    ]
