# -*- coding: utf-8 -*-
"""testcase 模块路由汇总。"""

from fastapi import APIRouter
from .health_route import router as health_router
from .testcases import router as testcases_router
from .generate import router as generate_router
from .export import router as export_router

router = APIRouter()
router.include_router(health_router)
router.include_router(testcases_router)
router.include_router(generate_router)
router.include_router(export_router)

__all__ = ["router"]
