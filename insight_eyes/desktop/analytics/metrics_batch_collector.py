# -*- coding: utf-8 -*-
"""
批量采集器 - 时间窗口快照采集

Copyright (c) 2025 Aceyuan361
"""
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from logzero import logger


@dataclass
class MetricsSnapshot:
    """性能快照 - 某一时刻所有性能指标的集合"""
    snapshot_timestamp: datetime
    collection_start_ts: float
    collection_end_ts: float
    collection_duration_ms: float
    cpu: Dict[str, Any]
    memory: Dict[str, Any]
    fps: Dict[str, Any]
    network: Dict[str, Any]
    battery: Dict[str, Any]
    collection_success: bool = True
    collection_errors: Dict[str, str] = field(default_factory=dict)
    incomplete_metrics: List[str] = field(default_factory=list)

    def is_complete(self) -> bool:
        return (self.collection_success and
                len(self.incomplete_metrics) == 0 and
                len(self.collection_errors) == 0)

    def get_summary(self) -> str:
        status = "✓" if self.is_complete() else "✗"
        cpu_val = self.cpu.get('appCpuRate', 0) if self.cpu else 0
        mem_val = self.memory.get('totalPass', 0) if self.memory else 0
        fps_val = self.fps.get('fps', 0) if self.fps else 0
        return (f"[{status}] {self.snapshot_timestamp.strftime('%H:%M:%S')} | "
                f"CPU: {cpu_val}%, Memory: {mem_val}MB, FPS: {fps_val}")

    def to_raw_metrics_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.snapshot_timestamp,
            'cpu': self.cpu or {},
            'memory': self.memory or {},
            'fps': self.fps or {},
            'network': self.network or {},
            'battery': self.battery or {}
        }


