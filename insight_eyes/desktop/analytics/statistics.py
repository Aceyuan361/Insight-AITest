"""
统计分析器

负责计算性能会话的统计数据，包括平均值、分位数、峰值等
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import numpy as np

from PyQt6.QtCore import QObject, pyqtSignal

from .models import (
    ProcessedMetrics, SessionSummary, AlertSeverity
)


class StatisticsAnalyzer(QObject):
    """统计分析器

    主要功能：
    1. 计算监控会话的统计摘要
    2. 对比多个会话的性能
    3. 计算分位数和标准差
    4. 生成性能报告
    """

    # 信号：摘要计算完成
    summary_ready = pyqtSignal(object)  # SessionSummary

    def __init__(self, session_id: int):
        """初始化统计分析器

        Args:
            session_id: 监控会话ID
        """
        super().__init__()
        self._session_id = session_id
        self._metrics_history: List[ProcessedMetrics] = []

    def add_metrics(self, metrics: ProcessedMetrics):
        """添加指标数据

        Args:
            metrics: 处理后的指标数据
        """
        self._metrics_history.append(metrics)

    def calculate_session_summary(self, start_time: Optional[datetime] = None,
                                 end_time: Optional[datetime] = None) -> Optional[SessionSummary]:
        """计算监控会话摘要

        Args:
            start_time: 会话开始时间，如果为None则使用第一个数据点
            end_time: 会话结束时间，如果为None则使用最后一个数据点

        Returns:
            会话摘要对象
        """
        if not self._metrics_history:
            return None

        # 过滤时间范围内的数据
        if start_time and end_time:
            filtered = [m for m in self._metrics_history
                       if start_time <= m.timestamp <= end_time]
        else:
            filtered = self._metrics_history

        if not filtered:
            return None

        # 确定时间范围
        actual_start = filtered[0].timestamp
        actual_end = filtered[-1].timestamp
        duration = (actual_end - actual_start).total_seconds()

        # 提取各项指标数据
        fps_values = [m.fps.fps for m in filtered if m.fps and m.fps.fps > 0]
        jank_counts = [m.fps.jank_count for m in filtered if m.fps]
        big_jank_counts = [m.fps.big_jank_count for m in filtered if m.fps]

        memory_values = [m.memory.total_mb for m in filtered if m.memory]
        cpu_values = [m.cpu.app_cpu_percent for m in filtered if m.cpu]

        network_sent = [m.network.total_sent_mb for m in filtered if m.network]
        network_received = [m.network.total_received_mb for m in filtered if m.network]

        # 统计告警
        all_alerts = []
        for m in filtered:
            all_alerts.extend(m.alerts)

        critical_count = sum(1 for a in all_alerts if a.severity == AlertSeverity.CRITICAL)
        warning_count = sum(1 for a in all_alerts if a.severity == AlertSeverity.WARNING)

        # 计算统计数据
        summary = SessionSummary(
            session_id=self._session_id,
            start_time=actual_start,
            end_time=actual_end,
            duration_seconds=duration,

            # FPS统计
            avg_fps=float(np.mean(fps_values)) if fps_values else 0.0,
            min_fps=float(np.min(fps_values)) if fps_values else 0.0,
            max_fps=float(np.max(fps_values)) if fps_values else 0.0,
            fps_p95=float(np.percentile(fps_values, 95)) if len(fps_values) > 0 else 0.0,
            fps_std=float(np.std(fps_values)) if fps_values else 0.0,
            jank_count=int(np.sum(jank_counts)) if jank_counts else 0,
            big_jank_count=int(np.sum(big_jank_counts)) if big_jank_counts else 0,

            # 内存统计
            avg_memory_mb=float(np.mean(memory_values)) if memory_values else 0.0,
            peak_memory_mb=float(np.max(memory_values)) if memory_values else 0.0,
            memory_leaked_mb=float(memory_values[-1] - memory_values[0]) if len(memory_values) > 1 else 0.0,

            # CPU统计
            avg_cpu_percent=float(np.mean(cpu_values)) if cpu_values else 0.0,
            peak_cpu_percent=float(np.max(cpu_values)) if cpu_values else 0.0,

            # 网络统计
            total_data_sent_mb=float(network_sent[-1]) if network_sent else 0.0,
            total_data_received_mb=float(network_received[-1]) if network_received else 0.0,

            # 告警统计
            alert_count=len(all_alerts),
            critical_count=critical_count,
            warning_count=warning_count
        )

        # 发送信号
        self.summary_ready.emit(summary)

        return summary

    def compare_sessions(self, other_session_ids: List[int],
                        other_summaries: Dict[int, 'SessionSummary']) -> Dict[str, Any]:
        """对比多个会话的性能

        Args:
            other_session_ids: 其他会话ID列表
            other_summaries: 其他会话的摘要数据 {session_id: SessionSummary}

        Returns:
            对比结果
        """
        # 计算当前会话摘要
        current_summary = self.calculate_session_summary()
        if not current_summary:
            return {'error': '当前会话无数据'}

        comparison = {
            'current_session': current_summary.to_dict(),
            'other_sessions': [],
            'analysis': {}
        }

        # 添加其他会话数据
        for session_id in other_session_ids:
            if session_id in other_summaries:
                comparison['other_sessions'].append({
                    'session_id': session_id,
                    'summary': other_summaries[session_id].to_dict()
                })

        # 对比分析
        if comparison['other_sessions']:
            other = comparison['other_sessions'][0]['summary']

            comparison['analysis'] = {
                'fps_change': self._calculate_change(
                    current_summary.avg_fps,
                    other['avg_fps']
                ),
                'memory_change': self._calculate_change(
                    current_summary.avg_memory_mb,
                    other['avg_memory_mb']
                ),
                'cpu_change': self._calculate_change(
                    current_summary.avg_cpu_percent,
                    other['avg_cpu_percent']
                ),
                'jank_change': self._calculate_change(
                    current_summary.jank_count,
                    other['jank_count']
                ),
                'alert_change': self._calculate_change(
                    current_summary.alert_count,
                    other['alert_count']
                )
            }

        return comparison

    def calculate_percentile(self, metric_name: str, percentile: float) -> float:
        """计算指定指标的百分位数

        Args:
            metric_name: 指标名称 ('fps', 'memory', 'cpu')
            percentile: 百分位数 (0-100)

        Returns:
            百分位数值
        """
        if percentile < 0 or percentile > 100:
            raise ValueError("百分位数必须在0-100之间")

        values = []
        for m in self._metrics_history:
            if metric_name == 'fps' and m.fps and m.fps.fps > 0:
                values.append(m.fps.fps)
            elif metric_name == 'memory' and m.memory:
                values.append(m.memory.total_mb)
            elif metric_name == 'cpu' and m.cpu:
                values.append(m.cpu.app_cpu_percent)

        if not values:
            return 0.0

        return float(np.percentile(values, percentile))

    def get_time_series_data(self, metric_name: str) -> List[Dict[str, Any]]:
        """获取时间序列数据（用于绘图）

        Args:
            metric_name: 指标名称

        Returns:
            时间序列数据列表 [{'timestamp': ..., 'value': ...}, ...]
        """
        time_series = []

        for m in self._metrics_history:
            value = None

            if metric_name == 'fps' and m.fps:
                value = m.fps.fps
            elif metric_name == 'memory' and m.memory:
                value = m.memory.total_mb
            elif metric_name == 'cpu' and m.cpu:
                value = m.cpu.app_cpu_percent
            elif metric_name == 'jank' and m.fps:
                value = m.fps.jank_count

            if value is not None:
                time_series.append({
                    'timestamp': m.timestamp.isoformat(),
                    'value': float(value)
                })

        return time_series

    def calculate_stability_score(self) -> Dict[str, float]:
        """计算性能稳定性评分

        评分标准：
        - FPS稳定性：基于FPS标准差和波动
        - 内存稳定性：基于内存增长和波动
        - CPU稳定性：基于CPU波动

        Returns:
            各项稳定性评分 (0-100)
        """
        fps_values = [m.fps.fps for m in self._metrics_history if m.fps and m.fps.fps > 0]
        memory_values = [m.memory.total_mb for m in self._metrics_history if m.memory]
        cpu_values = [m.cpu.app_cpu_percent for m in self._metrics_history if m.cpu]

        scores = {}

        # FPS稳定性评分
        if len(fps_values) > 10:
            fps_std = np.std(fps_values)
            fps_mean = np.mean(fps_values)
            fps_cv = fps_std / fps_mean if fps_mean > 0 else 0  # 变异系数

            # 变异系数越小越稳定
            fps_stability = max(0, 100 - fps_cv * 100)
            scores['fps_stability'] = round(fps_stability, 2)
        else:
            scores['fps_stability'] = 0.0

        # 内存稳定性评分
        if len(memory_values) > 10:
            memory_std = np.std(memory_values)
            memory_mean = np.mean(memory_values)
            memory_cv = memory_std / memory_mean if memory_mean > 0 else 0

            # 检查是否有持续增长
            memory_growth = memory_values[-1] - memory_values[0]
            growth_penalty = min(50, max(0, (memory_growth - 50) / 10))  # 增长超过50MB开始扣分

            memory_stability = max(0, 100 - memory_cv * 50 - growth_penalty)
            scores['memory_stability'] = round(memory_stability, 2)
        else:
            scores['memory_stability'] = 0.0

        # CPU稳定性评分
        if len(cpu_values) > 10:
            cpu_std = np.std(cpu_values)
            cpu_mean = np.mean(cpu_values)
            cpu_cv = cpu_std / cpu_mean if cpu_mean > 0 else 0

            cpu_stability = max(0, 100 - cpu_cv * 100)
            scores['cpu_stability'] = round(cpu_stability, 2)
        else:
            scores['cpu_stability'] = 0.0

        # 总体稳定性
        scores['overall_stability'] = round(np.mean(list(scores.values())), 2)

        return scores

    def detect_performance_degradation(self, window_seconds: int = 60) -> List[Dict[str, Any]]:
        """检测性能退化

        对比前后两个时间窗口的性能指标

        Args:
            window_seconds: 时间窗口大小（秒）

        Returns:
            检测到的性能退化列表
        """
        if len(self._metrics_history) < 2:
            return []

        degradations = []

        # 找到中间分割点
        mid_time = self._metrics_history[0].timestamp + timedelta(seconds=window_seconds)

        early_window = [m for m in self._metrics_history if m.timestamp <= mid_time]
        late_window = [m for m in self._metrics_history if m.timestamp > mid_time]

        if not early_window or not late_window:
            return []

        # 对比FPS
        early_fps = [m.fps.fps for m in early_window if m.fps and m.fps.fps > 0]
        late_fps = [m.fps.fps for m in late_window if m.fps and m.fps.fps > 0]

        if early_fps and late_fps:
            early_avg = np.mean(early_fps)
            late_avg = np.mean(late_fps)

            if late_avg < early_avg * 0.8:  # 下降超过20%
                degradations.append({
                    'metric': 'FPS',
                    'early_avg': float(early_avg),
                    'late_avg': float(late_avg),
                    'degradation_percent': round((early_avg - late_avg) / early_avg * 100, 2),
                    'severity': 'high' if late_avg < early_avg * 0.6 else 'medium'
                })

        # 对比内存
        early_mem = [m.memory.total_mb for m in early_window if m.memory]
        late_mem = [m.memory.total_mb for m in late_window if m.memory]

        if early_mem and late_mem:
            early_avg = np.mean(early_mem)
            late_avg = np.mean(late_mem)

            if late_avg > early_avg * 1.3:  # 增长超过30%
                degradations.append({
                    'metric': 'Memory',
                    'early_avg': float(early_avg),
                    'late_avg': float(late_avg),
                    'growth_percent': round((late_avg - early_avg) / early_avg * 100, 2),
                    'severity': 'high' if late_avg > early_avg * 1.5 else 'medium'
                })

        return degradations

    def _calculate_change(self, current: float, baseline: float) -> Dict[str, float]:
        """计算变化率

        Args:
            current: 当前值
            baseline: 基线值

        Returns:
            变化信息
        """
        if baseline == 0:
            return {
                'absolute': float(current),
                'relative': 0.0,
                'direction': 'unchanged'
            }

        change = current - baseline
        relative = (change / baseline) * 100

        direction = 'unchanged'
        if abs(relative) > 5:
            direction = 'improved' if change < 0 else 'degraded'

        return {
            'absolute': float(change),
            'relative': float(relative),
            'direction': direction
        }

    def export_metrics(self, format: str = 'json') -> str:
        """导出指标数据

        Args:
            format: 导出格式 ('json', 'csv')

        Returns:
            导出的数据字符串
        """
        if format == 'json':
            import json
            data = [m.to_dict() for m in self._metrics_history]
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif format == 'csv':
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # 写入表头
            writer.writerow([
                'timestamp', 'fps', 'memory_mb', 'cpu_percent',
                'upload_kb_s', 'download_kb_s', 'alert_count'
            ])

            # 写入数据
            for m in self._metrics_history:
                row = [
                    m.timestamp.isoformat(),
                    m.fps.fps if m.fps else '',
                    m.memory.total_mb if m.memory else '',
                    m.cpu.app_cpu_percent if m.cpu else '',
                    m.network.upload_speed_kb_s if m.network else '',
                    m.network.download_speed_kb_s if m.network else '',
                    len(m.alerts)
                ]
                writer.writerow(row)

            return output.getvalue()
        else:
            raise ValueError(f"不支持的格式: {format}")

    def clear_history(self):
        """清空历史数据"""
        self._metrics_history.clear()
