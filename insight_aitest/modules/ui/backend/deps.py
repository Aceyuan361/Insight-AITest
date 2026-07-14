# -*- coding: utf-8 -*-
"""ui 模块依赖注入（对标 api/deps.py）。"""

from __future__ import annotations

import os

from insight_aitest.modules.ui.backend.persistence.database import UIRunDatabase
from insight_aitest.modules.ui.backend.persistence.batch_database import UIBatchRunDatabase

_DB_PATH = os.path.expanduser("~/.insight_eye/ui.db")

_run_db: UIRunDatabase | None = None
_batch_db: UIBatchRunDatabase | None = None


def get_run_db() -> UIRunDatabase:
    global _run_db
    if _run_db is None:
        _run_db = UIRunDatabase(_DB_PATH)
    return _run_db


def get_batch_db() -> UIBatchRunDatabase:
    global _batch_db
    if _batch_db is None:
        _batch_db = UIBatchRunDatabase(_DB_PATH)
    return _batch_db
