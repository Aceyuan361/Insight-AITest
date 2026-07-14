# -*- coding: utf-8 -*-
"""生成相关 API：/analyze 分析可测点（Phase A）+ /generate 生成单条（Phase B）。"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from insight_aitest.modules.testcase.backend.deps import get_analyzer, get_generator, get_tc_db
from insight_aitest.modules.testcase.backend.generator.analyzer import TestPoint
from insight_aitest.modules.testcase.backend.persistence.models import CaseType, TestType
from insight_aitest.modules.testcase.backend.routes.testcases import CaseOut, _out

router = APIRouter(prefix="/testcases", tags=["testcase"])


class AnalyzeRequest(BaseModel):
    query: str
    document_ids: list[int] | None = None


class TestPointOut(BaseModel):
    id: str
    summary: str
    suggested_type: str
    suggested_design: str
    rationale: str


@router.post("/analyze", response_model=list[TestPointOut], deprecated=True)
async def analyze(req: AnalyzeRequest, response: Response, analyzer=Depends(get_analyzer)):
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</api/modules/ai/tasks/quick>; rel="successor-version"'
    points = await asyncio.to_thread(analyzer.analyze, req.query, req.document_ids)
    return [
        TestPointOut(
            id=p.id,
            summary=p.summary,
            suggested_type=p.suggested_type.value,
            suggested_design=p.suggested_design.value,
            rationale=p.rationale,
        )
        for p in points
    ]


class GenerateRequest(BaseModel):
    point: TestPointOut
    document_ids: list[int] | None = None
    type: str | None = None  # 覆盖建议类型
    test_design: str | None = None  # 覆盖建议设计方法
    project_id: int | None = None
    version_id: int | None = None


@router.post("/generate", response_model=CaseOut, status_code=201, deprecated=True)
async def generate(
    req: GenerateRequest, response: Response, gen=Depends(get_generator), db=Depends(get_tc_db)
) -> CaseOut:
    """为单个可测点生成一条用例，生成即落库为 draft。"""
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</api/modules/ai/tasks/quick>; rel="successor-version"'
    point = TestPoint(
        id=req.point.id,
        summary=req.point.summary,
        suggested_type=CaseType(req.point.suggested_type),
        suggested_design=TestType(req.point.suggested_design),
        rationale=req.point.rationale,
    )
    case = await asyncio.to_thread(gen.generate, point, req.document_ids, req.type, req.test_design)
    case.project_id = req.project_id
    case.version_id = req.version_id
    cid = db.create_case(case)
    return _out(db.get_case(cid))


class ImageInput(BaseModel):
    data: str  # base64 编码（不含 data: 前缀）
    mime: str = "image/png"


class GenerateFromImageRequest(BaseModel):
    images: list[ImageInput]
    base_url: str
    point_summary: str = ""
    project_id: int | None = None
    version_id: int | None = None


@router.post("/generate-from-image", response_model=CaseOut, status_code=201, deprecated=True)
async def generate_from_image(
    req: GenerateFromImageRequest,
    response: Response,
    gen=Depends(get_generator),
    db=Depends(get_tc_db),
) -> CaseOut:
    """从截图生成一条 UI 用例，生成即落库为 draft。"""
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</api/modules/ai/tasks/quick>; rel="successor-version"'
    images = [(img.data, img.mime) for img in req.images]
    case = await asyncio.to_thread(gen.generate_from_image, images, req.base_url, req.point_summary)
    case.project_id = req.project_id
    case.version_id = req.version_id
    cid = db.create_case(case)
    return _out(db.get_case(cid))
