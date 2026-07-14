# -*- coding: utf-8 -*-
"""
iOS 性能指标频率控制层

负责处理从 SysmonStreamService 持续接收的数据，并提供按设定频率聚合的指标。

功能：
1. 异常数据过滤（只过滤明显非法值）
2. 时间窗口累加（环形缓冲区）
3. 按设定频率聚合数据
"""

import math
import time
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from logzero import logger


@dataclass
class SecondBucket:
    """一秒内的数据桶

    存储某一秒内接收到的所有 CPU 和内存数据点。
    """

    second_timestamp: int  # Unix 时间戳（秒）
    cpu_values: List[float] = field(default_factory=list)
    memory_values: List[float] = field(default_factory=list)

    def has_valid_data(self) -> bool:
        """是否有有效数据"""
        return bool(self.cpu_values or self.memory_values)

    def clear(self):
        """清空数据"""
        self.cpu_values.clear()
        self.memory_values.clear()


class DataValidator:
    """异常数据快速过滤器

    只过滤明显非法的值，不过滤合法的 0 值（应用可能真的空闲）。
    """

    @staticmethod
    def validate_cpu(value: float) -> bool:
        """验证 CPU 数据是否有效

        快速路径，O(1) 时间复杂度。

        过滤规则：
        - None 值
        - 非数值类型
        - NaN
        - 超出物理范围（< 0 或 > 100）

        注意：CPU = 0 是合法的（应用空闲），不过滤。

        Args:
            value: CPU 使用率值

        Returns:
            bool: 是否有效
        """
        # None 检查
        if value is None:
            return False

        # 类型检查
        if not isinstance(value, (int, float)):
            return False

        # NaN 检查
        if math.isnan(value):
            return False

        # 范围检查: CPU 必须在 [0, 100] 之间
        if value < 0.0 or value > 100.0:
            return False

        return True

    @staticmethod
    def validate_memory_mb(value: float) -> bool:
        """验证内存数据是否有效（单位：MB）

        过滤规则：
        - None 值
        - 非数值类型
        - NaN
        - <= 0（内存不能为 0 或负数）
        - > 8192（最大 8GB）

        Args:
            value: 内存使用量（MB）

        Returns:
            bool: 是否有效
        """
        if value is None:
            return False

        if not isinstance(value, (int, float)):
            return False

        if math.isnan(value):
            return False

        # 内存不能为 0 或负数
        if value <= 0.0:
            return False

        # 最大 8GB
        if value > 8192.0:
            return False

        return True


