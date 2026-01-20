"""
性能异常检测器

负责检测各类性能异常，包括FPS卡顿、内存泄露、CPU高负载等
支持自定义阈值和多种检测算法
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import deque
import numpy as np

from PyQt6.QtCore import QObject, pyqtSignal

from .models import (
    ProcessedMetrics, Alert, AlertType, AlertSeverity
)
from .thresholds import ThresholdManager


class AnomalyDetector(QObject):
    """性能异常检测器

    主要功能：
    1. FPS卡顿检测（低帧率、连续卡顿、大卡顿）
    2. 内存泄露检测（持续增长、增长率异常）
    3. CPU异常检测（高负载、持续高占用）
    4. 网络异常检测（上传异常、超时）

    无延迟检测：与采集频率同步，实时处理每个数据点
    """

    # 信号：检测到异常
    alert_triggered = pyqtSignal(object)  # Alert

    # 信号：检测状态更新
    detection_status = pyqtSignal(str)  # 状态消息

    def __init__(self, session_id: int, threshold_manager: ThresholdManager,
                 enable_suppression: bool = True, default_cooldown_seconds: int = 30):
        """初始化异常检测器

        Args:
            session_id: 监控会话ID
            threshold_manager: 阈值管理器
            enable_suppression: 是否启用告警抑制，默认启用
            default_cooldown_seconds: 默认冷却期（秒），默认30秒
        """
        super().__init__()

        self._session_id = session_id
        self._thresholds = threshold_manager
        self._enable_suppression = enable_suppression
        self._default_cooldown = default_cooldown_seconds

        # 告警冷却期记录 - 字典: {alert_key: last_trigger_time}
        # alert_key 格式: f"{alert_type.value}_{metric_name}"
        self._alert_cooldown: Dict[str, datetime] = {}

        # 历史状态用于趋势分析
        self._low_fps_count = 0  # 低帧率计数
        self._high_cpu_count = 0  # 高CPU计数
        self._zero_upload_count = 0  # 零上行计数
        self._last_network_time = None  # 上次网络活动时间

        # 用于检测持续增长的内存值
        self._memory_history = deque(maxlen=10)

    def _should_suppress_alert(self, alert: Alert) -> bool:
        """
        检查告警是否应该被抑制（在冷却期内）- 修复版（P2-22）

        修复内容：
        - 只有在告警通过抑制检查时才更新冷却时间
        - 避免冷却期刚过时立即更新时间导致后续告警被错误抑制

        Args:
            alert: 告警对象

        Returns:
            bool: True 表示应该抑制，False 表示可以触发
        """
        if not self._enable_suppression:
            return False

        # 获取冷却期时间（秒）
        cooldown_seconds = self._get_alert_cooldown(alert)

        # 生成告警唯一键
        alert_key = self._generate_alert_key(alert)

        # 检查是否在冷却期内
        last_trigger_time = self._alert_cooldown.get(alert_key)
        if last_trigger_time is None:
            # 首次触发，记录时间并返回 False（不抑制）
            self._alert_cooldown[alert_key] = datetime.now()
            return False

        # 计算距离上次触发的时间
        time_since_last = (datetime.now() - last_trigger_time).total_seconds()

        if time_since_last < cooldown_seconds:
            # 仍在冷却期内，抑制此告警
            return True
        else:
            # 冷却期已过，允许触发并更新时间
            # 修复：只有在真正触发告警时才更新时间
            self._alert_cooldown[alert_key] = datetime.now()
            return False

    def _generate_alert_key(self, alert: Alert) -> str:
        """
        生成告警的唯一键

        Args:
            alert: 告警对象

        Returns:
            str: 告警键
        """
        return f"{alert.alert_type.value}_{alert.metric_name}"

    def _get_alert_cooldown(self, alert: Alert) -> int:
        """
        获取告警的冷却期时间（秒）

        不同类型和严重程度的告警可能有不同的冷却期

        Args:
            alert: 告警对象

        Returns:
            int: 冷却期秒数
        """
        # 严重告警的冷却期较短（需要尽快响应）
        if alert.severity == AlertSeverity.CRITICAL:
            return min(self._default_cooldown, 15)  # 最多15秒

        # 警告级别告警使用默认冷却期
        if alert.severity == AlertSeverity.WARNING:
            return self._default_cooldown  # 默认30秒

        # 其他情况使用默认冷却期
        return self._default_cooldown

    def clear_cooldown_history(self) -> None:
        """清空告警冷却期历史（用于测试或重置）"""
        self._alert_cooldown.clear()

    def get_cooldown_stats(self) -> Dict[str, Any]:
        """
        获取告警冷却期统计信息

        Returns:
            统计信息字典
        """
        now = datetime.now()
        active_cooldowns = []

        for alert_key, last_time in self._alert_cooldown.items():
            time_since = (now - last_time).total_seconds()
            cooldown_remaining = max(0, self._default_cooldown - time_since)
            active_cooldowns.append({
                'alert_key': alert_key,
                'last_trigger': last_time.isoformat(),
                'seconds_ago': time_since,
                'cooldown_remaining': cooldown_remaining
            })

        return {
            'total_alerts_tracked': len(self._alert_cooldown),
            'active_cooldowns': active_cooldowns,
            'default_cooldown_seconds': self._default_cooldown
        }

    def detect_all(self, metrics: ProcessedMetrics) -> List[Alert]:
        """执行所有异常检测

        Args:
            metrics: 处理后的指标数据

        Returns:
            检测到的告警列表（已应用告警抑制）
        """
        all_detected_alerts = []

        # FPS检测
        if metrics.fps:
            fps_alerts = self.detect_fps_anomaly(metrics)
            all_detected_alerts.extend(fps_alerts)

        # 内存检测
        if metrics.memory:
            memory_alerts = self.detect_memory_anomaly(metrics)
            all_detected_alerts.extend(memory_alerts)

        # CPU检测
        if metrics.cpu:
            cpu_alerts = self.detect_cpu_anomaly(metrics)
            all_detected_alerts.extend(cpu_alerts)

        # 网络检测
        if metrics.network:
            network_alerts = self.detect_network_anomaly(metrics)
            all_detected_alerts.extend(network_alerts)

        # 应用告警抑制
        filtered_alerts = []
        suppressed_count = 0

        for alert in all_detected_alerts:
            if self._should_suppress_alert(alert):
                suppressed_count += 1
            else:
                filtered_alerts.append(alert)

        # 发送未抑制的告警信号
        for alert in filtered_alerts:
            self.alert_triggered.emit(alert)

        # 如果有告警被抑制，记录日志（可选）
        if suppressed_count > 0:
            self.detection_status.emit(f"已抑制 {suppressed_count} 个重复告警")

        return filtered_alerts

    def detect_fps_anomaly(self, metrics: ProcessedMetrics) -> List[Alert]:
        """检测FPS异常

        检测项目：
        1. 实时FPS < 阈值（警告/严重）
        2. 帧时间 > 阈值（大卡顿）
        3. 卡顿次数统计

        Args:
            metrics: 处理后的指标数据

        Returns:
            检测到的FPS告警列表
        """
        if not metrics.fps:
            return []

        alerts = []
        fps = metrics.fps
        thresholds = self._thresholds.fps

        # 1. 严重低帧率检测
        if fps.fps < thresholds.critical_fps:
            self._low_fps_count += 1
            alert = Alert(
                alert_type=AlertType.LOW_FPS,
                severity=AlertSeverity.CRITICAL,
                metric_name="FPS",
                current_value=fps.fps,
                threshold=thresholds.critical_fps,
                message=f"严重低帧率: 当前FPS {fps.fps:.1f} < 阈值 {thresholds.critical_fps}",
                timestamp=metrics.timestamp,
                session_id=self._session_id,
                device_id=metrics.device_id,
                app_id=metrics.app_id,
                context={
                    'jank_count': fps.jank_count,
                    'big_jank_count': fps.big_jank_count,
                    'frame_time_avg': fps.frame_time_avg
                }
            )
            alerts.append(alert)

        # 2. 警告级低帧率检测
        elif fps.fps < thresholds.warning_fps:
            self._low_fps_count += 1
            alert = Alert(
                alert_type=AlertType.LOW_FPS,
                severity=AlertSeverity.WARNING,
                metric_name="FPS",
                current_value=fps.fps,
                threshold=thresholds.warning_fps,
                message=f"低帧率警告: 当前FPS {fps.fps:.1f} < 阈值 {thresholds.warning_fps}",
                timestamp=metrics.timestamp,
                session_id=self._session_id,
                device_id=metrics.device_id,
                app_id=metrics.app_id,
                context={
                    'jank_count': fps.jank_count,
                    'trend': fps.trend.value
                }
            )
            alerts.append(alert)
        else:
            # FPS正常，重置计数
            self._low_fps_count = 0

        # 3. 大卡顿检测（帧时间过长）
        if fps.frame_time_max > thresholds.big_jank_frame_time_ms:
            alert = Alert(
                alert_type=AlertType.FPS_BIG_JANK,
                severity=AlertSeverity.CRITICAL,
                metric_name="FrameTime",
                current_value=fps.frame_time_max,
                threshold=thresholds.big_jank_frame_time_ms,
                message=f"检测到大卡顿: 帧时间 {fps.frame_time_max:.1f}ms > 阈值 {thresholds.big_jank_frame_time_ms}ms",
                timestamp=metrics.timestamp,
                session_id=self._session_id,
                device_id=metrics.device_id,
                app_id=metrics.app_id,
                context={
                    'fps': fps.fps,
                    'frame_time_avg': fps.frame_time_avg
                }
            )
            alerts.append(alert)

        # 4. 卡顿次数告警
        if fps.jank_count > 0:
            severity = AlertSeverity.WARNING if fps.jank_count < 5 else AlertSeverity.CRITICAL
            alert = Alert(
                alert_type=AlertType.FPS_JANK,
                severity=severity,
                metric_name="JankCount",
                current_value=fps.jank_count,
                threshold=0,
                message=f"检测到 {fps.jank_count} 次卡顿",
                timestamp=metrics.timestamp,
                session_id=self._session_id,
                device_id=metrics.device_id,
                app_id=metrics.app_id,
                context={
                    'fps': fps.fps,
                    'big_jank_count': fps.big_jank_count
                }
            )
            alerts.append(alert)

        # 5. FPS波动检测
        if fps.trend.value == 'fluctuating' and fps.fps < thresholds.warning_fps:
            alert = Alert(
                alert_type=AlertType.FPS_FLUCTUATION,
                severity=AlertSeverity.WARNING,
                metric_name="FPS_Trend",
                current_value=fps.fps,
                threshold=thresholds.warning_fps,
                message=f"FPS波动异常: 当前FPS {fps.fps:.1f}, 趋势不稳定",
                timestamp=metrics.timestamp,
                session_id=self._session_id,
                device_id=metrics.device_id,
                app_id=metrics.app_id,
                context={'trend': fps.trend.value}
            )
            alerts.append(alert)

        return alerts

    def detect_memory_anomaly(self, metrics: ProcessedMetrics) -> List[Alert]:
        """检测内存异常

        检测项目：
        1. 内存持续增长（泄露风险）
        2. 内存增长率异常
        3. 高内存占用

        Args:
            metrics: 处理后的指标数据

        Returns:
            检测到的内存告警列表
        """
        if not metrics.memory:
            return []

        alerts = []
        memory = metrics.memory
        thresholds = self._thresholds.memory

        # 更新内存历史
        self._memory_history.append(memory.total_mb)

        # 1. 高内存占用检测
        if memory.total_mb > thresholds.high_memory_mb:
            alert = Alert(
                alert_type=AlertType.HIGH_MEMORY,
                severity=AlertSeverity.WARNING,
                metric_name="Memory",
                current_value=memory.total_mb,
                threshold=thresholds.high_memory_mb,
                message=f"高内存占用: 当前 {memory.total_mb:.1f}MB > 阈值 {thresholds.high_memory_mb}MB",
                timestamp=metrics.timestamp,
                session_id=self._session_id,
                device_id=metrics.device_id,
                app_id=metrics.app_id,
                context={
                    'native_mb': memory.native_mb,
                    'dalvik_mb': memory.dalvik_mb,
                    'growth_rate': memory.growth_rate_mb_per_min
                }
            )
            alerts.append(alert)

        # 2. 内存增长率异常检测
        if memory.growth_rate_mb_per_min > thresholds.growth_rate_critical_mb_per_min:
            alert = Alert(
                alert_type=AlertType.MEMORY_GROWTH,
                severity=AlertSeverity.CRITICAL,
                metric_name="MemoryGrowthRate",
                current_value=memory.growth_rate_mb_per_min,
                threshold=thresholds.growth_rate_critical_mb_per_min,
                message=f"内存增长率严重: {memory.growth_rate_mb_per_min:.1f}MB/min > 阈值 {thresholds.growth_rate_critical_mb_per_min}MB/min",
                timestamp=metrics.timestamp,
                session_id=self._session_id,
                device_id=metrics.device_id,
                app_id=metrics.app_id,
                context={'current_memory_mb': memory.total_mb}
            )
            alerts.append(alert)
        elif memory.growth_rate_mb_per_min > thresholds.growth_rate_warning_mb_per_min:
            alert = Alert(
                alert_type=AlertType.MEMORY_GROWTH,
                severity=AlertSeverity.WARNING,
                metric_name="MemoryGrowthRate",
                current_value=memory.growth_rate_mb_per_min,
                threshold=thresholds.growth_rate_warning_mb_per_min,
                message=f"内存增长率警告: {memory.growth_rate_mb_per_min:.1f}MB/min > 阈值 {thresholds.growth_rate_warning_mb_per_min}MB/min",
                timestamp=metrics.timestamp,
                session_id=self._session_id,
                device_id=metrics.device_id,
                app_id=metrics.app_id,
                context={'current_memory_mb': memory.total_mb}
            )
            alerts.append(alert)

        # 3. 内存持续增长检测（泄露风险）
        if len(self._memory_history) >= thresholds.monotonic_increase_samples:
            # 检查是否单调递增
            is_monotonic = all(
                self._memory_history[i] <= self._memory_history[i + 1]
                for i in range(len(self._memory_history) - 1)
            )

            if is_monotonic:
                # 计算增长量
                growth = self._memory_history[-1] - self._memory_history[0]

                if growth > thresholds.leak_growth_mb:
                    alert = Alert(
                        alert_type=AlertType.MEMORY_LEAK,
                        severity=AlertSeverity.CRITICAL,
                        metric_name="MemoryLeak",
                        current_value=growth,
                        threshold=thresholds.leak_growth_mb,
                        message=f"疑似内存泄露: {len(self._memory_history)}个采样点持续增长 {growth:.1f}MB",
                        timestamp=metrics.timestamp,
                        session_id=self._session_id,
                        device_id=metrics.device_id,
                        app_id=metrics.app_id,
                        context={
                            'start_memory_mb': self._memory_history[0],
                            'current_memory_mb': self._memory_history[-1],
                            'samples': len(self._memory_history)
                        }
                    )
                    alerts.append(alert)

        return alerts

    def detect_cpu_anomaly(self, metrics: ProcessedMetrics) -> List[Alert]:
        """检测CPU异常

        检测项目：
        1. 应用CPU过高
        2. 系统CPU过高
        3. CPU持续高负载

        Args:
            metrics: 处理后的指标数据

        Returns:
            检测到的CPU告警列表
        """
        if not metrics.cpu:
            return []

        alerts = []
        cpu = metrics.cpu
        thresholds = self._thresholds.cpu

        # 1. 应用CPU过高检测
        if cpu.app_cpu_percent > thresholds.high_app_cpu_percent:
            self._high_cpu_count += 1

            severity = AlertSeverity.CRITICAL if cpu.app_cpu_percent > 90 else AlertSeverity.WARNING
            alert = Alert(
                alert_type=AlertType.HIGH_CPU,
                severity=severity,
                metric_name="AppCPU",
                current_value=cpu.app_cpu_percent,
                threshold=thresholds.high_app_cpu_percent,
                message=f"应用CPU占用过高: {cpu.app_cpu_percent:.1f}% > 阈值 {thresholds.high_app_cpu_percent}%",
                timestamp=metrics.timestamp,
                session_id=self._session_id,
                device_id=metrics.device_id,
                app_id=metrics.app_id,
                context={
                    'sys_cpu_percent': cpu.sys_cpu_percent,
                    'moving_avg': cpu.moving_avg
                }
            )
            alerts.append(alert)
        else:
            self._high_cpu_count = 0

        # 2. 系统CPU过高检测
        if cpu.sys_cpu_percent > thresholds.high_sys_cpu_percent:
            alert = Alert(
                alert_type=AlertType.HIGH_CPU,
                severity=AlertSeverity.CRITICAL,
                metric_name="SysCPU",
                current_value=cpu.sys_cpu_percent,
                threshold=thresholds.high_sys_cpu_percent,
                message=f"系统CPU负载过高: {cpu.sys_cpu_percent:.1f}% > 阈值 {thresholds.high_sys_cpu_percent}%",
                timestamp=metrics.timestamp,
                session_id=self._session_id,
                device_id=metrics.device_id,
                app_id=metrics.app_id,
                context={'app_cpu_percent': cpu.app_cpu_percent}
            )
            alerts.append(alert)

        # 3. CPU持续高负载检测
        # 使用移动平均值来判断持续高负载
        if cpu.moving_avg > thresholds.sustained_cpu_percent:
            # 注意：这里需要累积时间判断，简化处理使用计数
            # 实际应用中应该基于真实时间
            if self._high_cpu_count > thresholds.sustained_duration_seconds:
                alert = Alert(
                    alert_type=AlertType.CPU_SUSTAINED,
                    severity=AlertSeverity.WARNING,
                    metric_name="CPUSustained",
                    current_value=cpu.moving_avg,
                    threshold=thresholds.sustained_cpu_percent,
                    message=f"CPU持续高负载: 移动平均 {cpu.moving_avg:.1f}% > 阈值 {thresholds.sustained_cpu_percent}%，持续 {self._high_cpu_count}秒",
                    timestamp=metrics.timestamp,
                    session_id=self._session_id,
                    device_id=metrics.device_id,
                    app_id=metrics.app_id,
                    context={
                        'current_cpu': cpu.app_cpu_percent,
                        'duration_seconds': self._high_cpu_count
                    }
                )
                alerts.append(alert)

        return alerts

    def detect_network_anomaly(self, metrics: ProcessedMetrics) -> List[Alert]:
        """检测网络异常

        检测项目：
        1. 上行异常（有下行无上行）
        2. 网络超时

        Args:
            metrics: 处理后的指标数据

        Returns:
            检测到的网络告警列表
        """
        if not metrics.network:
            return []

        alerts = []
        network = metrics.network
        thresholds = self._thresholds.network

        # 检测网络活动
        has_activity = (network.upload_speed_kb_s > 0 or
                       network.download_speed_kb_s > 0)

        if has_activity:
            self._last_network_time = metrics.timestamp
        else:
            # 检查网络超时
            if self._last_network_time:
                timeout_duration = (metrics.timestamp - self._last_network_time).total_seconds()
                if timeout_duration > thresholds.timeout_seconds:
                    alert = Alert(
                        alert_type=AlertType.NETWORK_TIMEOUT,
                        severity=AlertSeverity.WARNING,
                        metric_name="NetworkTimeout",
                        current_value=timeout_duration,
                        threshold=thresholds.timeout_seconds,
                        message=f"网络超时: 无网络活动 {timeout_duration:.0f}秒 > 阈值 {thresholds.timeout_seconds}秒",
                        timestamp=metrics.timestamp,
                        session_id=self._session_id,
                        device_id=metrics.device_id,
                        app_id=metrics.app_id,
                        context={'last_activity': self._last_network_time.isoformat()}
                    )
                    alerts.append(alert)

        # 检测上传异常（有下行无上行）
        if network.download_speed_kb_s > 0 and network.upload_speed_kb_s == 0:
            self._zero_upload_count += 1

            if self._zero_upload_count >= thresholds.zero_upload_threshold:
                alert = Alert(
                    alert_type=AlertType.UPLOAD_ERROR,
                    severity=AlertSeverity.WARNING,
                    metric_name="UploadSpeed",
                    current_value=0.0,
                    threshold=0.1,
                    message=f"可能的上传异常: 有下行({network.download_speed_kb_s:.1f}KB/s)但无上行，持续 {self._zero_upload_count}次",
                    timestamp=metrics.timestamp,
                    session_id=self._session_id,
                    device_id=metrics.device_id,
                    app_id=metrics.app_id,
                    context={'download_speed': network.download_speed_kb_s}
                )
                alerts.append(alert)
        else:
            self._zero_upload_count = 0

        return alerts

    def reset_state(self):
        """重置检测状态"""
        self._low_fps_count = 0
        self._high_cpu_count = 0
        self._zero_upload_count = 0
        self._last_network_time = None
        self._memory_history.clear()
