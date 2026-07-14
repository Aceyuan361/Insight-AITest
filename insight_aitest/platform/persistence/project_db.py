# -*- coding: utf-8 -*-
"""项目分类数据库（ProjectDatabase）。

独立 projects.db 文件（~/.insight_eye/projects.db），存 projects + project_versions 两张表。
遵循 P0-1 的平台 ORM 模式：create_all + session_scope。

跨模块分类查询（如"某项目下有多少文档/用例"）不在本类实现——需要跨 DB 聚合，
由 API 层分别查 kb.db / testcase.db 后合并。本类只管 projects.db 自身的 CRUD。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select

from insight_aitest.platform.persistence import Base, get_engine, session_scope
from insight_aitest.platform.persistence.project_models import Project, ProjectVersion


class ProjectDatabase:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Base.metadata.create_all(
            get_engine(db_path),
            tables=[Project.__table__, ProjectVersion.__table__],
        )

    # ===== Project =====

    def create_project(self, name: str, description: str = "", color: str = "#00e5ff") -> int:
        with session_scope(self.db_path) as s:
            p = Project(name=name, description=description, color=color)
            s.add(p)
            s.flush()
            return p.id

    def get_project(self, project_id: int) -> Project | None:
        with session_scope(self.db_path) as s:
            return s.get(Project, project_id)

    def list_projects(self) -> list[Project]:
        stmt = select(Project).order_by(Project.created_at.desc())
        with session_scope(self.db_path) as s:
            return list(s.scalars(stmt))

    def update_project(
        self,
        project_id: int,
        name: str | None = None,
        description: str | None = None,
        color: str | None = None,
    ) -> bool:
        with session_scope(self.db_path) as s:
            p = s.get(Project, project_id)
            if p is None:
                return False
            if name is not None:
                p.name = name
            if description is not None:
                p.description = description
            if color is not None:
                p.color = color
            p.updated_at = datetime.now()
            return True

    def delete_project(self, project_id: int) -> bool:
        with session_scope(self.db_path) as s:
            p = s.get(Project, project_id)
            if p is None:
                return False
            s.delete(p)  # CASCADE 删除关联 versions
            return True

    def count_versions(self, project_id: int) -> int:
        stmt = select(func.count(ProjectVersion.id)).where(ProjectVersion.project_id == project_id)
        with session_scope(self.db_path) as s:
            return s.scalar(stmt) or 0

    def name_exists(self, name: str, exclude_id: int | None = None) -> bool:
        stmt = select(func.count(Project.id)).where(Project.name == name)
        if exclude_id is not None:
            stmt = stmt.where(Project.id != exclude_id)
        with session_scope(self.db_path) as s:
            return (s.scalar(stmt) or 0) > 0

    # ===== Version =====

    def create_version(
        self, project_id: int, name: str, description: str = "", is_active: bool = True
    ) -> int:
        with session_scope(self.db_path) as s:
            v = ProjectVersion(
                project_id=project_id, name=name, description=description, is_active=is_active
            )
            s.add(v)
            s.flush()
            return v.id

    def get_version(self, version_id: int) -> ProjectVersion | None:
        with session_scope(self.db_path) as s:
            return s.get(ProjectVersion, version_id)

    def list_versions(self, project_id: int) -> list[ProjectVersion]:
        stmt = (
            select(ProjectVersion)
            .where(ProjectVersion.project_id == project_id)
            .order_by(ProjectVersion.created_at.desc())
        )
        with session_scope(self.db_path) as s:
            return list(s.scalars(stmt))

    def list_all_versions(self) -> list[ProjectVersion]:
        """列出所有版本（供全局下拉用）。"""
        stmt = select(ProjectVersion).order_by(ProjectVersion.project_id, ProjectVersion.name)
        with session_scope(self.db_path) as s:
            return list(s.scalars(stmt))

    def update_version(
        self,
        version_id: int,
        name: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> bool:
        with session_scope(self.db_path) as s:
            v = s.get(ProjectVersion, version_id)
            if v is None:
                return False
            if name is not None:
                v.name = name
            if description is not None:
                v.description = description
            if is_active is not None:
                v.is_active = is_active
            v.updated_at = datetime.now()
            return True

    def delete_version(self, version_id: int) -> bool:
        with session_scope(self.db_path) as s:
            v = s.get(ProjectVersion, version_id)
            if v is None:
                return False
            s.delete(v)
            return True

    def version_name_exists(
        self, project_id: int, name: str, exclude_id: int | None = None
    ) -> bool:
        stmt = select(func.count(ProjectVersion.id)).where(
            ProjectVersion.project_id == project_id, ProjectVersion.name == name
        )
        if exclude_id is not None:
            stmt = stmt.where(ProjectVersion.id != exclude_id)
        with session_scope(self.db_path) as s:
            return (s.scalar(stmt) or 0) > 0
