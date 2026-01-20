# -*- coding: utf-8 -*-
"""
iOS 依赖检测器
检测 py-ios-device 和 pymobiledevice3 是否可用

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
import subprocess
from typing import Tuple, Optional
from logzero import logger


class IOSDependencyChecker:
    """
    iOS 依赖检测器

    检测 iOS 高级监控所需的依赖：
    - py-ios-device: 核心 iOS 性能数据采集库
    - pymobiledevice3: iOS 17+ 远程隧道连接库

    支持版本：
    - iOS 15-16: 使用 tidevice（基础支持）
    - iOS 17-26: 使用 py-ios-device + pymobiledevice3（完整支持）
    """

    # 依赖缓存（避免重复检查）
    _pyios_available: Optional[bool] = None
    _pymobiledevice3_available: Optional[bool] = None

    @classmethod
    def check_pyios_device(cls) -> bool:
        """
        检查 py-ios-device 是否可用

        Returns:
            bool: py-ios-device 是否可用
        """
        # 使用缓存
        if cls._pyios_available is not None:
            return cls._pyios_available

        try:
            import py_ios_device
            cls._pyios_available = True
            logger.info(f"[依赖检测] ✓ py-ios-device 可用 (版本: {getattr(py_ios_device, '__version__', 'unknown')})")
            return True
        except ImportError:
            cls._pyios_available = False
            logger.debug("[依赖检测] ✗ py-ios-device 未安装")
            return False

    @classmethod
    def check_pymobiledevice3(cls) -> bool:
        """
        检查 pymobiledevice3 是否可用

        Returns:
            bool: pymobiledevice3 是否可用
        """
        # 使用缓存
        if cls._pymobiledevice3_available is not None:
            return cls._pymobiledevice3_available

        try:
            import pymobiledevice3
            cls._pymobiledevice3_available = True
            logger.info(f"[依赖检测] ✓ pymobiledevice3 可用 (版本: {getattr(pymobiledevice3, '__version__', 'unknown')})")
            return True
        except ImportError:
            cls._pymobiledevice3_available = False
            logger.debug("[依赖检测] ✗ pymobiledevice3 未安装")
            return False

    @classmethod
    def check_all(cls) -> Tuple[bool, bool]:
        """
        检查所有 iOS 高级依赖

        Returns:
            tuple: (pyios_available, pymobiledevice3_available)
        """
        pyios = cls.check_pyios_device()
        pmd3 = cls.check_pymobiledevice3()
        return pyios, pmd3

    @classmethod
    def has_full_support(cls) -> bool:
        """
        检查是否具有完整的 iOS 监控支持

        Returns:
            bool: 是否具有完整支持（需要两个依赖都可用）
        """
        pyios, pmd3 = cls.check_all()
        return pyios and pmd3

    @classmethod
    def suggest_ios_full_support(cls):
        """
        提示用户安装完整 iOS 支持

        当检测到 iOS 17+ 设备但缺少依赖时，显示安装提示
        """
        logger.warning("")
        logger.warning("=" * 60)
        logger.warning("检测到 iOS 17+ 设备，建议安装完整 iOS 支持")
        logger.warning("")
        logger.warning("安装命令：")
        logger.warning("  pip install py-ios-device")
        logger.warning("  pip install pymobiledevice3")
        logger.warning("  pip install 'pymobiledevice3[openssl]'")
        logger.warning("")
        logger.warning("或使用项目 extras 安装：")
        logger.warning("  pip install -e '.[ios-full]'")
        logger.warning("=" * 60)
        logger.warning("")

    @classmethod
    def clear_cache(cls):
        """
        清除依赖检测缓存

        在重新安装依赖后，需要清除缓存以重新检测
        """
        cls._pyios_available = None
        cls._pymobiledevice3_available = None
        logger.debug("[依赖检测] 缓存已清除")
