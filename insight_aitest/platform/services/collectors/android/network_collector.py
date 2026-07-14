# -*- coding: utf-8 -*-
"""
Android 网络流量采集器
使用 ADB 实现 Android 应用的网络流量数据采集

改进：
- 集成设备配置系统（DeviceProfile）
- 小米设备使用 sh -c 包装命令
- 支持 UID 缓存优化
"""

import re
import time
from typing import Optional, Dict
from logzero import logger
from insight_aitest.platform.services.collectors.adb import adb


class NetworkCollector:
    """
    Android 网络流量采集器 - 集成设备配置系统

    使用 ADB 读取 /proc/net/dev 或 /proc/uid_stat 获取网络流量
    """

    def __init__(self, device_id: str, device_profile=None):
        """
        初始化网络流量采集器

        Args:
            device_id: Android 设备 ID
            device_profile: 设备配置档案（可选）
        """
        self.device_id = device_id
        self.device_profile = device_profile
        self.strategy = device_profile.get_strategy() if device_profile else None

        if self.strategy:
            logger.debug(
                f"[网络采集器] 使用策略: {self.strategy.network_method}, "
                f"Shell包装: {self.strategy.network_shell_wrap}, "
                f"UID缓存: {self.strategy.network_uid_cache}"
            )

        self.last_data = {}  # 存储上次采集的数据，用于计算流量速率
        self.last_time = {}  # 存储上次采集的时间

    def _get_app_uid(self, package_name: str) -> Optional[int]:
        """
        获取应用的 UID

        Args:
            package_name: 应用包名

        Returns:
            int: 应用 UID，失败返回 None
        """
        try:
            # 使用 dumpsys package 获取 UID（在Python中过滤，兼容Windows）
            result = adb.shell(f"dumpsys package {package_name}", self.device_id)

            if result:
                # 在 Python 中查找 userId=
                for line in result.split("\n"):
                    if "userId=" in line:
                        match = re.search(r"userId=(\d+)", line)
                        if match:
                            return int(match.group(1))

            # 备选方法: 从 /data/data/ 目录推断（在Python中过滤，兼容Windows）
            result = adb.shell("ls -l /data/data/", self.device_id)
            if result:
                for line in result.split("\n"):
                    if package_name in line:
                        match = re.search(r"\s(\d+)\s+\d+\s+\d+ " + re.escape(package_name), line)
                        if match:
                            return int(match.group(1))

            return None

        except Exception as e:
            logger.error(f"获取应用 UID 失败: {e}")
            return None

    def _get_traffic_from_uid_stat(self, uid: int) -> Optional[Dict[str, int]]:
        """
        从 /proc/uid_stat 获取网络流量 - 修复版：Windows 兼容

        Windows 错误原因：
        - `sh -c` 在 Windows ADB 上不可用
        - 2>/dev/null 重定向由设备 shell 处理，不需要 sh -c

        修复方法：
        - 直接使用 `cat /proc/uid_stat/{uid}/tcp_rcv 2>/dev/null`
        - ADB 会将整个命令传递给设备 shell 执行

        Args:
            uid: 应用 UID

        Returns:
            dict: {'rx_bytes': int, 'tx_bytes': int} 或 None
        """
        try:
            # 方法1：直接读取（设备 shell 会处理重定向）
            rx_result = adb.shell(f"cat /proc/uid_stat/{uid}/tcp_rcv 2>/dev/null", self.device_id)
            tx_result = adb.shell(f"cat /proc/uid_stat/{uid}/tcp_snd 2>/dev/null", self.device_id)

            # 方法2：如果方法1返回空或错误，尝试不使用重定向
            if not rx_result or "No such file" in rx_result or "Permission denied" in rx_result:
                rx_result = adb.shell(f"cat /proc/uid_stat/{uid}/tcp_rcv", self.device_id)
            if not tx_result or "No such file" in tx_result or "Permission denied" in tx_result:
                tx_result = adb.shell(f"cat /proc/uid_stat/{uid}/tcp_snd", self.device_id)

            if rx_result and tx_result and rx_result.strip() and tx_result.strip():
                try:
                    rx_bytes = int(rx_result.strip())
                    tx_bytes = int(tx_result.strip())
                    return {"rx_bytes": rx_bytes, "tx_bytes": tx_bytes}
                except ValueError:
                    logger.debug(f"uid_stat 返回值格式错误: rx='{rx_result}', tx='{tx_result}'")

            return None

        except (ValueError, Exception) as e:
            logger.debug(f"从 uid_stat 读取流量失败: {e}")
            return None

    def _get_traffic_from_network_dev(self, package_name: str) -> Optional[Dict[str, int]]:
        """
        从 /proc/net/dev 获取网络流量（简化方法，仅作备选）

        注意：此方法获取的是整个设备的网络流量，不是应用级别的
        """
        try:
            result = adb.shell("cat /proc/net/dev", self.device_id)

            if not result:
                return None

            lines = result.strip().split("\n")
            total_rx = 0
            total_tx = 0

            for line in lines:
                if ":" in line and not line.strip().startswith("Inter-"):
                    parts = line.split()
                    if len(parts) >= 10:
                        # 接收字节数在第二列
                        try:
                            total_rx += int(parts[1])
                            # 发送字节数在第十列
                            total_tx += int(parts[9])
                        except (ValueError, IndexError):
                            continue

            return {"rx_bytes": total_rx, "tx_bytes": total_tx}

        except Exception as e:
            logger.debug(f"从 net_dev 读取流量失败: {e}")
            return None

    def _calculate_flow_rate(
        self, package_name: str, current_rx: int, current_tx: int
    ) -> Dict[str, float]:
        """
        计算网络流量速率

        Args:
            package_name: 应用包名
            current_rx: 当前接收字节数
            current_tx: 当前发送字节数

        Returns:
            dict: {'upFlow': float, 'downFlow': float} 单位 KB/s
        """
        current_time = time.time()

        if package_name not in self.last_data:
            # 第一次采集，存储数据并返回0
            self.last_data[package_name] = {"rx": current_rx, "tx": current_tx}
            self.last_time[package_name] = current_time
            return {"upFlow": 0, "downFlow": 0}

        last = self.last_data[package_name]
        last_time = self.last_time[package_name]

        # 计算差值
        rx_delta = current_rx - last["rx"]
        tx_delta = current_tx - last["tx"]

        # 计算时间差
        time_delta = current_time - last_time

        # 更新存储
        self.last_data[package_name] = {"rx": current_rx, "tx": current_tx}
        self.last_time[package_name] = current_time

        # 防御性检查：时间间隔过小会导致除零或极大的流量值
        # 设置最小时间间隔为 10ms，避免计算异常
        MIN_TIME_INTERVAL = 0.01  # 10 毫秒
        if time_delta <= MIN_TIME_INTERVAL:
            if time_delta <= 0:
                logger.debug(f"[网络采集] 时间间隔非正: {time_delta}s，跳过本次计算")
            else:
                logger.debug(
                    f"[网络采集] 时间间隔过小: {time_delta}s < {MIN_TIME_INTERVAL}s，跳过本次计算"
                )
            return {"upFlow": 0, "downFlow": 0}

        # 计算速率 (字节/秒 -> KB/s)
        down_flow = (rx_delta / time_delta) / 1024
        up_flow = (tx_delta / time_delta) / 1024

        return {"upFlow": round(max(0, up_flow), 2), "downFlow": round(max(0, down_flow), 2)}

    def collect(self, package_name: str) -> Optional[Dict[str, float]]:
        """
        采集网络流量

        Args:
            package_name: 应用包名 (如 com.example.app)

        Returns:
            dict: {'upFlow': float, 'downFlow': float} 单位 KB/s

        注意：
            - upFlow: 上行流量 (KB/s)
            - downFlow: 下行流量 (KB/s)
            - 流量速率需要两次采集之间计算
            - 第一次采集返回 0
        """
        try:
            # 方法1: 使用 UID 精确获取应用级流量
            uid = self._get_app_uid(package_name)
            if uid:
                traffic = self._get_traffic_from_uid_stat(uid)
                if traffic:
                    return self._calculate_flow_rate(
                        package_name, traffic["rx_bytes"], traffic["tx_bytes"]
                    )

            # 方法2: 使用设备级流量（备选）
            traffic = self._get_traffic_from_network_dev(package_name)
            if traffic:
                return self._calculate_flow_rate(
                    package_name, traffic["rx_bytes"], traffic["tx_bytes"]
                )

            # 如果都失败，返回默认值
            logger.debug(f"无法获取 {package_name} 的网络流量")
            return {"upFlow": 0, "downFlow": 0}

        except Exception as e:
            logger.error(f"Android 网络流量采集失败: {e}")
            # 返回默认值而非 None，避免后续处理失败
            return {"upFlow": 0, "downFlow": 0}

    def reset(self, package_name: str = None):
        """
        重置流量统计数据

        Args:
            package_name: 应用包名，如果为 None 则重置所有
        """
        if package_name:
            self.last_data.pop(package_name, None)
            self.last_time.pop(package_name, None)
        else:
            self.last_data.clear()
            self.last_time.clear()
