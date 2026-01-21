# -*- coding: utf-8 -*-
"""
iOS 电池采集器 (已弃用)

.. deprecated::
    请使用 py-ios-device 架构（PyIOSConnection + EnergyCollector）
    此类仅为向后兼容保留，将在未来版本中移除。

使用 tidevice 实现无需越狱的 iOS 电池数据采集

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
import subprocess
from typing import Optional, Dict, Any
from logzero import logger


class BatteryCollector:
    """
    iOS 电池状态采集器（已弃用）

    .. deprecated::
        请使用 py-ios-device 架构（PyIOSConnection + EnergyCollector）
        此类仅为向后兼容保留，将在未来版本中移除。

    使用 tidevice info 命令获取设备的电池信息
    """

    def __init__(self, udid: str):
        """
        初始化电池采集器

        Args:
            udid: iOS 设备唯一标识符
        """
        logger.warning("[DEPRECATED] BatteryCollector 已弃用，请使用 py-ios-device 架构")
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
                logger.warning("tidevice 未正确安装，电池采集可能不可用")
        except FileNotFoundError:
            logger.warning("未找到 tidevice 命令，请安装: pip install tidevice")

    def _run_tidevice(self, args: list, timeout: int = 30) -> Optional[str]:
        """
        执行 tidevice 命令

        Args:
            args: 命令参数列表
            timeout: 超时时间（秒）

        Returns:
            str: 命令输出，失败返回 None
        """
        try:
            cmd = ['tidevice', '--udid', self.udid] + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                logger.error(f"tidevice 命令失败: {result.stderr}")
                return None

            return result.stdout

        except subprocess.TimeoutExpired:
            logger.error(f"tidevice 命令超时: {' '.join(args)}")
            return None
        except FileNotFoundError:
            logger.error("未找到 tidevice 命令，请安装: pip install tidevice")
            return None
        except Exception as e:
            logger.error(f"tidevice 执行异常: {e}")
            return None

    def collect(self) -> Optional[Dict[str, Any]]:
        """
        采集电池状态

        Returns:
            dict: {
                'level': int,           # 电量百分比
                'temperature': float,   # 温度 (°C)
                'current': float,       # 电流 (mA)
                'voltage': float,       # 电压 (V)
                'power': float,         # 功率 (W)
                'status': str,          # 充电状态
            } 或 None

        注意：
            - tidevice info 输出包含设备信息但不包含详细电池信息
            - 需要使用其他方式获取详细的电池数据
            - 目前返回默认值
        """
        try:
            output = self._run_tidevice(['info'])
            if not output:
                return None

            # 解析设备信息获取电池数据
            result = {
                'level': 0,
                'temperature': 0,
                'current': 0,
                'voltage': 0,
                'power': 0,
                'status': 'unknown'
            }

            # tidevice info 输出包含设备信息但不包含详细电池信息
            # 需要使用其他方式获取
            logger.debug("iOS 电池详细信息采集暂不支持，返回默认值")

            return result

        except Exception as e:
            logger.error(f"iOS 电池采集失败: {e}")
            return None
