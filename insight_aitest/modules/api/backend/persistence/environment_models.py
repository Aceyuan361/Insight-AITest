# -*- coding: utf-8 -*-
"""环境数据模型（spec E.1 §2 + P0-1 ORM 迁移）。

P0-1：Environment 从手写 dataclass 改为 ``MappedAsDataclass`` ORM 模型，
同名同字段替换——业务层（routes/tests）用法不变。
- variables 存 JSON 列（原生 JSON）。
- is_default 存 INTEGER 0/1，Python 侧 bool。
- ``name`` 有 UNIQUE 约束（旧表就有），保留。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from insight_aitest.platform.persistence import Base


class Environment(MappedAsDataclass, Base, kw_only=True):
    """环境（ORM 模型，即业务层 DTO）。variables 存 JSON 列。"""

    __test__ = False
    __tablename__ = "environments"
    __table_args__ = (UniqueConstraint("name", name="sqlite_autoindex_environments_1"),)

    id: Mapped[int | None] = mapped_column(
        Integer, primary_key=True, autoincrement=True, default=None
    )
    name: Mapped[str] = mapped_column(Text)
    base_url: Mapped[str] = mapped_column(Text)
    variables: Mapped[dict] = mapped_column("variables_json", JSON, default_factory=dict)
    variables_meta: Mapped[dict] = mapped_column("variables_meta_json", JSON, default_factory=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
