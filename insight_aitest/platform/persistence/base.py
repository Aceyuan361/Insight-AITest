# -*- coding: utf-8 -*-
"""平台持久层 ORM 基类（spec P0-1 §4.2）。

全局唯一 Base，所有模块的 ORM 表模型继承它。模块只"声明表"，"连接"归平台层。
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """全局 ORM 基类。所有模块的表模型继承它。"""
