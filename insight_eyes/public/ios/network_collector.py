# -*- coding: utf-8 -*-
"""
iOS 网络流量采集器
使用 tidevice 实现无需越狱的 iOS 网络流量数据采集

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
import subprocess
from typing import Optional, Dict
from logzero import logger


class NetworkCollector:
    """
    iOS 网络流量采集器

    注意：
        - iOS 网络流量采集受到系统限制
        - 目前 tidevice 不直接支持网络流量采集
        - 返回默认值 0
    """

    def __init__(self, udid: str):
        """
        初始化网络流量采集器

        Args:
            udid: iOS 设备唯一标识符
        """
        self.udid = udid
        self._check_tidevice()

    def _check_tidevice(self):
        """检查 tidevice 是否可用"""
        try:
            result = subprocess.run(
                ['tidevice', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"tidevice 可用: {result.stdout.strip()}")
            else:
                logger.warning("tidevice 未正确安装，网络流量采集可能不可用")
        except FileNotFoundError:
            logger.warning("未找到 tidevice 命令，请安装: pip install tidevice")

    def collect(self, bundle_id: str) -> Optional[Dict[str, float]]:
        """
        采集网络流量

        Args:
            bundle_id: 应用 Bundle ID (如 com.apple.mobilesafari)

        Returns:
            dict: {'upFlow': float, 'downFlow': float} 单位 KB/s

        注意：
            - iOS 网络流量采集需要使用 tidevice perf 或其他方式
            - 目前 tidevice 暂不支持 iOS 网络流量采集
            - 返回默认值 0
        """
        try:
            # iOS 网络流量采集需要使用 tidevice perf 或其他方式
            # 目前暂不支持，返回默认值
            logger.warning("iOS 网络流量采集暂不支持，返回默认值 0 (tidevice 限制)")

            return {
                'upFlow': 0,
                'downFlow': 0
            }

        except Exception as e:
            logger.error(f"iOS 网络流量采集失败: {e}")
            return None
