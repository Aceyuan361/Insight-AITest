# -*- coding: utf-8 -*-
"""AI 模块路由汇总。kernel 通过 manifest 引用本模块的 `router`。

文档管理（documents router）已迁移到独立 kb 模块。
ai 模块保留对话/聊天/RAG/配置 + Agent 任务（子项目2）。
"""

from fastapi import APIRouter

from .health_route import router as health_router
from .conversations import router as conversations_router
from .chat import router as chat_router
from .config_route import router as config_router
from .tasks import router as tasks_router

router = APIRouter()
router.include_router(health_router)
router.include_router(conversations_router)
router.include_router(chat_router)
router.include_router(config_router)
router.include_router(tasks_router)

__all__ = ["router"]