class TimeWindowAccumulator:
    """时间窗口累加器（环形缓冲区）

    只保留固定时间的原始秒级数据，超出部分自动覆盖。

    特性：
    - O(1) 追加数据
    - 环形缓冲区，自动覆盖旧数据
    - 支持按任意频率聚合
    - 线程安全
    """

    def __init__(self, window_seconds: int = 120):
        """初始化时间窗口累加器

        Args:
            window_seconds: 保留多少秒的原始数据
                           - 需要大于用户设置的最大采集频率
                           - 默认 120 秒足够支持 1-60 秒的采集频率
        """
        self._window_seconds = window_seconds
        self._buckets: List[SecondBucket] = [SecondBucket(0) for _ in range(window_seconds)]
        self._lock = threading.RLock()
        # 上次有效值缓存（用于避免无数据时返回 0 导致曲线波动）
        self._last_valid_cpu: Optional[float] = None
        self._last_valid_memory: Optional[float] = None
        logger.debug(f"时间窗口累加器初始化: 窗口大小={window_seconds}秒")

    def add(self, cpu: float, memory_mb: float) -> bool:
        """添加数据点到当前秒

        超出窗口大小的旧数据会自动被覆盖（环形缓冲区特性）。

        Args:
            cpu: CPU 使用率
            memory_mb: 内存使用量（MB）

        Returns:
            bool: 是否成功添加
        """
        with self._lock:
            current_second = int(time.time())
            idx = current_second % self._window_seconds

            bucket = self._buckets[idx]

            # 如果这一秒是新的一秒，清空旧数据
            if bucket.second_timestamp != current_second:
                self._buckets[idx] = SecondBucket(current_second)
                bucket = self._buckets[idx]

            # 添加数据（先验证）
            added = False
            cpu_valid = DataValidator.validate_cpu(cpu)
            mem_valid = DataValidator.validate_memory_mb(memory_mb)

            # 调试日志
            if cpu_valid or mem_valid:
                logger.debug(
                    f"[TimeWindow] 添加数据: second={current_second}, cpu={cpu}(valid={cpu_valid}), memory={memory_mb:.2f}(valid={mem_valid})"
                )

            if cpu_valid:
                bucket.cpu_values.append(cpu)
                added = True

            if mem_valid:
                bucket.memory_values.append(memory_mb)
                added = True

            return added

    def get_aggregated_data(self, frequency_seconds: int) -> Dict[str, float]:
        """聚合指定频率的数据

        聚合策略：
        1. 每秒内多个数据点：
           - CPU: 取平均值
           - Memory: 取峰值
        2. 多秒聚合：
           - CPU: 再次取平均（平滑处理）
           - Memory: 取峰值（反映最高占用）

        Args:
            frequency_seconds: 聚合多少秒的数据

        Returns:
            {'cpu_app': float, 'used_mb': float}
        """
        with self._lock:
            now = int(time.time())

            # 修正：查询当前秒往前 N 秒的数据（包含当前秒）
            # 例如：now=100, frequency=1，则查询 [100]
            #       now=100, frequency=5，则查询 [96, 97, 98, 99, 100]
            end_second = now  # 包含当前秒
            start_second = end_second - frequency_seconds + 1

            cpu_list = []
            memory_list = []

            # 调试日志
            logger.debug(
                f"[聚合] 查询时间范围: [{start_second}, {end_second}], 频率={frequency_seconds}秒"
            )

            # 遍历时间窗口，收集每秒的聚合数据
            for sec in range(start_second, end_second + 1):
                idx = sec % self._window_seconds
                bucket = self._buckets[idx]

                # 调试日志：显示每秒的数据情况
                if bucket.second_timestamp == sec:
                    cpu_count = len(bucket.cpu_values)
                    mem_count = len(bucket.memory_values)
                    logger.debug(f"[聚合] 第{sec}秒: cpu_count={cpu_count}, mem_count={mem_count}")
                else:
                    logger.debug(
                        f"[聚合] 第{sec}秒: 时间戳不匹配 (bucket={bucket.second_timestamp}, query={sec})"
                    )
                    continue

                if bucket.has_valid_data():
                    # 每秒内聚合
                    if bucket.cpu_values:
                        sec_cpu_avg = sum(bucket.cpu_values) / len(bucket.cpu_values)
                        cpu_list.append(sec_cpu_avg)
                        logger.debug(
                            f"[聚合] 第{sec}秒 CPU 平均: {sec_cpu_avg:.2f}% (来自 {cpu_count} 个数据点)"
                        )

                    if bucket.memory_values:
                        sec_memory_max = max(bucket.memory_values)
                        memory_list.append(sec_memory_max)
                        logger.debug(f"[聚合] 第{sec}秒 Memory 峰值: {sec_memory_max:.2f}MB")

            # 调试日志：显示聚合结果
            logger.debug(
                f"[聚合] 总计: cpu_list长度={len(cpu_list)}, memory_list长度={len(memory_list)}"
            )

            # 跨秒聚合
            if cpu_list:
                final_cpu = sum(cpu_list) / len(cpu_list)
                # 更新上次有效值缓存
                self._last_valid_cpu = final_cpu
                logger.debug(f"[聚合] CPU 最终平均: {final_cpu:.2f}%")
            else:
                # 如果没有有效数据，使用上次有效值
                if self._last_valid_cpu is not None:
                    final_cpu = self._last_valid_cpu
                    logger.debug(f"[聚合] CPU 无新数据，使用上次有效值: {final_cpu:.2f}%")
                else:
                    # 如果从未有过有效数据，返回 0.0
                    final_cpu = 0.0
                    logger.debug("[聚合] CPU 从无有效数据，返回 0.0")

            if memory_list:
                final_memory = max(memory_list)
                # 更新上次有效值缓存
                self._last_valid_memory = final_memory
                logger.debug(f"[聚合] Memory 最终峰值: {final_memory:.2f}MB")
            else:
                # 如果没有有效数据，使用上次有效值
                if self._last_valid_memory is not None:
                    final_memory = self._last_valid_memory
                    logger.debug(f"[聚合] Memory 无新数据，使用上次有效值: {final_memory:.2f}MB")
                else:
                    # 如果从未有过有效数据，返回 0.0
                    final_memory = 0.0
                    logger.debug("[聚合] Memory 从无有效数据，返回 0.0")

            return {"cpu_app": round(final_cpu, 2), "used_mb": round(final_memory, 2)}

    def get_recent_seconds_count(self, seconds: int) -> int:
        """获取最近 N 秒中有多少秒有有效数据

        Args:
            seconds: 查询最近多少秒

        Returns:
            有有效数据的秒数
        """
        with self._lock:
            now = int(time.time())
            count = 0

            for i in range(seconds):
                sec = now - 1 - i
                idx = sec % self._window_seconds
                bucket = self._buckets[idx]

                if bucket.second_timestamp == sec and bucket.has_valid_data():
                    count += 1

            return count

    def clear(self):
        """清空所有数据"""
        with self._lock:
            for bucket in self._buckets:
                bucket.clear()
            # 清空上次有效值缓存
            self._last_valid_cpu = None
            self._last_valid_memory = None
            logger.debug("时间窗口累加器已清空")


