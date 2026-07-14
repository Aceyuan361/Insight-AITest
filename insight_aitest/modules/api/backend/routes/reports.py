# -*- coding: utf-8 -*-
"""执行报告 API（HTML）。

消费 RunRecord 生成自包含 HTML 报告（纯 Python，无外部依赖）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from insight_aitest.modules.api.backend.deps import get_run_db
from insight_aitest.modules.api.backend.persistence.database import RunDatabase
from insight_aitest.modules.api.backend.report.html_report import render_run_html

router = APIRouter(prefix="/runs", tags=["api"])


@router.get("/{run_id}/report.html")
async def run_report_html(run_id: int, db: RunDatabase = Depends(get_run_db)) -> Response:
    """单次执行的 HTML 报告。"""
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "执行记录不存在")
    html = render_run_html(run)
    return Response(content=html, media_type="text/html; charset=utf-8")
