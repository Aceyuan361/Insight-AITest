# -*- coding: utf-8 -*-
"""api 模块路由汇总。"""

from fastapi import APIRouter
from .environments import router as environments_router
from .reports import router as reports_router
from .runs import router as runs_router
from .suites import router as suites_router
from ..scheduler.routes import router as schedules_router

router = APIRouter()
router.include_router(runs_router)
router.include_router(reports_router)
router.include_router(environments_router)
router.include_router(suites_router)
router.include_router(schedules_router)

__all__ = ["router"]
