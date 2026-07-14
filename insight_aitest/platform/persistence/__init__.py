# -*- coding: utf-8 -*-
"""平台持久层（spec P0-1）。

提供统一的 ORM Base + engine/session 工厂，替代原 8 个 DB 类各自的
裸 sqlite3 + threading.local 模板。模块只声明表（继承 Base），不管连接。
"""

from __future__ import annotations

from insight_aitest.platform.persistence.base import Base
from insight_aitest.platform.persistence.engine import (
    ensure_schema,
    get_engine,
    get_session_factory,
)
from insight_aitest.platform.persistence.session import session_scope

__all__ = [
    "Base",
    "ensure_schema",
    "get_engine",
    "get_session_factory",
    "session_scope",
]
