# -*- coding: utf-8 -*-
"""平台持久层 engine/session 工厂单测（spec P0-1 §8.2）。

覆盖：按 db_path 缓存幂等、scoped_session 线程安全、WAL/foreign_keys PRAGMA 生效、
session_scope 自动 commit/rollback。
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime

import pytest
from sqlalchemy import Text, text
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from insight_aitest.platform.persistence import (
    Base,
    ensure_schema,
    get_engine,
    get_session_factory,
    session_scope,
)
from insight_aitest.platform.persistence.engine import dispose_all

# 每个测试用独立 db_path，并复用 infra 缓存（不 dispose 会跨测试串，故 fixture 清理）


@pytest.fixture(autouse=True)
def _isolate_engine_cache():
    dispose_all()
    yield
    dispose_all()


class _Note(MappedAsDataclass, Base):
    __tablename__ = "persistence_note"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    body: Mapped[str] = mapped_column(Text, default="x")
    created_at: Mapped[datetime] = mapped_column(default_factory=datetime.now)


def _path(tmp_path, name="t.db"):
    return str(tmp_path / name)


def test_engine_cached_per_db_path(tmp_path):
    p = _path(tmp_path)
    assert get_engine(p) is get_engine(p)  # 同 path 同 engine


def test_session_factory_cached_per_db_path(tmp_path):
    p = _path(tmp_path)
    assert get_session_factory(p) is get_session_factory(p)


def test_different_paths_different_engines(tmp_path):
    a, b = _path(tmp_path, "a.db"), _path(tmp_path, "b.db")
    assert get_engine(a) is not get_engine(b)


def test_wal_and_foreign_keys_pragma(tmp_path):
    p = _path(tmp_path)
    e = get_engine(p)
    with e.connect() as conn:
        assert conn.execute(text("PRAGMA journal_mode")).scalar() == "wal"
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_session_scope_commit_on_success(tmp_path):
    p = _path(tmp_path)
    Base.metadata.create_all(get_engine(p))
    with session_scope(p) as s:
        s.add(_Note(body="hello"))
        s.flush()
    # 新 session 读回
    with session_scope(p) as s:
        rows = s.query(_Note).all()
    assert len(rows) == 1
    assert rows[0].body == "hello"


def test_session_scope_rollback_on_exception(tmp_path):
    p = _path(tmp_path)
    Base.metadata.create_all(get_engine(p))
    with pytest.raises(RuntimeError):
        with session_scope(p) as s:
            s.add(_Note(body="will-rollback"))
            s.flush()
            raise RuntimeError("boom")
    with session_scope(p) as s:
        assert s.query(_Note).count() == 0


def test_scoped_session_thread_local(tmp_path):
    """scoped_session：同线程拿同 session，跨线程不同。"""
    p = _path(tmp_path)
    factory = get_session_factory(p)
    s_main = factory()
    other = {}

    def _worker():
        other["s"] = factory()

    t = threading.Thread(target=_worker)
    t.start()
    t.join()
    assert factory() is s_main  # 主线程稳定同 session
    assert other["s"] is not s_main  # 子线程独立 session


def test_ensure_schema_runs_migrators(tmp_path):
    p = _path(tmp_path)
    called = []

    def migrator_a(db_path):
        called.append(("a", db_path))

    def migrator_b(db_path):
        called.append(("b", db_path))

    ensure_schema(p, [migrator_a, migrator_b])
    assert called == [("a", p), ("b", p)]


def test_legacy_isoformat_text_read_by_orm_datetime(tmp_path):
    """旧库存 datetime 存 isoformat TEXT，ORM 原生 DateTime 能读回（spec §0.2）。"""
    p = _path(tmp_path)
    # 用旧 schema 裸 sqlite 建库，created_at 存 isoformat TEXT
    with sqlite3.connect(p) as raw:
        raw.execute("CREATE TABLE legacy_dt (id INTEGER PRIMARY KEY, ts TEXT)")
        raw.execute("INSERT INTO legacy_dt (id, ts) VALUES (1, ?)", (datetime.now().isoformat(),))
        raw.commit()

    class LegacyDT(MappedAsDataclass, Base):
        __tablename__ = "legacy_dt"
        id: Mapped[int] = mapped_column(primary_key=True, init=False)
        ts: Mapped[datetime] = mapped_column()

    with session_scope(p) as s:
        row = s.get(LegacyDT, 1)
    assert isinstance(row.ts, datetime)
