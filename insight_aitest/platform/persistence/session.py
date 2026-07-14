# -*- coding: utf-8 -*-
"""平台持久层事务上下文（spec P0-1 §4.4）。

``session_scope`` 替代原 8 个 DB 类各自的 ``@contextmanager transaction()``：
退出自动 commit，异常自动 rollback，并清理 scoped_session 的线程绑定。
"""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy.orm import Session

from insight_aitest.platform.persistence.engine import get_session_factory


@contextmanager
def session_scope(db_path: str):
    """事务上下文（等价原 ``with db.transaction() as conn``）。

    用法::

        with session_scope(db_path) as s:
            s.add(obj)        # 退出自动 commit，异常自动 rollback
    """
    factory = get_session_factory(db_path)
    s: Session = factory()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
        factory.remove()  # 清理 scoped_session 线程绑定
