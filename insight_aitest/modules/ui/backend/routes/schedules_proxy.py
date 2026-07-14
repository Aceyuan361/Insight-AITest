# -*- coding: utf-8 -*-
"""schedules 路由代理（从 scheduler.routes 重新导出 router）。

routes/__init__.py 统一从此文件 include，避免顶层 routes 目录引用 scheduler 子包的歧义。
"""

from insight_aitest.modules.ui.backend.scheduler.routes import router  # noqa: F401

__all__ = ["router"]
