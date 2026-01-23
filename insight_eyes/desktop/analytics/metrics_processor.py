"""
性能指标处理器

负责接收、清洗、计算派生指标，并提供滑动窗口统计功能
"""

from collections import deque
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from logzero import logger

from PyQt6.QtCore import QObject, pyqtSignal

from .models import (
    ProcessedMetrics, FPSMetrics, MemoryMetrics,
    CPUMetrics, NetworkMetrics, BatteryMetrics, TrendType
)
from .thresholds import ThresholdManager
from .data_validator import DataValidator


class MetricsProcessor(QObject):
    """性能指标处理器

    主要功能：
    1. 接收并清洗原始指标数据
    2. 计算派生指标（增长率、移动平均等）
    3. 维护滑动窗口用于趋势分析
    4. 检测数据趋势（上升/下降/波动）
    """

    # 信号：处理后的指标就绪
    metrics_ready = pyqtSignal(object)  # ProcessedMetrics

    # 信号：检测到数据异常
    data_error = pyqtSignal(str)  # 错误消息

    def __init__(self, session_id: int, device_id: str, app_id: str,
                 window_size: int = 60, threshold_manager: Optional[ThresholdManager] = None,
                 enable_validation: bool = True):
        """初始化指标处理器

        Args:
            session_id: 监控会话ID
            device_id: 设备ID
            app_id: 应用ID
            window_size: 滑动窗口大小（秒）
            threshold_manager: 阈值管理器
            enable_validation: 是否启用数据验证，默认启用
        """
        super().__init__()

        self._session_id = session_id
        self._device_id = device_id
        self._app_id = app_id
        self._window_size = window_size
        self._thresholds = threshold_manager or ThresholdManager()

        # 数据验证器
        self._validator = DataValidator(strict_mode=False) if enable_validation else None

        # 滑动窗口存储历史数据
        self._fps_buffer = deque(maxlen=window_size)
        self._memory_buffer = deque(maxlen=window_size)
        self._cpu_buffer = deque(maxlen=window_size)
        self._network_buffer = deque(maxlen=window_size)
        self._battery_buffer = deque(maxlen=window_size)  # 电池数据缓冲区

        # 用于内存泄露检测的长时间窗口
        self._memory_long_buffer = deque(maxlen=300)  # 5分钟窗口（假设1秒采样）

    def process_raw_data(self, raw_data: Dict[str, Any]) -> Optional[ProcessedMetrics]:
        """处理原始指标数据

        Args:
            raw_data: 原始数据字典，包含fps, memory, cpu, network等字段

        Returns:
            处理后的指标对象，如果数据无效则返回None
        """
        try:
            timestamp = datetime.now()

            # 数据验证（如果启用）
            if self._validator is not None:
                validation_result = self._validator.validate_raw_data(raw_data)

                # 如果有严重错误，发出信号并返回 None
                if validation_result.has_errors:
                    error_messages = validation_result.get_all_messages()
                    error_summary = f"数据验证失败: {'; '.join(error_messages[:3])}"
                    self.data_error.emit(error_summary)
                    # 根据错误数量决定是否继续处理（放宽阈值从3到10）
                    if validation_result.error_count > 10:
                        return None

                # 警告信息通过日志输出（不影响数据处理）
                if validation_result.has_warnings:
                    # 可以选择记录警告或发出警告信号
                    pass

            # 处理各项指标
            fps_metrics = self._process_fps(raw_data.get('fps', {}), timestamp)
            memory_metrics = self._process_memory(raw_data.get('memory', {}), timestamp)
            cpu_metrics = self._process_cpu(raw_data.get('cpu', {}), timestamp)
            network_metrics = self._process_network(raw_data.get('network', {}), timestamp)
            battery_metrics = self._process_battery(raw_data.get('battery', {}), timestamp)

            # 创建处理后的指标对象
            processed = ProcessedMetrics(
                session_id=self._session_id,
                timestamp=timestamp,
                device_id=self._device_id,
                app_id=self._app_id,
                fps=fps_metrics,
                memory=memory_metrics,
                cpu=cpu_metrics,
                network=network_metrics,
                battery=battery_metrics
            )

            # 更新滑动窗口
            self._update_buffers(processed)

            # 发出信号
            self.metrics_ready.emit(processed)

            return processed

        except Exception as e:
            self.data_error.emit(f"数据处理错误: {str(e)}")
            return None

    def _process_fps(self, raw_fps: Dict[str, Any], timestamp: datetime) -> Optional[FPSMetrics]:
        """处理FPS数据"""
        if not raw_fps:
            return None

        try:
            fps = raw_fps.get('fps', 0.0)
            jank = raw_fps.get('jank', 0)
            big_jank = raw_fps.get('bigJank', 0)
            frame_time_avg = raw_fps.get('ftime_avg', 0.0)
            frame_time_max = raw_fps.get('ftime_max', 0.0)

            # 数据清洗：处理异常值
            if fps < 0 or fps > 240:  # 合理的FPS范围
                fps = 0.0

            if frame_time_avg < 0:
                frame_time_avg = 0.0

            # 计算趋势
            trend = self._calculate_trend(list(self._fps_buffer), 'fps', fps)

            return FPSMetrics(
                fps=fps,
                jank_count=jank,
                big_jank_count=big_jank,
                frame_time_avg=frame_time_avg,
                frame_time_max=frame_time_max,
                trend=trend,
                timestamp=timestamp
            )

        except (KeyError, TypeError, ValueError):
            return None

    def _process_memory(self, raw_memory: Dict[str, Any], timestamp: datetime) -> Optional[MemoryMetrics]:
        """处理内存数据

        注意：MemoryCollector 已经将 KB 转换为 MB，这里直接使用

        Args:
            raw_memory: 原始内存数据，可能的键:
                - totalPass/total: 总内存 (MB) - MemoryCollector 已转换
                - nativePass/native: Native 堆内存 (MB)
                - dalvikPass/dalvik: Dalvik 堆内存 (MB)
            timestamp: 时间戳

        Returns:
            MemoryMetrics: 处理后的内存指标
        """
        if not raw_memory:
            return None

        try:
            # 获取内存值（MemoryCollector 已经转换为 MB）
            # 兼容多种键名：支持 iOS ('used_mb') 和 Android ('totalPass', 'total')
            total = (raw_memory.get('used_mb') or
                     raw_memory.get('totalPass', 0.0) or
                     raw_memory.get('total', 0.0))
            native = raw_memory.get('nativePass', 0.0) or raw_memory.get('native', 0.0)
            dalvik = raw_memory.get('dalvikPass', 0.0) or raw_memory.get('dalvik', 0.0)

            # 确保是数值类型
            total_mb = float(total) if total else 0.0
            native_mb = float(native) if native else 0.0
            dalvik_mb = float(dalvik) if dalvik else 0.0

            # 边界检查：确保值在合理范围内
            # 移动应用内存通常在 0 - 2048 MB 之间
            MAX_REASONABLE_MEMORY_MB = 2048.0  # 2 GB

            if total_mb > MAX_REASONABLE_MEMORY_MB:
                # 如果值异常大，可能是数据单位错误
                # 记录警告并限制最大值
                logger.warning(f"内存值异常: {total_mb} MB，限制为最大值")
                total_mb = min(total_mb, MAX_REASONABLE_MEMORY_MB)

            # 计算内存增长率
            growth_rate = self._calculate_memory_growth_rate()

            # 计算趋势
            trend = self._calculate_trend(list(self._memory_buffer), 'total_mb', total_mb)

            return MemoryMetrics(
                total_mb=total_mb,
                native_mb=native_mb,
                dalvik_mb=dalvik_mb,
                growth_rate_mb_per_min=growth_rate,
                trend=trend,
                timestamp=timestamp
            )

        except (KeyError, TypeError, ValueError):
            return None

    def _process_cpu(self, raw_cpu: Dict[str, Any], timestamp: datetime) -> Optional[CPUMetrics]:
        """处理CPU数据"""
        if not raw_cpu:
            return None

        try:
            # 支持 iOS ('cpu_app') 和 Android ('appCpuRate') 字段名
            app_cpu = raw_cpu.get('cpu_app') or raw_cpu.get('appCpuRate', 0.0)
            sys_cpu = raw_cpu.get('cpu_system') or raw_cpu.get('sysCpuRate', 0.0)

            # 数据清洗：确保在合理范围内
            app_cpu = max(0.0, min(100.0, app_cpu))
            sys_cpu = max(0.0, min(100.0, sys_cpu))

            # 计算移动平均
            moving_avg = self._calculate_moving_avg(list(self._cpu_buffer), 'app_cpu_percent', app_cpu)

            return CPUMetrics(
                app_cpu_percent=app_cpu,
                sys_cpu_percent=sys_cpu,
                moving_avg=moving_avg,
                thread_count=raw_cpu.get('threadCount', 0),
                timestamp=timestamp
            )

        except (KeyError, TypeError, ValueError):
            return None

    def _process_network(self, raw_network: Dict[str, Any], timestamp: datetime) -> Optional[NetworkMetrics]:
        """处理网络数据"""
        if not raw_network:
            return None

        try:
            up_speed = raw_network.get('upFlow', 0.0)
            down_speed = raw_network.get('downFlow', 0.0)

            # 计算累计流量（从历史数据累加）
            total_sent, total_received = self._calculate_total_traffic(up_speed, down_speed)

            return NetworkMetrics(
                upload_speed_kb_s=up_speed,
                download_speed_kb_s=down_speed,
                total_sent_mb=total_sent,
                total_received_mb=total_received,
                timestamp=timestamp
            )

        except (KeyError, TypeError, ValueError):
            return None

    def _process_battery(self, raw_battery: Dict[str, Any], timestamp: datetime) -> Optional[BatteryMetrics]:
        """处理电池数据"""
        if not raw_battery:
            return None

        try:
            level = raw_battery.get('level', 0)
            temperature = raw_battery.get('temperature', 0.0)
            current = raw_battery.get('current', 0.0)
            voltage = raw_battery.get('voltage', 0.0)
            power = raw_battery.get('power', 0.0)
            status = raw_battery.get('status', 'unknown')
            capacity = raw_battery.get('capacity')  # 可选字段

            # 数据清洗：确保数据在合理范围内
            if not isinstance(level, (int, float)) or level < 0 or level > 100:
                level = 0
            if not isinstance(temperature, (int, float)):
                temperature = 0.0
            if not isinstance(current, (int, float)):
                current = 0.0
            if not isinstance(voltage, (int, float)):
                voltage = 0.0
            if not isinstance(power, (int, float)):
                power = 0.0
            if not isinstance(status, str):
                status = 'unknown'

            return BatteryMetrics(
                level=int(level),
                temperature=float(temperature),
                current=float(current),
                voltage=float(voltage),
                power=float(power),
                status=status,
                capacity=int(capacity) if capacity and isinstance(capacity, (int, float)) else None,
                timestamp=timestamp
            )

        except (KeyError, TypeError, ValueError):
            return None

    def _update_buffers(self, metrics: ProcessedMetrics):
        """更新滑动窗口缓冲区"""
        if metrics.fps:
            self._fps_buffer.append({
                'fps': metrics.fps.fps,
                'timestamp': metrics.fps.timestamp
            })

        if metrics.memory:
            self._memory_buffer.append({
                'total_mb': metrics.memory.total_mb,
                'timestamp': metrics.memory.timestamp
            })
            self._memory_long_buffer.append({
                'total_mb': metrics.memory.total_mb,
                'timestamp': metrics.memory.timestamp
            })

        if metrics.cpu:
            self._cpu_buffer.append({
                'app_cpu_percent': metrics.cpu.app_cpu_percent,
                'sys_cpu_percent': metrics.cpu.sys_cpu_percent,
                'timestamp': metrics.cpu.timestamp
            })

        if metrics.network:
            self._network_buffer.append({
                'upload_speed_kb_s': metrics.network.upload_speed_kb_s,
                'download_speed_kb_s': metrics.network.download_speed_kb_s,
                'timestamp': metrics.network.timestamp
            })

        if metrics.battery:
            self._battery_buffer.append({
                'level': metrics.battery.level,
                'temperature': metrics.battery.temperature,
                'timestamp': metrics.battery.timestamp
            })

    def _calculate_trend(self, buffer: List[Dict], field: str, current_value: float) -> TrendType:
        """计算数据趋势

        Args:
            buffer: 历史数据缓冲区
            field: 要分析的字段名
            current_value: 当前值

        Returns:
            趋势类型
        """
        if len(buffer) < 3:
            return TrendType.STABLE

        try:
            # 提取最近的值
            values = [item.get(field, 0) for item in list(buffer)[-10:]]

            if len(values) < 3:
                return TrendType.STABLE

            # 计算线性回归斜率
            x = np.arange(len(values))
            y = np.array(values)

            # 避免除零错误
            if np.std(y) < 0.01:
                return TrendType.STABLE

            slope = np.polyfit(x, y, 1)[0]

            # 计算变化率
            avg_value = np.mean(y)
            if avg_value == 0:
                return TrendType.STABLE

            change_rate = slope / avg_value

            # 判断趋势
            if change_rate > 0.05:  # 上升超过5%
                return TrendType.INCREASING
            elif change_rate < -0.05:  # 下降超过5%
                return TrendType.DECREASING
            else:
                # 检查是否波动
                if np.std(y) / avg_value > 0.2:  # 变异系数>20%
                    return TrendType.FLUCTUATING
                else:
                    return TrendType.STABLE

        except (ValueError, ZeroDivisionError):
            return TrendType.STABLE

    def _calculate_memory_growth_rate(self) -> float:
        """
        计算内存增长率（MB/min）- 修复版（P2-21）

        修复内容：
        - 使用固定时间窗口（30秒）而非 buffer 首尾
        - 避免 buffer 滑动时首元素移除导致的计算跳变
        - 使用线性回归计算趋势，更准确反映真实增长速率

        Returns:
            内存增长率，如果无法计算则返回0.0
        """
        if len(self._memory_buffer) < 2:
            return 0.0

        try:
            from datetime import timedelta

            # 使用固定时间窗口（30秒）避免 buffer 滑动导致的跳变
            time_window = timedelta(seconds=30)
            now = self._memory_buffer[-1]['timestamp']

            # 获取时间窗口内的数据点
            window_data = [
                item for item in self._memory_buffer
                if now - item['timestamp'] <= time_window
            ]

            if len(window_data) < 2:
                return 0.0

            # 使用线性回归计算增长率（更稳定）
            # x: 时间（秒）, y: 内存（MB）
            import numpy as np
            times = [(now - item['timestamp']).total_seconds() for item in window_data]
            mems = [item.get('total_mb', 0.0) for item in window_data]

            # 转换为 numpy 数组
            x = np.array(times)
            y = np.array(mems)

            # 线性回归: y = mx + b
            # 斜率 m = (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²)
            n = len(x)
            if n < 2:
                return 0.0

            sum_x = np.sum(x)
            sum_y = np.sum(y)
            sum_xy = np.sum(x * y)
            sum_x2 = np.sum(x ** 2)

            denominator = n * sum_x2 - sum_x ** 2
            if denominator == 0:
                return 0.0

            # 斜率（MB/秒），需要转换为 MB/分钟
            slope = (n * sum_xy - sum_x * sum_y) / denominator

            # 转换为 MB/min（乘以 60），并取负值（因为时间是倒序的）
            growth_rate_per_min = -slope * 60

            return round(growth_rate_per_min, 2)

        except (KeyError, ValueError, ImportError):
            return 0.0

    def _calculate_moving_avg(self, buffer: List[Dict], field: str,
                             current_value: float, window: int = 10) -> float:
        """计算移动平均值

        Args:
            buffer: 历史数据缓冲区
            field: 要计算的字段名
            current_value: 当前值
            window: 窗口大小

        Returns:
            移动平均值
        """
        try:
            # 获取最近的值
            recent_values = [item.get(field, 0.0) for item in list(buffer)[-window+1:]]
            recent_values.append(current_value)

            if not recent_values:
                return current_value

            return round(float(np.mean(recent_values)), 2)

        except (ValueError, TypeError):
            return current_value

    def _calculate_total_traffic(self, up_speed: float, down_speed: float) -> Tuple[float, float]:
        """计算累计流量

        使用实际采样间隔计算流量增量，而不是硬编码 1 秒

        Args:
            up_speed: 上行速度(KB/s)
            down_speed: 下行速度(KB/s)

        Returns:
            (总发送量MB, 总接收量MB)
        """
        if not self._network_buffer:
            # 初始值，假设 1 秒采样间隔
            return (up_speed / 1024.0, down_speed / 1024.0)

        try:
            # 从上一个采样点累加
            last = self._network_buffer[-1]

            # 获取上次累计值（如果没有，假设为 0）
            last_total_sent = last.get('total_sent_mb', 0.0)
            last_total_received = last.get('total_received_mb', 0.0)

            # 获取上次时间戳
            last_timestamp = last.get('timestamp')
            if last_timestamp is None:
                # 如果没有时间戳，使用默认 1 秒间隔
                time_diff = 1.0
            else:
                # 计算实际时间差（秒）
                current_timestamp = datetime.now()
                time_diff = (current_timestamp - last_timestamp).total_seconds()

                # 防止时间差过小（例如重复采样）或过大
                time_diff = max(0.1, min(time_diff, 60.0))

            # 使用实际时间差计算增量
            sent_increment = up_speed * time_diff / 1024.0  # KB/s * s / 1024 = MB
            received_increment = down_speed * time_diff / 1024.0

            total_sent = last_total_sent + sent_increment
            total_received = last_total_received + received_increment

            return (round(total_sent, 2), round(total_received, 2))

        except (KeyError, ValueError):
            return (up_speed / 1024.0, down_speed / 1024.0)

    def get_recent_fps(self, count: int = 10) -> List[float]:
        """获取最近的FPS数据"""
        return [item['fps'] for item in list(self._fps_buffer)[-count:]]

    def get_recent_memory(self, count: int = 10) -> List[float]:
        """获取最近的内存数据"""
        return [item['total_mb'] for item in list(self._memory_buffer)[-count:]]

    def get_recent_cpu(self, count: int = 10) -> List[float]:
        """获取最近的CPU数据"""
        return [item['app_cpu_percent'] for item in list(self._cpu_buffer)[-count:]]

    def get_memory_long_term(self) -> List[float]:
        """获取长期内存数据（用于泄露检测）"""
        return [item['total_mb'] for item in list(self._memory_long_buffer)]

    def clear_buffers(self):
        """清空所有缓冲区"""
        self._fps_buffer.clear()
        self._memory_buffer.clear()
        self._cpu_buffer.clear()
        self._network_buffer.clear()
        self._memory_long_buffer.clear()
