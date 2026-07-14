# -*- coding: utf-8 -*-
"""环境 CRUD + 克隆/导入导出 API（spec E.1 §4 + 环境管理增强）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from insight_aitest.modules.api.backend.deps import get_env_db
from insight_aitest.modules.api.backend.persistence.environment_database import EnvironmentDatabase

router = APIRouter(prefix="/environments", tags=["api"])


class EnvCreate(BaseModel):
    name: str
    base_url: str
    variables: dict = {}
    variables_meta: dict = {}
    is_default: bool = False


class EnvUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    variables: dict | None = None
    variables_meta: dict | None = None
    is_default: bool | None = None


class CloneRequest(BaseModel):
    new_name: str


def _env_out(env) -> dict:
    return {
        "id": env.id,
        "name": env.name,
        "base_url": env.base_url,
        "variables": env.variables,
        "variables_meta": getattr(env, "variables_meta", None) or {},
        "is_default": env.is_default,
        "created_at": env.created_at.isoformat(),
        "updated_at": env.updated_at.isoformat(),
    }


@router.post("", status_code=201)
async def create_env(body: EnvCreate, db: EnvironmentDatabase = Depends(get_env_db)) -> dict:
    if db.get_by_name(body.name):
        raise HTTPException(409, f"环境名 '{body.name}' 已存在")
    eid = db.create(
        name=body.name, base_url=body.base_url, variables=body.variables,
        variables_meta=body.variables_meta, is_default=body.is_default
    )
    return _env_out(db.get(eid))


@router.get("")
async def list_envs(db: EnvironmentDatabase = Depends(get_env_db)) -> list[dict]:
    return [_env_out(e) for e in db.list()]


# ===== 静态路径，必须在 /{env_id} 之前 =====

@router.get("/export")
async def export_envs(db: EnvironmentDatabase = Depends(get_env_db)) -> Response:
    """导出所有环境为 JSON。"""
    import json
    envs = [_env_out(e) for e in db.list()]
    content = json.dumps(envs, ensure_ascii=False, indent=2, default=str)
    return Response(
        content=content, media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="environments.json"'},
    )


@router.post("/import")
async def import_envs(body: list[dict], db: EnvironmentDatabase = Depends(get_env_db)) -> dict:
    """批量导入环境 JSON。

    已存在的环境名跳过（不覆盖）。
    """
    imported = 0
    skipped = 0
    for item in body:
        name = item.get("name")
        if not name:
            continue
        if db.get_by_name(name):
            skipped += 1
            continue
        db.create(
            name=name,
            base_url=item.get("base_url", ""),
            variables=item.get("variables", {}),
            variables_meta=item.get("variables_meta", {}),
            is_default=False,  # 导入不设默认，避免冲突
        )
        imported += 1
    return {"imported": imported, "skipped": skipped}


@router.get("/{env_id}")
async def get_env(env_id: int, db: EnvironmentDatabase = Depends(get_env_db)) -> dict:
    env = db.get(env_id)
    if not env:
        raise HTTPException(404, "环境不存在")
    return _env_out(env)


@router.put("/{env_id}")
async def update_env(
    env_id: int, body: EnvUpdate, db: EnvironmentDatabase = Depends(get_env_db)
) -> dict:
    if not db.get(env_id):
        raise HTTPException(404, "环境不存在")
    if body.name and db.get_by_name(body.name) and db.get_by_name(body.name).id != env_id:
        raise HTTPException(409, f"环境名 '{body.name}' 已存在")
    db.update(env_id, **body.model_dump(exclude_none=True))
    return _env_out(db.get(env_id))


@router.post("/{env_id}/clone", status_code=201)
async def clone_env(
    env_id: int, body: CloneRequest, db: EnvironmentDatabase = Depends(get_env_db)
) -> dict:
    """克隆环境。"""
    if db.get_by_name(body.new_name):
        raise HTTPException(409, f"环境名 '{body.new_name}' 已存在")
    try:
        new_id = db.clone(env_id, body.new_name)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return _env_out(db.get(new_id))


@router.delete("/{env_id}")
async def delete_env(env_id: int, db: EnvironmentDatabase = Depends(get_env_db)) -> dict:
    if not db.delete(env_id):
        raise HTTPException(404, "环境不存在")
    return {"deleted": env_id}
