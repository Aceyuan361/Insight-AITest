# -*- coding: utf-8 -*-
"""
Insight-Eye Desktop Module
桌面应用模块

此模块包含桌面应用的核心功能:
- core: 设备管理、应用枚举等核心功能
- ui: PyQt6用户界面
- analytics: 性能分析和告警
- data: 数据存储和导出
- main: 应用入口
"""

__version__ = "1.0.0"
__author__ = "Aceyuan361"

from .main import main

__all__ = ['main']
