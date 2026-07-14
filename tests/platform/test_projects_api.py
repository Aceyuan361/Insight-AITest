# -*- coding: utf-8 -*-
"""项目分类 API + 数据模型集成测试。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_projects_app(tmp_path, monkeypatch):
    """构造一个用 tmp 目录的 app，patch projects.db 路径。"""
    import insight_aitest.platform.api.projects as proj_api

    proj_api._project_db = None  # 重置单例

    # patch get_project_db 返回 tmp 路径的 DB（monkeypatch 负责自动恢复）
    def _tmp_get():
        from insight_aitest.platform.persistence.project_db import ProjectDatabase

        if proj_api._project_db is None:
            proj_api._project_db = ProjectDatabase(str(tmp_path / "projects.db"))
        return proj_api._project_db

    monkeypatch.setattr(proj_api, "get_project_db", _tmp_get)

    app = FastAPI()
    app.include_router(proj_api.build_projects_router(), prefix="/api/platform")
    return TestClient(app)


def test_project_crud(tmp_path, monkeypatch):
    c = _setup_projects_app(tmp_path, monkeypatch)

    # 创建
    r = c.post("/api/platform/projects", json={"name": "商城系统", "description": "电商", "color": "#00e5ff"})
    assert r.status_code == 201
    proj = r.json()
    assert proj["name"] == "商城系统"
    assert proj["id"] > 0
    pid = proj["id"]

    # 列表
    r = c.get("/api/platform/projects")
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "商城系统"

    # 详情
    r = c.get(f"/api/platform/projects/{pid}")
    assert r.json()["name"] == "商城系统"

    # 更新
    r = c.put(f"/api/platform/projects/{pid}", json={"name": "商城V2"})
    assert r.json()["name"] == "商城V2"

    # 删除（无关联数据，应成功）
    # 注：_count_referenced 跨 7 个模块 DB 查询，测试环境各模块 DB 单例未隔离，
    # 这里 patch 为全 0（无引用）以验证删除路径本身。
    import insight_aitest.platform.api.projects as proj_api
    monkeypatch.setattr(
        proj_api,
        "_count_referenced",
        lambda **kw: {
            "documents": 0, "testcases": 0, "api_runs": 0, "ui_runs": 0,
            "sessions": 0, "conversations": 0, "tasks": 0,
        },
    )
    r = c.delete(f"/api/platform/projects/{pid}")
    assert r.status_code == 200
    assert r.json()["deleted"] is True

    # 确认已删
    r = c.get(f"/api/platform/projects/{pid}")
    assert r.status_code == 404


def test_project_name_unique(tmp_path, monkeypatch):
    c = _setup_projects_app(tmp_path, monkeypatch)
    c.post("/api/platform/projects", json={"name": "项目A"})
    r = c.post("/api/platform/projects", json={"name": "项目A"})
    assert r.status_code == 409


def test_version_crud(tmp_path, monkeypatch):
    c = _setup_projects_app(tmp_path, monkeypatch)
    pid = c.post("/api/platform/projects", json={"name": "项目B"}).json()["id"]

    # 创建版本
    r = c.post(f"/api/platform/projects/{pid}/versions", json={"name": "v1.0"})
    assert r.status_code == 201
    vid = r.json()["id"]

    # 列表
    r = c.get(f"/api/platform/projects/{pid}/versions")
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "v1.0"

    # 更新
    r = c.put(f"/api/platform/versions/{vid}", json={"name": "v2.0"})
    assert r.json()["name"] == "v2.0"

    # 删除
    r = c.delete(f"/api/platform/versions/{vid}")
    assert r.status_code == 200


def test_version_name_unique_per_project(tmp_path, monkeypatch):
    c = _setup_projects_app(tmp_path, monkeypatch)
    pid = c.post("/api/platform/projects", json={"name": "项目C"}).json()["id"]
    c.post(f"/api/platform/projects/{pid}/versions", json={"name": "v1.0"})
    r = c.post(f"/api/platform/projects/{pid}/versions", json={"name": "v1.0"})
    assert r.status_code == 409


def test_delete_project_blocked_when_referenced(tmp_path, monkeypatch):
    """有文档/用例关联时应阻止删除项目。"""
    c = _setup_projects_app(tmp_path, monkeypatch)
    pid = c.post("/api/platform/projects", json={"name": "项目D"}).json()["id"]

    # mock 关联计数：patch _count_referenced 返回有引用
    import insight_aitest.platform.api.projects as proj_api

    monkeypatch.setattr(
        proj_api, "_count_referenced", lambda **kw: {"documents": 3, "testcases": 0}
    )

    r = c.delete(f"/api/platform/projects/{pid}")
    assert r.status_code == 409
    assert "文档" in r.json()["detail"]