class MetricsBatchCollector:
    """批量采集器 - 时间窗口快照采集

    性能优化：
    1. FPS 采集降频策略（参考 Matrix）：每 5 次批量采集才采集一次 FPS
    2. FPS 数据缓存：两次采集之间使用缓存数据
    3. 并行采集优化：使用 ThreadPoolExecutor 并行执行
    """

    DEFAULT_TIMEOUT = 8.0  # iOS sysmon 需要约 4-5 秒，设置更长的超时时间
    # FPS 采集降频：每 N 次批量采集才采集一次 FPS（参考 Matrix 的延迟策略）
    FPS_COLLECTION_INTERVAL = 5

    def __init__(self, apm, timeout_seconds: float = DEFAULT_TIMEOUT):
        self.apm = apm
        self.timeout_seconds = timeout_seconds
        self._collection_count = 0
        # FPS 缓存（用于降频策略）
        self._last_fps_data = None
        self._fps_collection_count = 0
        logger.debug(f"批量采集器初始化: 超时={timeout_seconds}秒, FPS降频={self.FPS_COLLECTION_INTERVAL}")

    def collect_batch(self, device_id: str, package_name: str) -> MetricsSnapshot:
        """
        批量采集所有性能指标

        性能优化：FPS 采集降频策略
        - 每 N 次批量采集才采集一次 FPS（默认5次）
        - 两次 FPS 采集之间使用缓存数据
        - 这大大减少了 dumpsys gfxinfo 的调用次数
        """
        self._collection_count += 1
        collection_id = self._collection_count

        snapshot_timestamp = datetime.now()
        collection_start_ts = time.time()

        logger.debug(f"[批量采集 #{collection_id}] 开始: {snapshot_timestamp.strftime('%H:%M:%S.%f')[:-3]}")

        # ============ FPS 降频策略 ============
        should_collect_fps = (self._collection_count % self.FPS_COLLECTION_INTERVAL == 0)
        if not should_collect_fps and self._last_fps_data:
            logger.debug(f"[批量采集 #{collection_id}] 使用FPS缓存（下次采集: {self.FPS_COLLECTION_INTERVAL - (self._collection_count % self.FPS_COLLECTION_INTERVAL)}次后）")
        else:
            self._fps_collection_count += 1
            logger.debug(f"[批量采集 #{collection_id}] 采集FPS（第{self._fps_collection_count}次）")

        def _collect_fps():
            """FPS采集包装函数（支持降频）"""
            nonlocal should_collect_fps  # 声明使用外层作用域的变量
            logger.info(f"[_collect_fps] 开始采集: should_collect_fps={should_collect_fps}, cached_fps={self._last_fps_data.get('fps', 0) if self._last_fps_data else 'None'}")

            # 关键修复：如果缓存为 0，强制重新采集
            if not should_collect_fps:
                # 检查缓存是否有效
                if not self._last_fps_data or self._last_fps_data.get('fps', 0) == 0:
                    logger.info("[_collect_fps] 缓存为 0 或无缓存，强制重新采集")
                    should_collect_fps = True

            if should_collect_fps:
                # 实际采集FPS
                logger.info(f"[_collect_fps] 调用 self.apm.collectFps()...")
                fps_data = self.apm.collectFps()
                logger.info(f"[_collect_fps] collectFps() 返回: fps={fps_data.get('fps', 0) if fps_data else 'None'}")
                self._last_fps_data = fps_data  # 更新缓存
                return fps_data
            else:
                # 使用缓存数据
                cached_fps = self._last_fps_data.get('fps', 0) if self._last_fps_data else 0
                logger.info(f"[_collect_fps] 使用缓存: fps={cached_fps}")
                return self._last_fps_data if self._last_fps_data else {
                    'fps': 0, 'jank': 0, 'bigJank': 0,
                    'ftime_avg': 0, 'ftime_max': 0, 'ftime_min': 0
                }

        tasks = {
            'cpu': lambda: self.apm.collectCpu(),
            'memory': lambda: self.apm.collectMemory(),
            'fps': _collect_fps,  # 使用降频包装函数
            'network': lambda: self.apm.collectFlow(),
            'battery': lambda: self.apm.collectBattery()
        }

        results = {}
        errors = {}
        incomplete = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_metric = {
                executor.submit(task_func): metric_name
                for metric_name, task_func in tasks.items()
            }

            for future in as_completed(future_to_metric, timeout=self.timeout_seconds):
                metric_name = future_to_metric[future]
                try:
                    result = future.result(timeout=self.timeout_seconds)
                    results[metric_name] = result
                    # 电池采集特别日志
                    if metric_name == 'battery' and result:
                        level = result.get('level', 0) if isinstance(result, dict) else 0
                        temp = result.get('temperature', 0) if isinstance(result, dict) else 0
                        logger.debug(f"[批量采集 #{collection_id}] ✓ battery: level={level}%, temp={temp}°C")
                    else:
                        logger.debug(f"[批量采集 #{collection_id}] ✓ {metric_name}")
                except TimeoutError:
                    errors[metric_name] = f"超时"
                    incomplete.append(metric_name)
                    logger.warning(f"[批量采集 #{collection_id}] ✗ {metric_name} 超时")
                except Exception as e:
                    errors[metric_name] = str(e)
                    incomplete.append(metric_name)
                    logger.warning(f"[批量采集 #{collection_id}] ✗ {metric_name} 失败: {e}")

        collection_end_ts = time.time()
        collection_duration_ms = (collection_end_ts - collection_start_ts) * 1000

        snapshot = MetricsSnapshot(
            snapshot_timestamp=snapshot_timestamp,
            collection_start_ts=collection_start_ts,
            collection_end_ts=collection_end_ts,
            collection_duration_ms=collection_duration_ms,
            cpu=results.get('cpu', {}),
            memory=results.get('memory', {}),
            fps=results.get('fps', {}),
            network=results.get('network', {}),
            battery=results.get('battery', {}),
            collection_success=len(incomplete) == 0,
            collection_errors=errors,
            incomplete_metrics=incomplete
        )

        if snapshot.is_complete():
            # 提取指标值用于日志
            cpu_val = snapshot.cpu.get('appCpuRate', 0) if snapshot.cpu else 0
            mem_val = snapshot.memory.get('totalPass', 0) if snapshot.memory else 0
            fps_val = snapshot.fps.get('fps', 0) if snapshot.fps else 0
            battery_level = snapshot.battery.get('level', 0) if snapshot.battery else 0
            battery_temp = snapshot.battery.get('temperature', 0) if snapshot.battery else 0
            logger.info(f"[批量采集 #{collection_id}] ✓ 完成: CPU={cpu_val}%, Memory={mem_val}MB, FPS={fps_val}, Battery={battery_level}%, Temp={battery_temp}°C, 耗时={collection_duration_ms:.0f}ms")
        else:
            logger.warning(f"[批量采集 #{collection_id}] ⚠ 部分失败: {incomplete}, 耗时 {collection_duration_ms:.0f}ms")

        return snapshot
