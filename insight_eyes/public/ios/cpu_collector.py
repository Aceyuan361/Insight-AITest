# -*- coding: utf-8 -*-
"""
iOS CPU 采集器
使用 tidevice 实现无需越狱的 iOS CPU 性能数据采集

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
import subprocess
import re
from typing import Optional, Dict
from logzero import logger


class CPUCollector:
    """
    iOS CPU 使用率采集器

    使用 tidevice perf 命令获取应用的 CPU 使用率
    """

    def __init__(self, udid: str):
        """
        初始化 CPU 采集器

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
                logger.warning("tidevice 未正确安装，CPU 采集可能不可用")
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

    def collect(self, bundle_id: str) -> Optional[Dict[str, float]]:
        """
        采集 CPU 使用率

        Args:
            bundle_id: 应用 Bundle ID (如 com.apple.mobilesafari)

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float} 或 None

        注意：
            - tidevice perf --io 需要应用在前台运行
            - CPU 使用率以百分比形式返回
            - 如果应用未运行或设备未连接，返回 None
        """
        try:
            # 使用 tidevice perf 获取性能数据
            # tidevice perf 命令会持续输出应用的性能指标
            output = self._run_tidevice(['perf', '--bundleid', bundle_id, '--io'], timeout=5)

            if output:
                # 解析 CPU 数据
                # tidevice perf 输出格式示例:
                # [Device] CPU: 15.2% Memory: 120.5MB
                for line in output.split('\n'):
                    if 'CPU' in line:
                        # 提取 CPU 使用率
                        match = re.search(r'CPU[:\s]+([\d.]+)%', line)
                        if match:
                            cpu_rate = float(match.group(1))
                            # iOS 不区分应用和系统 CPU，返回相同的值
                            return {
                                'appCpuRate': round(cpu_rate, 2),
                                'sysCpuRate': round(cpu_rate, 2)
                            }

            # 如果无法获取数据，返回默认值
            logger.debug("无法通过 tidevice perf 获取 CPU 数据，可能应用未在前台运行")

            return {
                'appCpuRate': 0.0,
                'sysCpuRate': 0.0
            }

        except Exception as e:
            logger.error(f"iOS CPU 采集失败: {e}")
            return None
