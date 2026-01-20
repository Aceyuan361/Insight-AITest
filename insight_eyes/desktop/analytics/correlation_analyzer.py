"""
异常关联分析器

负责分析异常之间的关联关系，生成详细的异常报告
辅助开发者定位性能问题的根本原因
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import numpy as np

from PyQt6.QtCore import QObject, pyqtSignal

from .models import (
    ProcessedMetrics, Alert, AlertType, AlertSeverity
)


class CorrelationAnalyzer(QObject):
    """异常关联分析器

    主要功能：
    1. 关联同一时间点的多维度数据
    2. 分析异常发生时的系统状态
    3. 生成异常详情报告
    4. 识别潜在的性能瓶颈
    """

    # 信号：生成关联分析报告
    report_generated = pyqtSignal(dict)  # 分析报告

    def __init__(self, session_id: int):
        """初始化关联分析器

        Args:
            session_id: 监控会话ID
        """
        super().__init__()
        self._session_id = session_id

        # 存储历史指标数据（用于关联分析）
        self._metrics_history = []  # List[ProcessedMetrics]
        self._alerts_history = []   # List[Alert]

        # 时间窗口（秒）
        self._correlation_window = 10

    def add_metrics(self, metrics: ProcessedMetrics):
        """添加指标数据到历史记录

        Args:
            metrics: 处理后的指标数据
        """
        self._metrics_history.append(metrics)

        # 添加告警到历史
        for alert in metrics.alerts:
            self._alerts_history.append(alert)

    def analyze_alert_context(self, alert: Alert) -> Dict[str, Any]:
        """分析告警发生时的上下文

        Args:
            alert: 要分析的告警

        Returns:
            包含上下文信息的字典
        """
        # 查找告警时间点附近的指标数据
        context_metrics = self._find_metrics_near_time(
            alert.timestamp, window_seconds=5
        )

        if not context_metrics:
            return {'error': '未找到上下文数据'}

        # 提取关键指标
        context = {
            'alert_type': alert.alert_type.value,
            'alert_time': alert.timestamp.isoformat(),
            'alert_message': alert.message,
            'metrics_at_alert_time': {}
        }

        # 添加FPS上下文
        if context_metrics.fps:
            context['metrics_at_alert_time']['fps'] = {
                'fps': context_metrics.fps.fps,
                'jank_count': context_metrics.fps.jank_count,
                'big_jank_count': context_metrics.fps.big_jank_count,
                'frame_time_avg': context_metrics.fps.frame_time_avg,
                'frame_time_max': context_metrics.fps.frame_time_max,
                'trend': context_metrics.fps.trend.value
            }

        # 添加内存上下文
        if context_metrics.memory:
            context['metrics_at_alert_time']['memory'] = {
                'total_mb': context_metrics.memory.total_mb,
                'native_mb': context_metrics.memory.native_mb,
                'dalvik_mb': context_metrics.memory.dalvik_mb,
                'growth_rate_mb_per_min': context_metrics.memory.growth_rate_mb_per_min,
                'trend': context_metrics.memory.trend.value
            }

        # 添加CPU上下文
        if context_metrics.cpu:
            context['metrics_at_alert_time']['cpu'] = {
                'app_cpu_percent': context_metrics.cpu.app_cpu_percent,
                'sys_cpu_percent': context_metrics.cpu.sys_cpu_percent,
                'moving_avg': context_metrics.cpu.moving_avg
            }

        # 添加网络上下文
        if context_metrics.network:
            context['metrics_at_alert_time']['network'] = {
                'upload_speed_kb_s': context_metrics.network.upload_speed_kb_s,
                'download_speed_kb_s': context_metrics.network.download_speed_kb_s
            }

        # 分析可能的原因
        context['possible_causes'] = self._analyze_possible_causes(
            alert, context_metrics
        )

        return context

    def correlate_fps_with_resources(self, alert: Alert) -> Dict[str, Any]:
        """关联FPS异常与资源使用情况

        Args:
            alert: FPS相关的告警

        Returns:
            关联分析结果
        """
        # 获取告警前后的指标数据
        before_metrics = self._find_metrics_near_time(
            alert.timestamp - timedelta(seconds=2), window_seconds=3
        )
        at_metrics = self._find_metrics_near_time(
            alert.timestamp, window_seconds=3
        )

        correlation = {
            'alert_type': alert.alert_type.value,
            'analysis_time': datetime.now().isoformat(),
            'correlation_summary': {}
        }

        if before_metrics and at_metrics:
            # 分析CPU变化
            if before_metrics.cpu and at_metrics.cpu:
                cpu_change = at_metrics.cpu.app_cpu_percent - before_metrics.cpu.app_cpu_percent
                correlation['correlation_summary']['cpu_change'] = f"{cpu_change:+.1f}%"

                if cpu_change > 20:
                    correlation['correlation_summary']['cpu_spike'] = (
                        f"卡顿时CPU突增{cpu_change:.1f}%，可能是CPU密集型操作导致"
                    )

            # 分析内存变化
            if before_metrics.memory and at_metrics.memory:
                mem_change = at_metrics.memory.total_mb - before_metrics.memory.total_mb
                correlation['correlation_summary']['memory_change'] = f"{mem_change:+.1f}MB"

                if mem_change > 50:
                    correlation['correlation_summary']['memory_spike'] = (
                        f"卡顿时内存增长{mem_change:.1f}MB，可能是GC或内存分配导致"
                    )

            # 分析网络变化
            if before_metrics.network and at_metrics.network:
                network_change = (at_metrics.network.download_speed_kb_s -
                                 before_metrics.network.download_speed_kb_s)
                correlation['correlation_summary']['network_change'] = f"{network_change:+.1f}KB/s"

        return correlation

    def correlate_memory_with_usage(self, alert: Alert) -> Dict[str, Any]:
        """关联内存异常与使用情况

        Args:
            alert: 内存相关的告警

        Returns:
            关联分析结果
        """
        correlation = {
            'alert_type': alert.alert_type.value,
            'analysis_time': datetime.now().isoformat(),
            'correlation_summary': {}
        }

        # 获取历史内存数据
        memory_history = [
            m.memory.total_mb for m in self._metrics_history[-30:]
            if m.memory and m.timestamp <= alert.timestamp
        ]

        if len(memory_history) >= 10:
            # 计算增长趋势
            growth_rate = np.polyfit(range(len(memory_history)), memory_history, 1)[0]

            correlation['correlation_summary']['memory_trend'] = {
                'growth_rate_per_sample': float(growth_rate),
                'samples': len(memory_history),
                'start_mb': float(memory_history[0]),
                'end_mb': float(memory_history[-1]),
                'total_growth_mb': float(memory_history[-1] - memory_history[0])
            }

            # 查找同一时间点的FPS和CPU
            at_metrics = self._find_metrics_near_time(alert.timestamp, window_seconds=3)

            if at_metrics and at_metrics.fps:
                correlation['correlation_summary']['fps_impact'] = {
                    'fps': at_metrics.fps.fps,
                    'jank_count': at_metrics.fps.jank_count,
                    'trend': at_metrics.fps.trend.value
                }

            if at_metrics and at_metrics.cpu:
                correlation['correlation_summary']['cpu_impact'] = {
                    'app_cpu_percent': at_metrics.cpu.app_cpu_percent,
                    'moving_avg': at_metrics.cpu.moving_avg
                }

        return correlation

    def generate_anomaly_report(self, alert: Alert) -> Dict[str, Any]:
        """生成异常详情报告

        Args:
            alert: 要生成报告的告警

        Returns:
            详细的异常报告
        """
        report = {
            'session_id': self._session_id,
            'alert_info': {
                'type': alert.alert_type.value,
                'severity': alert.severity.value,
                'metric': alert.metric_name,
                'current_value': alert.current_value,
                'threshold': alert.threshold,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat()
            },
            'context': {},
            'correlation': {},
            'recommendations': []
        }

        # 获取上下文
        context = self.analyze_alert_context(alert)
        report['context'] = context

        # 根据告警类型进行关联分析
        if alert.alert_type in [AlertType.LOW_FPS, AlertType.FPS_JANK, AlertType.FPS_BIG_JANK]:
            correlation = self.correlate_fps_with_resources(alert)
            report['correlation'] = correlation

            # 添加建议
            if 'cpu_spike' in correlation.get('correlation_summary', {}):
                report['recommendations'].append({
                    'priority': 'high',
                    'action': '检查主线程是否有耗时操作',
                    'details': correlation['correlation_summary']['cpu_spike']
                })

            if 'memory_spike' in correlation.get('correlation_summary', {}):
                report['recommendations'].append({
                    'priority': 'medium',
                    'action': '检查是否有频繁的内存分配或GC',
                    'details': correlation['correlation_summary']['memory_spike']
                })

        elif alert.alert_type in [AlertType.MEMORY_LEAK, AlertType.MEMORY_GROWTH, AlertType.HIGH_MEMORY]:
            correlation = self.correlate_memory_with_usage(alert)
            report['correlation'] = correlation

            # 添加建议
            report['recommendations'].append({
                'priority': 'high',
                'action': '使用内存分析工具检查内存泄露',
                'details': '重点检查长时间存活的对象引用'
            })

            if context.get('metrics_at_alert_time', {}).get('cpu', {}).get('app_cpu_percent', 0) > 60:
                report['recommendations'].append({
                    'priority': 'medium',
                    'action': '高CPU可能加剧内存问题，检查是否有循环引用'
                })

        elif alert.alert_type in [AlertType.HIGH_CPU, AlertType.CPU_SUSTAINED]:
            # CPU异常分析
            at_metrics = self._find_metrics_near_time(alert.timestamp, window_seconds=3)
            if at_metrics and at_metrics.fps:
                report['correlation']['fps_impact'] = {
                    'fps': at_metrics.fps.fps,
                    'jank_count': at_metrics.fps.jank_count
                }

                if at_metrics.fps.fps < 30:
                    report['recommendations'].append({
                        'priority': 'high',
                        'action': '高CPU导致低FPS，优化CPU密集型操作',
                        'details': f'CPU: {at_metrics.cpu.app_cpu_percent:.1f}%, FPS: {at_metrics.fps.fps:.1f}'
                    })

        # 发送报告信号
        self.report_generated.emit(report)

        return report

    def analyze_session_patterns(self) -> Dict[str, Any]:
        """分析整个会话的性能模式

        Returns:
            会话模式分析结果
        """
        if not self._metrics_history:
            return {'error': '无历史数据'}

        # 统计各类告警
        alert_counts = defaultdict(int)
        severity_counts = defaultdict(int)

        for alert in self._alerts_history:
            alert_counts[alert.alert_type.value] += 1
            severity_counts[alert.severity.value] += 1

        # 分析告警时间分布
        alert_timeline = []
        for alert in self._alerts_history:
            alert_timeline.append({
                'time': alert.timestamp.isoformat(),
                'type': alert.alert_type.value,
                'severity': alert.severity.value
            })

        # 识别告警聚集
        clusters = self._identify_alert_clusters()

        return {
            'session_id': self._session_id,
            'total_alerts': len(self._alerts_history),
            'alert_counts': dict(alert_counts),
            'severity_counts': dict(severity_counts),
            'alert_timeline': alert_timeline,
            'alert_clusters': clusters,
            'recommendations': self._generate_session_recommendations(alert_counts)
        }

    def _find_metrics_near_time(self, target_time: datetime,
                                window_seconds: int = 5) -> Optional[ProcessedMetrics]:
        """查找最接近目标时间的指标数据

        Args:
            target_time: 目标时间
            window_seconds: 时间窗口（秒）

        Returns:
            最接近的指标数据，如果找不到则返回None
        """
        if not self._metrics_history:
            return None

        # 在窗口内查找
        window_start = target_time - timedelta(seconds=window_seconds)
        window_end = target_time + timedelta(seconds=window_seconds)

        candidates = [
            m for m in self._metrics_history
            if window_start <= m.timestamp <= window_end
        ]

        if not candidates:
            return None

        # 返回最接近的一个
        candidates.sort(key=lambda m: abs((m.timestamp - target_time).total_seconds()))
        return candidates[0]

    def _analyze_possible_causes(self, alert: Alert,
                                 metrics: ProcessedMetrics) -> List[str]:
        """分析告警的可能原因

        Args:
            alert: 告警对象
            metrics: 指标数据

        Returns:
            可能原因列表
        """
        causes = []

        if alert.alert_type == AlertType.LOW_FPS:
            if metrics.cpu and metrics.cpu.app_cpu_percent > 70:
                causes.append("CPU占用过高可能导致渲染延迟")

            if metrics.memory and metrics.memory.total_mb > 400:
                causes.append("内存占用高可能触发频繁GC导致卡顿")

            if metrics.network and metrics.network.download_speed_kb_s > 1000:
                causes.append("大量网络下载可能占用主线程")

        elif alert.alert_type == AlertType.MEMORY_LEAK:
            causes.append("可能存在未释放的对象引用")
            causes.append("检查静态变量、单例、监听器等常见泄露点")

            if metrics.cpu and metrics.cpu.app_cpu_percent > 60:
                causes.append("高CPU可能加剧内存分配，检查循环中的对象创建")

        elif alert.alert_type == AlertType.HIGH_CPU:
            causes.append("检查主线程是否有耗时操作")
            causes.append("检查是否有死循环或频繁计算")

            if metrics.fps and metrics.fps.fps < 30:
                causes.append("高CPU导致FPS下降，优化算法或移到子线程")

        return causes

    def _identify_alert_clusters(self) -> List[Dict[str, Any]]:
        """识别告警聚集（短时间内多次告警）

        Returns:
            告警聚集列表
        """
        if not self._alerts_history:
            return []

        clusters = []
        current_cluster = None

        for alert in sorted(self._alerts_history, key=lambda a: a.timestamp):
            if current_cluster is None:
                current_cluster = {
                    'start_time': alert.timestamp,
                    'end_time': alert.timestamp,
                    'alerts': [alert],
                    'types': [alert.alert_type.value]
                }
            else:
                time_diff = (alert.timestamp - current_cluster['end_time']).total_seconds()

                if time_diff <= 10:  # 10秒内视为同一聚集
                    current_cluster['end_time'] = alert.timestamp
                    current_cluster['alerts'].append(alert)
                    if alert.alert_type.value not in current_cluster['types']:
                        current_cluster['types'].append(alert.alert_type.value)
                else:
                    # 结束当前聚集
                    if len(current_cluster['alerts']) > 1:
                        clusters.append({
                            'start_time': current_cluster['start_time'].isoformat(),
                            'end_time': current_cluster['end_time'].isoformat(),
                            'alert_count': len(current_cluster['alerts']),
                            'alert_types': current_cluster['types']
                        })

                    # 开始新聚集
                    current_cluster = {
                        'start_time': alert.timestamp,
                        'end_time': alert.timestamp,
                        'alerts': [alert],
                        'types': [alert.alert_type.value]
                    }

        # 添加最后一个聚集
        if current_cluster and len(current_cluster['alerts']) > 1:
            clusters.append({
                'start_time': current_cluster['start_time'].isoformat(),
                'end_time': current_cluster['end_time'].isoformat(),
                'alert_count': len(current_cluster['alerts']),
                'alert_types': current_cluster['types']
            })

        return clusters

    def _generate_session_recommendations(self, alert_counts: Dict[str, int]) -> List[str]:
        """生成会话级别的优化建议

        Args:
            alert_counts: 告警统计

        Returns:
            建议列表
        """
        recommendations = []

        # FPS相关建议
        if alert_counts.get('low_fps', 0) > 5:
            recommendations.append("频繁出现低FPS，建议全面检查渲染性能")

        if alert_counts.get('fps_jank', 0) > 10:
            recommendations.append("卡顿次数过多，建议优化主线程操作")

        # 内存相关建议
        if alert_counts.get('memory_leak', 0) > 0:
            recommendations.append("检测到内存泄露，使用内存分析工具定位泄露点")

        if alert_counts.get('memory_growth', 0) > 3:
            recommendations.append("内存持续增长，检查对象生命周期管理")

        # CPU相关建议
        if alert_counts.get('high_cpu', 0) > 5:
            recommendations.append("频繁的高CPU占用，检查算法复杂度和线程使用")

        if alert_counts.get('cpu_sustained', 0) > 2:
            recommendations.append("CPU持续高负载，可能存在死循环或资源竞争")

        return recommendations

    def clear_history(self):
        """清空历史数据"""
        self._metrics_history.clear()
        self._alerts_history.clear()
