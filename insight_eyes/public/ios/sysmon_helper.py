# -*- coding: utf-8 -*-
"""
iOS Sysmon 辅助类

封装 pymobiledevice3 developer dvt sysmon 命令行调用，
用于获取 iOS 进程的真实性能数据。

注意：需要 Developer Mode 已启用且 DeveloperDiskImage 已挂载。

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License
"""

import subprocess
import json
from typing import Dict, List, Optional
from logzero import logger


class SysmonHelper:
    """iOS Sysmon 辅助类"""

    def __init__(self, udid: str = None):
        """
        初始化 Sysmon 辅助类

        Args:
            udid: iOS 设备唯一标识符
        """
        self.udid = udid
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        """检查 sysmon 服务是否可用"""
        try:
            result = subprocess.run(
                ['pymobiledevice3', 'developer', 'dvt', 'sysmon', 'process', 'single'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                processes = json.loads(result.stdout)
                logger.info(f"Sysmon 服务可用，检测到 {len(processes)} 个进程")
                return True
            else:
                logger.warning(f"Sysmon 服务不可用: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"检查 Sysmon 服务失败: {e}")
            return False

    def get_process_by_bundle_id(self, bundle_id: str) -> Optional[Dict]:
        """
        根据 Bundle ID 获取进程信息

        Args:
            bundle_id: 应用的 Bundle ID (如 com.example.app)

        Returns:
            进程信息字典，如果未找到则返回 None
        """
        if not self._available:
            return None

        try:
            result = subprocess.run(
                ['pymobiledevice3', 'developer', 'dvt', 'sysmon', 'process', 'single'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.error(f"获取进程列表失败: {result.stderr}")
                return None

            processes = json.loads(result.stdout)

            # 查找匹配的进程
            for process in processes:
                # 匹配 execName 或 comm 字段
                exec_name = process.get('execName', '')
                comm = process.get('comm', '')
                name = process.get('name', '')

                if (bundle_id in exec_name or
                    bundle_id in comm or
                    bundle_id in name):
                    logger.debug(f"找到进程: {bundle_id} (PID: {process.get('pid')})")
                    return process

            logger.warning(f"未找到 Bundle ID 为 {bundle_id} 的进程")
            return None

        except json.JSONDecodeError as e:
            logger.error(f"解析进程列表 JSON 失败: {e}")
            return None
        except Exception as e:
            logger.error(f"获取进程信息失败: {e}")
            return None

    def get_process_by_pid(self, pid: int) -> Optional[Dict]:
        """
        根据 PID 获取进程信息

        Args:
            pid: 进程 ID

        Returns:
            进程信息字典，如果未找到则返回 None
        """
        if not self._available:
            return None

        try:
            result = subprocess.run(
                ['pymobiledevice3', 'developer', 'dvt', 'sysmon', 'process', 'single'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return None

            processes = json.loads(result.stdout)

            for process in processes:
                if process.get('pid') == pid:
                    return process

            return None

        except Exception as e:
            logger.error(f"根据 PID 获取进程失败: {e}")
            return None

    def get_energy_stats(self, pid: int) -> Optional[Dict]:
        """
        获取进程的能耗统计

        Args:
            pid: 进程 ID

        Returns:
            能耗数据字典，如果失败则返回 None
        """
        if not self._available:
            return None

        try:
            result = subprocess.run(
                ['pymobiledevice3', 'developer', 'dvt', 'energy', str(pid)],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode != 0:
                logger.debug(f"获取能耗数据失败: {result.stderr}")
                return None

            # 能耗监控会持续输出，读取最后一行
            lines = result.stdout.strip().split('\n')
            if lines:
                # 最后一行包含最新的能耗数据
                last_line = lines[-1]
                if '{' in last_line:
                    start = last_line.find('{')
                    energy_data = json.loads(last_line[start:])
                    if str(pid) in energy_data:
                        return energy_data[str(pid)]

            return None

        except Exception as e:
            logger.debug(f"获取能耗统计失败: {e}")
            return None

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._available

    @staticmethod
    def parse_cpu_usage(process: Dict) -> float:
        """
        从进程信息中解析 CPU 使用率

        Args:
            process: 进程信息字典

        Returns:
            CPU 使用率（百分比）
        """
        cpu_usage = process.get('cpuUsage', 0.0)
        return float(cpu_usage) if cpu_usage else 0.0

    @staticmethod
    def parse_memory_usage(process: Dict) -> Dict[str, float]:
        """
        从进程信息中解析内存使用情况

        Args:
            process: 进程信息字典

        Returns:
            {'used_mb': float, 'total_mb': float, 'percentage': float}
        """
        # 优先使用 physFootprint（物理足迹）
        phys_footprint = process.get('physFootprint', 0)
        resident_size = process.get('memResidentSize', 0)

        # 以字节为单位的内存使用量
        used_bytes = physFootprint if physFootprint > 0 else resident_size

        used_mb = used_bytes / 1024 / 1024

        # 总内存 - 使用固定值 4GB，因为 iOS 不提供真实总量
        total_mb = 4 * 1024

        percentage = (used_mb / total_mb * 100) if total_mb > 0 else 0

        return {
            'used_mb': round(used_mb, 2),
            'total_mb': float(total_mb),
            'percentage': round(percentage, 2)
        }
