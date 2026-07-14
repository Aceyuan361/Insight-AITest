# -*- coding: utf-8 -*-
"""AI 模块健康检查路由。"""

from fastapi import APIRouter

router = APIRouter(tags=["ai-health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "healthy", "module": "ai"}
