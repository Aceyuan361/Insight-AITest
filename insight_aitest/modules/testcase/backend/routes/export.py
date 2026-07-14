# -*- coding: utf-8 -*-
"""用例导出 API（JSON，给 E/F 执行消费）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from insight_aitest.modules.testcase.backend.deps import get_tc_db
from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase
from insight_aitest.modules.testcase.backend.routes.testcases import _out

router = APIRouter(prefix="/testcases", tags=["testcase"])


class ExportRequest(BaseModel):
    ids: list[int]


def _export_dict(case) -> dict:
    """导出完整用例结构（含 content/preconditions/status 等全字段）。"""
    return _out(case).model_dump()


@router.get("/{case_id}/export")
async def export_one(case_id: int, db: TestCaseDatabase = Depends(get_tc_db)) -> dict:
    case = db.get_case(case_id)
    if not case:
        raise HTTPException(404, "用例不存在")
    return _export_dict(case)


@router.post("/export")
async def export_batch(
    body: ExportRequest, db: TestCaseDatabase = Depends(get_tc_db)
) -> list[dict]:
    out = []
    for cid in body.ids:
        case = db.get_case(cid)
        if case:
            out.append(_export_dict(case))
    return out
