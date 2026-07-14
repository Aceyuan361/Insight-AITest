# -*- coding: utf-8 -*-
"""平台持久层自定义字段类型（spec P0-1）。

这里只放「单个字段格式的桥接类型」，不放「整类序列化协议的复刻」
（后者用原生 ``DateTime``/``JSON`` 即可，见 spec §0.1/§0.2）。

``CommaList``：把 ``list[str]`` ↔ 逗号分隔 TEXT。旧库的 tags 列就是这种格式，
迁 ORM 时为不破坏存量数据而保留。集中一处，替代原散落在各 DB 类的
``",".join(case.tags)`` / ``(row["tags"] or "").split(",")`` 模板。
"""

from __future__ import annotations

from enum import Enum

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator


class CommaList(TypeDecorator[list[str]]):
    """``list[str]`` ↔ 逗号分隔 TEXT（空列表存空串）。"""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: list[str] | None, dialect) -> str:  # noqa: ANN001
        return ",".join(value) if value else ""

    def process_result_value(self, value: str | None, dialect) -> list[str]:  # noqa: ANN001
        return [t for t in (value or "").split(",") if t]


def enum_values(enum_cls: type[Enum]) -> list[str]:
    """SQLAlchemy SAEnum 的 values_callable：把 Enum → [value 字符串列表]。

    所有模块的 ORM model 用 ``SAEnum(MyEnum, values_callable=enum_values)``
    确保枚举存储为 ``.value`` 而非 ``.name``。
    """
    return [e.value for e in enum_cls]
