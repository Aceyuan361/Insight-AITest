# -*- coding: utf-8 -*-
"""
配置管理模块

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License
"""

from .config_manager import (
    ConfigManager,
    AppConfig,
    UIConfig,
    DeviceConfig,
    get_config_manager
)

__all__ = [
    'ConfigManager',
    'AppConfig',
    'UIConfig',
    'DeviceConfig',
    'get_config_manager'
]
