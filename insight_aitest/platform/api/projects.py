# -*- coding: utf-8 -*-
"""项目分类 API：/api/platform/projects/*

提供 Project + Version 的 CRUD，以及跨模块关联计数（删除前阻止检查）。
跨 DB 聚合（projects.db / kb.db / testcase.db）由本路由层组合查询。
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# ===== 单例 =====

_project_db = None


def get_project_db():
    global _project_db
    if _project_db is None:
        from insight_aitest.platform.persistence.project_db import ProjectDatabase

        _project_db = ProjectDatabase(os.path.expanduser("~/.insight_eye/projects.db"))
    return _project_db


# ===== Pydantic schemas =====


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    color: str = "#00e5ff"


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None


class VersionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: str = ""
    is_active: bool = True


class VersionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


def _project_to_dict(p, version_count: int = 0) -> dict[str, Any]:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "color": p.color,
        "version_count": version_count,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _version_to_dict(v) -> dict[str, Any]:
    return {
        "id": v.id,
        "project_id": v.project_id,
        "name": v.name,
        "description": v.description,
        "is_active": v.is_active,
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "updated_at": v.updated_at.isoformat() if v.updated_at else None,
    }


def _count_referenced(
    project_id: int | None = None, version_id: int | None = None
) -> dict[str, int]:
    """跨 DB 统计各模块引用数（删除前阻止检查用）。

    各子 DB 查询失败时该维度记为 None（"未知"），调用方据此阻止删除——
    绝不静默吞异常后返回 0 放行删除（否则会孤立引用、误删有内容的项目）。
    覆盖：KB 文档 / 用例 / API 执行记录 / UI 执行记录 / 监控会话 / AI 会话 / Agent 任务。
    """

    def _safe_count(getter):
        """对单个模块的 count 调用做异常隔离，失败返回 None。"""
        try:
            if project_id is None:
                return 0
            return getter(project_id)
        except Exception:
            return None

    docs = _safe_count(
        lambda pid: __import__("insight_aitest.platform.services.kb.deps", fromlist=["get_kb_db"])
        .get_kb_db()
        .count_by_project(pid)
    )
    cases = _safe_count(
        lambda pid: __import__("insight_aitest.modules.testcase.backend.deps", fromlist=["get_tc_db"])
        .get_tc_db()
        .count_by_project(pid)
    )
    api_runs = _safe_count(
        lambda pid: __import__("insight_aitest.modules.api.backend.deps", fromlist=["get_run_db"])
        .get_run_db()
        .count_by_project(pid)
    )
    ui_runs = _safe_count(
        lambda pid: __import__("insight_aitest.modules.ui.backend.deps", fromlist=["get_run_db"])
        .get_run_db()
        .count_by_project(pid)
    )
    sessions = _safe_count(
        lambda pid: __import__(
            "insight_aitest.platform.persistence.database", fromlist=["DatabaseManager"]
        )
        .DatabaseManager.default()
        .count_sessions_by_project(pid)
    )
    conversations = _safe_count(
        lambda pid: __import__("insight_aitest.modules.ai.backend.deps", fromlist=["get_db"])
        .get_db()
        .count_conversations_by_project(pid)
    )
    tasks = _safe_count(
        lambda pid: __import__("insight_aitest.modules.ai.backend.deps", fromlist=["get_db"])
        .get_db()
        .count_tasks_by_project(pid)
    )
    return {
        "documents": docs,
        "testcases": cases,
        "api_runs": api_runs,
        "ui_runs": ui_runs,
        "sessions": sessions,
        "conversations": conversations,
        "tasks": tasks,
    }


# ===== Router =====


def build_projects_router() -> APIRouter:
    router = APIRouter(tags=["projects"])

    # ----- Project CRUD -----

    @router.get("/projects")
    async def list_projects() -> list[dict[str, Any]]:
        db = get_project_db()
        projects = db.list_projects()
        return [_project_to_dict(p, db.count_versions(p.id)) for p in projects]

    @router.post("/projects", status_code=201)
    async def create_project(body: ProjectCreate) -> dict[str, Any]:
        db = get_project_db()
        if db.name_exists(body.name):
            raise HTTPException(409, f"项目名「{body.name}」已存在")
        pid = db.create_project(name=body.name, description=body.description, color=body.color)
        return _project_to_dict(db.get_project(pid))

    @router.get("/projects/{project_id}")
    async def get_project(project_id: int) -> dict[str, Any]:
        db = get_project_db()
        p = db.get_project(project_id)
        if p is None:
            raise HTTPException(404, "项目不存在")
        return _project_to_dict(p, db.count_versions(project_id))

    @router.put("/projects/{project_id}")
    async def update_project(project_id: int, body: ProjectUpdate) -> dict[str, Any]:
        db = get_project_db()
        p = db.get_project(project_id)
        if p is None:
            raise HTTPException(404, "项目不存在")
        if (
            body.name is not None
            and body.name != p.name
            and db.name_exists(body.name, exclude_id=project_id)
        ):
            raise HTTPException(409, f"项目名「{body.name}」已存在")
        db.update_project(
            project_id,
            name=body.name,
            description=body.description,
            color=body.color,
        )
        return _project_to_dict(db.get_project(project_id), db.count_versions(project_id))

    @router.delete("/projects/{project_id}")
    async def delete_project(project_id: int) -> dict[str, Any]:
        db = get_project_db()
        p = db.get_project(project_id)
        if p is None:
            raise HTTPException(404, "项目不存在")
        refs = _count_referenced(project_id=project_id)
        # 任一维度查询失败（None）→ 未知引用风险，阻止删除
        if any(v is None for v in refs.values()):
            raise HTTPException(
                503,
                "无法确认项目引用情况（子数据库暂时不可用），请稍后重试。",
            )
        total_refs = sum(refs.values())
        if total_refs > 0:
            labels = {
                "documents": "文档",
                "testcases": "用例",
                "api_runs": "API 执行记录",
                "ui_runs": "UI 执行记录",
                "sessions": "监控会话",
                "conversations": "AI 会话",
                "tasks": "Agent 任务",
            }
            detail_parts = [f"{v} 个{labels[k]}" for k, v in refs.items() if v]
            raise HTTPException(
                409,
                f"项目下仍有 {total_refs} 项资源（{'、'.join(detail_parts)}），"
                "请先移除或重新归类后再删除。",
            )
        db.delete_project(project_id)
        return {"deleted": True, "id": project_id}

    # ----- Version CRUD -----

    @router.get("/projects/{project_id}/versions")
    async def list_versions(project_id: int) -> list[dict[str, Any]]:
        db = get_project_db()
        p = db.get_project(project_id)
        if p is None:
            raise HTTPException(404, "项目不存在")
        return [_version_to_dict(v) for v in db.list_versions(project_id)]

    @router.post("/projects/{project_id}/versions", status_code=201)
    async def create_version(project_id: int, body: VersionCreate) -> dict[str, Any]:
        db = get_project_db()
        p = db.get_project(project_id)
        if p is None:
            raise HTTPException(404, "项目不存在")
        if db.version_name_exists(project_id, body.name):
            raise HTTPException(409, f"版本名「{body.name}」在该项目下已存在")
        vid = db.create_version(
            project_id, name=body.name, description=body.description, is_active=body.is_active
        )
        return _version_to_dict(db.get_version(vid))

    @router.put("/versions/{version_id}")
    async def update_version(version_id: int, body: VersionUpdate) -> dict[str, Any]:
        db = get_project_db()
        v = db.get_version(version_id)
        if v is None:
            raise HTTPException(404, "版本不存在")
        if body.name is not None and body.name != v.name:
            if db.version_name_exists(v.project_id, body.name, exclude_id=version_id):
                raise HTTPException(409, f"版本名「{body.name}」在该项目下已存在")
        db.update_version(
            version_id,
            name=body.name,
            description=body.description,
            is_active=body.is_active,
        )
        return _version_to_dict(db.get_version(version_id))

    @router.delete("/versions/{version_id}")
    async def delete_version(version_id: int) -> dict[str, Any]:
        db = get_project_db()
        v = db.get_version(version_id)
        if v is None:
            raise HTTPException(404, "版本不存在")
        db.delete_version(version_id)
        return {"deleted": True, "id": version_id}

    return router
