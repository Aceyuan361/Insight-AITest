# -*- coding: utf-8 -*-
"""
平台内核 - 装配 FastAPI 应用的唯一入口。

装配流水线：config → logging → db → scan modules → assemble app。
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from logzero import logger

# 兼容旧 main.py 的 sys.path 注入（worktree 开发模式）
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# 让 manifest 里的短路径 import（如 performance.backend.routes）可用
_MODULES_PARENT = str(Path(__file__).parent.parent / "modules")
if _MODULES_PARENT not in sys.path:
    sys.path.insert(0, _MODULES_PARENT)

_MODULES_DIR = Path(__file__).parent.parent / "modules"


def _allowed_origins() -> list[str]:
    return os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:80,http://localhost:81,http://localhost:3000,http://localhost:8000,"
        "http://127.0.0.1:80,http://127.0.0.1:81",
    ).split(",")


def build_app() -> FastAPI:
    """装配并返回 FastAPI 应用。"""
    from insight_aitest.platform.api.platform import (
        build_platform_router,
        set_registry_view,
        set_dashboard_provider,
    )
    from insight_aitest.platform.api.dashboard import build_dashboard_provider
    from insight_aitest.platform.module_registry import ModuleLoadError, ModuleRegistry

    # 0. 旧 ai_kb.db → kb.db + ai.db 迁移（幂等，已迁移则跳过）
    try:
        from insight_aitest.platform.services.kb.database import migrate_from_legacy

        base = os.path.expanduser("~/.insight_eye")
        migrated = migrate_from_legacy(
            ai_kb_path=os.path.join(base, "ai_kb.db"),
            kb_db_path=os.path.join(base, "kb.db"),
            ai_db_path=os.path.join(base, "ai.db"),
        )
        if migrated:
            logger.info("已迁移旧 ai_kb.db → kb.db + ai.db（备份为 ai_kb.db.migrated）")
    except Exception as e:
        logger.warning(f"KB 迁移检查失败（非致命，继续启动）: {e}")

    # 1. 扫描模块清单（校验 + 拓扑排序）
    registry = ModuleRegistry()
    registry.scan(str(_MODULES_DIR))
    logger.info(
        f"已扫描到 {len(registry.modules)} 个模块: " f"{[m.manifest.id for m in registry.modules]}"
    )

    # 2. 解析后端 router/websocket（import 时校验）
    try:
        registry.resolve_backends()
    except ModuleLoadError as e:
        logger.error(f"模块后端加载失败，启动中止: {e}")
        raise

    # 3. 注入清单视图给平台 API
    set_registry_view(registry.to_public_list)
    set_dashboard_provider(build_dashboard_provider())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Insight-AITest 平台启动")
        yield
        logger.info("Insight-AITest 平台关闭")

    app = FastAPI(
        title="Insight-AITest Platform API",
        version="2.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 4. 平台级路由
    app.include_router(build_platform_router(), prefix="/api/platform")

    # 4.1 项目分类路由
    from insight_aitest.platform.api.projects import build_projects_router

    app.include_router(build_projects_router(), prefix="/api/platform")

    # 5. 模块路由（按拓扑序注册）
    for lm in registry.modules:
        if lm.router is not None:
            app.include_router(lm.router, prefix=f"/api/modules/{lm.manifest.id}")
            logger.info(f"已注册模块路由: /api/modules/{lm.manifest.id}")
        if lm.websocket is not None:
            ws_path = f"/api/modules/{lm.manifest.id}/ws/monitoring/{{session_id}}"
            app.websocket(ws_path)(lm.websocket)
            logger.info(f"已注册模块 WebSocket: {ws_path}")

    @app.get("/")
    async def root():
        return {"name": "Insight-AITest Platform API", "version": "2.1.0", "docs": "/docs"}

    return app
