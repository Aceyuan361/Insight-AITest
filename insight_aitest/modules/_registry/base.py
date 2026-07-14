# -*- coding: utf-8 -*-
"""模块可选基类，降低样板代码。不强制使用。"""

from __future__ import annotations

import os

from fastapi import APIRouter

from insight_aitest.modules._registry.manifest import ModuleManifest


class ModuleBase:
    def __init__(self, manifest: ModuleManifest) -> None:
        self.manifest = manifest
        self.router = APIRouter(tags=[manifest.id])

    def get_db(self):
        from insight_aitest.platform.persistence.database import DatabaseManager

        db_path = os.path.join(os.path.expanduser("~"), ".insight_eye", "monitoring.db")
        return DatabaseManager(db_path)

    @property
    def device_manager(self):
        from insight_aitest.platform.services.device_manager import DeviceManager

        return DeviceManager
