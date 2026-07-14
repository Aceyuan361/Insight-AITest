# -*- coding: utf-8 -*-
"""testcase 健康检查。"""

from fastapi import APIRouter

router = APIRouter(tags=["testcase"])


@router.get("/health")
async def health():
    return {"status": "healthy", "module": "testcase"}
