# -*- coding: utf-8 -*-
"""项目分类数据模型（平台级共享）。

Project → ProjectVersion 两层分类结构。
所有需要分类的模块（知识库文档、测试用例）通过可空逻辑外键关联。

设计要点：
- Project.name 全局唯一；ProjectVersion 同项目内 name 唯一。
- 外键 project_id/version_id 跨 DB 文件（projects.db vs kb.db vs testcase.db），
  SQLite 单连接无法跨文件 FK，故只做逻辑外键（不加 ForeignKey 约束）。
- 遵循 P0-1 的 MappedAsDataclass 风格：ORM 模型即 dataclass，零转换层。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from insight_aitest.platform.persistence import Base


class Project(MappedAsDataclass, Base):
    """项目。顶层分类容器。"""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    name: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    color: Mapped[str] = mapped_column(Text, default="#00e5ff")  # 侧边栏标识色
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)


class ProjectVersion(MappedAsDataclass, Base):
    """项目版本。Project 下的一级分类。同项目内版本名唯一。"""

    __tablename__ = "project_versions"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_version_project_name"),
        Index("idx_versions_project", "project_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), default=0
    )
    name: Mapped[str] = mapped_column(Text, default="")  # "v2.0"
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
