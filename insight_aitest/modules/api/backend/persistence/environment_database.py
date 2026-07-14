# -*- coding: utf-8 -*-
"""环境数据库（EnvironmentDatabase，spec E.1 §2 + P0-1 ORM 迁移）。

复用 api.db（与 runs/suite_runs 同库）。单默认约束：is_default 全表至多一个 true。

P0-1：从裸 sqlite3 + threading.local 迁移到平台 session_scope + ORM。
对外方法签名/返回类型完全不变（routes/tests 零改动）。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update

from insight_aitest.platform.persistence import Base, get_engine, session_scope
from insight_aitest.modules.api.backend.persistence.environment_models import Environment


class EnvironmentDatabase:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Base.metadata.create_all(get_engine(db_path), tables=[Environment.__table__])
        self._ensure_variables_meta_column()

    def _ensure_variables_meta_column(self) -> None:
        """增量迁移：旧库可能没有 variables_meta_json 列。"""
        from sqlalchemy import inspect, text

        engine = get_engine(self.db_path)
        inspector = inspect(engine)
        if Environment.__table__.name not in inspector.get_table_names():
            return
        existing_cols = {c["name"] for c in inspector.get_columns(Environment.__table__.name)}
        if "variables_meta_json" not in existing_cols:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE environments ADD COLUMN variables_meta_json JSON"))
                conn.commit()

    def _clear_default(self) -> None:
        with session_scope(self.db_path) as s:
            s.execute(update(Environment).values(is_default=False))

    def create(
        self, *, name: str, base_url: str, variables: dict | None = None,
        variables_meta: dict | None = None, is_default: bool = False
    ) -> int:
        if is_default:
            self._clear_default()
        env = Environment(
            name=name,
            base_url=base_url,
            variables=variables or {},
            variables_meta=variables_meta or {},
            is_default=is_default,
        )
        with session_scope(self.db_path) as s:
            s.add(env)
            s.flush()
            return env.id

    def get(self, env_id: int) -> Environment | None:
        with session_scope(self.db_path) as s:
            return s.get(Environment, env_id)

    def get_by_name(self, name: str) -> Environment | None:
        stmt = select(Environment).where(Environment.name == name)
        with session_scope(self.db_path) as s:
            return s.scalars(stmt).first()

    def get_default(self) -> Environment | None:
        """返回 is_default=True 的环境（用于执行时自动选用）。"""
        stmt = select(Environment).where(Environment.is_default == True)  # noqa: E712
        with session_scope(self.db_path) as s:
            return s.scalars(stmt).first()

    def list(self) -> list[Environment]:
        stmt = select(Environment).order_by(Environment.id)
        with session_scope(self.db_path) as s:
            return list(s.scalars(stmt))

    def clone(self, env_id: int, new_name: str) -> int:
        """克隆环境（复制所有字段，新名称）。"""
        src = self.get(env_id)
        if src is None:
            raise ValueError(f"环境 {env_id} 不存在")
        return self.create(
            name=new_name,
            base_url=src.base_url,
            variables=dict(src.variables or {}),
            variables_meta=dict(src.variables_meta or {}),
            is_default=False,  # 克隆不设为默认
        )

    def update(self, env_id: int, **fields) -> None:
        allowed = ("name", "base_url", "variables", "variables_meta", "is_default")
        if "is_default" in fields and fields["is_default"]:
            self._clear_default()
        with session_scope(self.db_path) as s:
            env = s.get(Environment, env_id)
            if env is None:
                return
            for k in allowed:
                if k not in fields or fields[k] is None:
                    continue
                setattr(env, k, fields[k])
            env.updated_at = datetime.now()

    def delete(self, env_id: int) -> bool:
        with session_scope(self.db_path) as s:
            env = s.get(Environment, env_id)
            if env is None:
                return False
            s.delete(env)
            return True
