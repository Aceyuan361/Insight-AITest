# -*- coding: utf-8 -*-
"""pytest 共享夹具（spec P0-1）。

P0-1 引入平台级 engine/session 缓存（按 db_path 缓存），跨测试会残留指向已删除
tmp 目录的 engine，导致后续测试的 ``Base.metadata.create_all`` 误在旧库上建表
（"table already exists"）。本 autouse fixture 每个测试前清空缓存，保证隔离。
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_persistence_engine_cache():
    from insight_aitest.platform.persistence.engine import dispose_all

    dispose_all()
    yield
    dispose_all()
