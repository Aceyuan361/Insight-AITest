# -*- coding: utf-8 -*-
"""ui 模块路由汇总。"""

from fastapi import APIRouter
from .runs import router as runs_router
from .batch import router as batch_router
from .schedules_proxy import router as schedules_router
from .config import router as config_router

router = APIRouter()
router.include_router(runs_router)
router.include_router(batch_router)
router.include_router(schedules_router)
router.include_router(config_router)

__all__ = ["router"]
