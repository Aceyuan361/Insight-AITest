# -*- coding: utf-8 -*-
"""性能模块路由汇总。kernel 通过 manifest 引用本模块的 `router`。"""

from fastapi import APIRouter

from .devices import router as devices_router
from .monitoring import router as monitoring_router

router = APIRouter()
router.include_router(devices_router)
router.include_router(monitoring_router)

__all__ = ["router"]
