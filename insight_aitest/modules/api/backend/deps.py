# -*- coding: utf-8 -*-
"""api 模块依赖注入。"""

from __future__ import annotations

import os

from insight_aitest.modules.api.backend.persistence.database import RunDatabase
from insight_aitest.modules.api.backend.persistence.environment_database import EnvironmentDatabase
from insight_aitest.modules.api.backend.persistence.suite_database import (
    SuiteDatabase,
    SuiteRunDatabase,
)

_DB_PATH = os.path.expanduser("~/.insight_eye/api.db")

_run_db: RunDatabase | None = None
_env_db: EnvironmentDatabase | None = None
_suite_db: SuiteDatabase | None = None
_suite_run_db: SuiteRunDatabase | None = None


def get_run_db() -> RunDatabase:
    global _run_db
    if _run_db is None:
        _run_db = RunDatabase(_DB_PATH)
    return _run_db


def get_env_db() -> EnvironmentDatabase:
    global _env_db
    if _env_db is None:
        _env_db = EnvironmentDatabase(_DB_PATH)
    return _env_db


def get_suite_db() -> SuiteDatabase:
    global _suite_db
    if _suite_db is None:
        _suite_db = SuiteDatabase(_DB_PATH)
    return _suite_db


def get_suite_run_db() -> SuiteRunDatabase:
    global _suite_run_db
    if _suite_run_db is None:
        _suite_run_db = SuiteRunDatabase(_DB_PATH)
    return _suite_run_db
