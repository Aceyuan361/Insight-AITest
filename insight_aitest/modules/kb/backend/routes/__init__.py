# -*- coding: utf-8 -*-
"""kb 模块路由汇总。kernel 通过 manifest 引用本模块的 `router`。"""

from fastapi import APIRouter

from .documents import router as documents_router

router = APIRouter()
router.include_router(documents_router)

__all__ = ["router"]
