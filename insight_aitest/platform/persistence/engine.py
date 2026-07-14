# -*- coding: utf-8 -*-
"""平台持久层 engine + session 工厂（spec P0-1 §4.3）。

按 db_path 缓存 engine / scoped_session，复刻原 8 个 DB 类各自的
``threading.local() + sqlite3.connect(check_same_thread=False) + PRAGMA WAL`` 语义，
收敛到一处。模块不再各自持有连接。

- ``get_engine(db_path)``：每 .db 文件一个 engine（共享同进程连接池）。
- ``get_session_factory(db_path)``：线程级 scoped_session（等价 threading.local conn）。
- ``ensure_schema(db_path, migrators)``：建表 + 增量 ALTER 的统一入口，
  替代原散落在各 ``_init_schema`` 的 ``ALTER TABLE ... try/except`` hack。
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import scoped_session, sessionmaker

_engines: dict[str, object] = {}
_sessions: dict[str, scoped_session] = {}


def _make_engine(db_path: str):
    db_path = os.path.abspath(db_path)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path}",
        # 复刻原行为：FastAPI 线程池复用连接
        connect_args={"check_same_thread": False},
        future=True,
    )

    # 复刻原 PRAGMA：WAL + foreign_keys（原 KB/AI 已启用，平台层统一）
    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


def get_engine(db_path: str):
    """返回 db_path 对应的 engine（首次创建并缓存）。"""
    db_path = os.path.abspath(db_path)
    if db_path not in _engines:
        _engines[db_path] = _make_engine(db_path)
    return _engines[db_path]


def get_session_factory(db_path: str) -> scoped_session:
    """返回线程级 scoped_session（等价原 threading.local() 连接）。

    ``expire_on_commit=False``：commit 后对象属性仍可访问，匹配原代码 commit 后再读行的模式。
    """
    db_path = os.path.abspath(db_path)
    if db_path not in _sessions:
        factory = sessionmaker(bind=get_engine(db_path), expire_on_commit=False)
        _sessions[db_path] = scoped_session(factory)
    return _sessions[db_path]


def ensure_schema(db_path: str, migrators: list[Callable[[str], None]]) -> None:
    """建表 + 增量 schema 变更的统一入口。

    替代原散落在各 ``_init_schema`` 的 ``ALTER TABLE ... try/except pass`` hack。
    每个 DB 类把建表 (CREATE TABLE IF NOT EXISTS) 和增量 ALTER 封装为
    形如 ``(db_path) -> None`` 的 migrator，统一在此调用。migrator 内部自行幂等。
    """
    for m in migrators:
        m(db_path)


def dispose_all() -> None:
    """关闭并清空所有缓存 engine/session（仅测试用，勿在运行期调用）。"""
    global _engines, _sessions
    # 快照后再操作，避免 dispose/remove 触发回调导致字典在迭代中改变
    sessions = list(_sessions.values())
    engines = list(_engines.values())
    for s in sessions:
        try:
            s.remove()
        except Exception:
            pass
    for e in engines:
        try:
            e.dispose()
        except Exception:
            pass
    _engines = {}
    _sessions = {}
