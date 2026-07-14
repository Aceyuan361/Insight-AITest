# -*- coding: utf-8 -*-
"""平台级 API：/api/platform/*"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter


# 可注入的"模块清单视图"，由 kernel 启动时设置。
# 默认返回空列表（便于测试与未装配时安全降级）。
def _empty_list() -> list[dict[str, Any]]:
    return []


_registry_view: Callable[[], list[dict[str, Any]]] = _empty_list


# 可注入的"仪表盘聚合数据 provider"，由 kernel 启动时设置。
# 默认返回空字典（平台层不直接依赖各模块 DB，避免耦合；由 kernel 组合各模块查询）。
def _empty_dict() -> dict[str, Any]:
    return {}


_dashboard_provider: Callable[[], dict[str, Any]] = _empty_dict


def set_registry_view(view: Callable[[], list[dict[str, Any]]]) -> None:
    global _registry_view
    _registry_view = view


def set_dashboard_provider(provider: Callable[[], dict[str, Any]]) -> None:
    global _dashboard_provider
    _dashboard_provider = provider


def build_platform_router() -> APIRouter:
    router = APIRouter(tags=["platform"])

    @router.get("/modules")
    async def list_modules() -> list[dict[str, Any]]:
        """返回已加载模块清单（前端据此生成路由/菜单/卡片）。"""
        return _registry_view()

    @router.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy"}

    @router.get("/dashboard/summary")
    async def dashboard_summary() -> dict[str, Any]:
        """跨模块聚合仪表盘：API/UI 执行结果 + 用例统计 + 性能会话。

        数据由 kernel 注入的 provider 提供（平台层不直接 import 模块 DB）。
        provider 缺失或异常时返回空结构（安全降级）。
        """
        try:
            return _dashboard_provider()
        except Exception:
            return {"executions": [], "stats": {}, "testcases": {}, "monitoring": {}}

    return router
