# -*- coding: utf-8 -*-
"""
iOS 内存采集器
使用 tidevice 实现无需越狱的 iOS 内存性能数据采集

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
import subprocess
import re
from typing import Optional, Dict
from logzero import logger


class MemoryCollector:
    """
    iOS 内存使用情况采集器

    使用 tidevice perf 命令获取应用的内存使用量
    """

    def __init__(self, udid: str):
        """
        初始化内存采集器

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
                logger.warning("tidevice 未正确安装，内存采集可能不可用")
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
        采集内存使用情况

        Args:
            bundle_id: 应用 Bundle ID (如 com.apple.mobilesafari)

        Returns:
            dict: {
                'totalPass': float,     # 总内存 (MB)
                'nativePass': float,    # Native 内存 (MB)
                'dalvikPass': float,    # Dalvik 内存 (MB，iOS 上为 0)
            } 或 None

        注意：
            - iOS 使用的是 Real Memory (实际物理内存)
            - 返回单位为 MB
            - 如果应用未运行或设备未连接，返回 None
        """
        try:
            # 使用 tidevice perf 获取性能数据
            output = self._run_tidevice(['perf', '--bundleid', bundle_id, '--io'], timeout=5)

            if output:
                # 解析内存数据
                # tidevice perf 输出格式示例:
                # [Device] CPU: 15.2% Memory: 120.5MB
                for line in output.split('\n'):
                    if 'Memory' in line or 'MEM' in line:
                        # 提取内存使用量，支持多种格式
                        # 格式1: Memory: 120.5MB
                        # 格式2: Memory: 120.5 MB
                        # 格式3: Memory: 120500KB
                        match = re.search(r'Memory[:\s]+([\d.]+)\s*(MB|KB)?', line, re.IGNORECASE)
                        if match:
                            memory_value = float(match.group(1))
                            unit = match.group(2)

                            # 转换为 MB
                            if unit and unit.upper() == 'KB':
                                memory_mb = memory_value / 1024
                            else:
                                memory_mb = memory_value

                            # iOS 内存统计
                            # totalPass: 总内存（主要值）
                            # nativePass: Native 堆内存（iOS 上与总内存相同）
                            # dalvikPass: Dalvik 堆内存（iOS 上不存在，返回 0）
                            return {
                                'totalPass': round(memory_mb, 2),
                                'nativePass': round(memory_mb, 2),
                                'dalvikPass': 0.0
                            }

            # 如果无法获取数据，返回默认值
            logger.debug("无法通过 tidevice perf 获取内存数据，可能应用未在前台运行")

            return {
                'totalPass': 0,
                'nativePass': 0,
                'dalvikPass': 0
            }

        except Exception as e:
            logger.error(f"iOS 内存采集失败: {e}")
            return None