class MetricsThrottle:
    """频率控制层 - 对外接口

    负责：
    1. 接收 SysmonStreamService 持续推送的原始数据
    2. 维护时间窗口累加器
    3. 提供按设定频率获取聚合数据的接口
    """

    def __init__(self, target_frequency: float = 1.0):
        """初始化频率控制层

        Args:
            target_frequency: 目标采集频率（秒），例如 1.0 表示每秒采集一次
        """
        self._target_frequency = target_frequency
        self._accumulator = TimeWindowAccumulator(window_seconds=120)
        self._process_cache: Dict[int, Dict] = {}  # {pid: {name, cpu, memory}}
        self._cache_lock = threading.RLock()
        self._last_data_time = 0.0
        self._target_bundle_id: Optional[str] = None  # 目标应用的 Bundle ID
        self._target_pid: Optional[int] = None  # 目标进程的 PID
        logger.debug(f"频率控制层初始化: 目标频率={target_frequency}秒")

    def on_raw_batch(self, process_list: List[Dict]):
        """接收原始数据批次（由 SysmonStreamService 调用）

        Args:
            process_list: 进程列表，每个进程包含 pid, name, cpuUsage, physFootprint 等字段
        """
        if not process_list:
            return

        current_time = time.time()
        self._last_data_time = current_time

        with self._cache_lock:
            for proc in process_list:
                pid = proc.get("pid")
                if pid is None:
                    continue

                # 更新进程缓存
                self._process_cache[pid] = {
                    "pid": pid,
                    "name": proc.get("name", ""),
                    "execName": proc.get("execName", ""),
                    "comm": proc.get("comm", ""),
                }

                # 提取 CPU 和内存数据
                cpu = proc.get("cpuUsage", 0.0)
                phys_footprint = proc.get("physFootprint", 0)
                memory_mb = phys_footprint / 1024 / 1024 if phys_footprint > 0 else 0.0

                # 调试日志：显示接收到的原始数据
                logger.debug(
                    f"[Throttle] 接收原始数据: pid={pid}, name={proc.get('name')}, cpuUsage={cpu}, physFootprint={phys_footprint}, memory_mb={memory_mb:.2f}"
                )

                # 关键修复：只累加目标进程的数据
                # 如果已设置目标 PID，只累加目标进程
                if self._target_pid is not None:
                    if pid == self._target_pid:
                        self._accumulator.add(cpu, memory_mb)
                # 否则累加所有数据（兼容模式）
                else:
                    self._accumulator.add(cpu, memory_mb)

    def get_metrics(self, bundle_id: str, target_pid: Optional[int] = None) -> Dict[str, float]:
        """获取聚合后的指标（由 Collector 调用）

        Args:
            bundle_id: 应用 Bundle ID（用于查找目标进程）
            target_pid: 目标进程 PID（如果已知，优先使用）

        Returns:
            {'cpu_app': float, 'cpu_system': float, 'used_mb': float, 'total_mb': float}
        """
        # 查找目标进程 PID（如果未提供）
        if target_pid is None:
            proc_info = self.get_process_info(bundle_id)
            if proc_info:
                target_pid = proc_info.get("pid")

        # 设置目标 PID（用于后续数据过滤）
        if target_pid is not None:
            with self._cache_lock:
                self._target_pid = target_pid
                if self._target_bundle_id != bundle_id:
                    self._target_bundle_id = bundle_id
                    # 切换目标进程时清空累加器
                    self._accumulator.clear()
                    logger.debug(
                        f"[Throttle] 切换目标进程: bundle_id={bundle_id}, pid={target_pid}"
                    )

        # 计算聚合频率（确保不小于 1 秒）
        frequency_seconds = max(1, int(self._target_frequency))

        # 从累加器获取聚合数据
        aggregated = self._accumulator.get_aggregated_data(frequency_seconds)

        # iOS 不区分系统 CPU
        return {
            "cpu_app": aggregated["cpu_app"],
            "cpu_system": 0.0,
            "used_mb": aggregated["used_mb"],
            "total_mb": 4 * 1024,  # 固定 4GB 总内存
        }

    def get_process_info(self, bundle_id: str) -> Optional[Dict]:
        """根据 Bundle ID 查找进程信息

        Args:
            bundle_id: 应用 Bundle ID

        Returns:
            进程信息字典，如果未找到则返回 None
        """
        with self._cache_lock:
            # 提取应用名
            parts = bundle_id.split(".")
            if len(parts) > 1:
                common_tlds = {"com", "net", "org", "io", "co", "app"}
                if parts[-1].lower() in common_tlds and len(parts) >= 2:
                    app_name = parts[-2]
                else:
                    app_name = parts[-1]
            else:
                app_name = bundle_id

            # 在缓存中查找
            for proc in self._process_cache.values():
                exec_name = proc.get("execName", "")
                comm = proc.get("comm", "")
                name = proc.get("name", "")

                if app_name in exec_name or app_name in comm or app_name in name:
                    return proc

            return None

    def is_receiving_data(self) -> bool:
        """检查是否正在接收数据

        Returns:
            bool: 最近 5 秒内是否有数据接收
        """
        return time.time() - self._last_data_time < 5.0

    def set_target_frequency(self, frequency: float):
        """更新目标采集频率

        Args:
            frequency: 新的采集频率（秒）
        """
        self._target_frequency = frequency
        logger.debug(f"频率控制层: 更新目标频率为 {frequency} 秒")

    def clear(self):
        """清空所有数据"""
        self._accumulator.clear()
        with self._cache_lock:
            self._process_cache.clear()
        logger.debug("频率控制层: 数据已清空")
