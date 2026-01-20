"""
数据访问层 - 提供高级数据查询接口
封装复杂的数据查询逻辑
"""
from typing import List, Tuple, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from .database import DatabaseManager


class MetricsRepository:
    """性能指标数据访问类 - 提供时序数据查询和统计"""

    def __init__(self, db: DatabaseManager):
        """
        初始化数据访问层

        Args:
            db: 数据库管理器实例
        """
        self.db = db

    def get_fps_trend(self, session_id: int) -> List[Tuple[datetime, float]]:
        """
        获取FPS趋势数据

        Args:
            session_id: 会话ID

        Returns:
            [(timestamp, fps), ...] 列表
        """
        metrics = self.db.get_metrics(session_id)
        return [
            (datetime.fromisoformat(m['timestamp']), m['fps'] or 0)
            for m in metrics if m['fps'] is not None
        ]

    def get_memory_trend(self, session_id: int) -> List[Tuple[datetime, float]]:
        """
        获取内存趋势数据

        Args:
            session_id: 会话ID

        Returns:
            [(timestamp, memory_pss), ...] 列表，单位MB
        """
        metrics = self.db.get_metrics(session_id)
        return [
            (datetime.fromisoformat(m['timestamp']), m['memory_pss'] or 0)
            for m in metrics if m['memory_pss'] is not None
        ]

    def get_cpu_trend(self, session_id: int) -> List[Tuple[datetime, float, float]]:
        """
        获取CPU趋势数据

        Args:
            session_id: 会话ID

        Returns:
            [(timestamp, cpu_app, cpu_system), ...] 列表，百分比
        """
        metrics = self.db.get_metrics(session_id)
        return [
            (
                datetime.fromisoformat(m['timestamp']),
                m['cpu_app'] or 0,
                m['cpu_system'] or 0
            )
            for m in metrics if m['cpu_app'] is not None
        ]

    def get_network_trend(self, session_id: int) -> List[Tuple[datetime, float, float]]:
        """
        获取网络流量趋势数据

        Args:
            session_id: 会话ID

        Returns:
            [(timestamp, up_speed, down_speed), ...] 列表，单位KB/s
        """
        metrics = self.db.get_metrics(session_id)
        return [
            (
                datetime.fromisoformat(m['timestamp']),
                m['network_up_speed'] or 0,
                m['network_down_speed'] or 0
            )
            for m in metrics if m['network_up_speed'] is not None
        ]

    def get_battery_trend(self, session_id: int) -> List[Tuple[datetime, float, float]]:
        """
        获取电池电量趋势数据

        Args:
            session_id: 会话ID

        Returns:
            [(timestamp, battery_level, battery_temp), ...] 列表
        """
        metrics = self.db.get_metrics(session_id)
        return [
            (
                datetime.fromisoformat(m['timestamp']),
                m['battery_level'] or 0,
                m['battery_temp'] or 0
            )
            for m in metrics if m['battery_level'] is not None
        ]

    def get_statistics(self, session_id: int) -> Dict:
        """
        获取会话的统计数据（平均值、最大值、最小值、标准差）

        Args:
            session_id: 会话ID

        Returns:
            统计数据字典
        """
        metrics = self.db.get_metrics(session_id)

        if not metrics:
            return {}

        stats = {}

        # FPS统计
        fps_values = [m['fps'] for m in metrics if m['fps'] is not None and m['fps'] > 0]
        if fps_values:
            stats['fps'] = {
                'avg': round(statistics.mean(fps_values), 2),
                'max': round(max(fps_values), 2),
                'min': round(min(fps_values), 2),
                'median': round(statistics.median(fps_values), 2),
                'stdev': round(statistics.stdev(fps_values), 2) if len(fps_values) > 1 else 0
            }

        # CPU统计
        cpu_app_values = [m['cpu_app'] for m in metrics if m['cpu_app'] is not None]
        if cpu_app_values:
            stats['cpu_app'] = {
                'avg': round(statistics.mean(cpu_app_values), 2),
                'max': round(max(cpu_app_values), 2),
                'min': round(min(cpu_app_values), 2),
                'median': round(statistics.median(cpu_app_values), 2)
            }

        # 内存统计
        memory_pss_values = [m['memory_pss'] for m in metrics if m['memory_pss'] is not None]
        if memory_pss_values:
            stats['memory_pss'] = {
                'avg': round(statistics.mean(memory_pss_values), 2),
                'max': round(max(memory_pss_values), 2),
                'min': round(min(memory_pss_values), 2),
                'median': round(statistics.median(memory_pss_values), 2)
            }

        # 网络统计
        network_up_values = [m['network_up_speed'] for m in metrics if m['network_up_speed'] is not None]
        network_down_values = [m['network_down_speed'] for m in metrics if m['network_down_speed'] is not None]

        if network_up_values:
            stats['network_up'] = {
                'avg': round(statistics.mean(network_up_values), 2),
                'max': round(max(network_up_values), 2),
                'total_mb': round(sum(network_up_values) / 1024, 2)  # KB -> MB
            }

        if network_down_values:
            stats['network_down'] = {
                'avg': round(statistics.mean(network_down_values), 2),
                'max': round(max(network_down_values), 2),
                'total_mb': round(sum(network_down_values) / 1024, 2)
            }

        # 卡顿统计
        jank_counts = [m['fps_jank_count'] for m in metrics if m['fps_jank_count'] is not None]
        if jank_counts:
            stats['jank'] = {
                'total': sum(jank_counts),
                'avg_per_sample': round(statistics.mean(jank_counts), 2)
            }

        return stats

    def get_time_series_data(self, session_id: int,
                             start_time: datetime = None,
                             end_time: datetime = None,
                             metrics: List[str] = None) -> Dict[str, List[Tuple[datetime, float]]]:
        """
        获取多个指标的时间序列数据

        Args:
            session_id: 会话ID
            start_time: 开始时间
            end_time: 结束时间
            metrics: 要获取的指标列表，如 ['cpu_app', 'memory_pss', 'fps']

        Returns:
            {metric_name: [(timestamp, value), ...], ...}
        """
        if metrics is None:
            metrics = ['cpu_app', 'memory_pss', 'fps', 'network_up_speed', 'network_down_speed']

        all_metrics = self.db.get_metrics(session_id, start_time, end_time)

        result = defaultdict(list)

        for m in all_metrics:
            timestamp = datetime.fromisoformat(m['timestamp'])
            for metric in metrics:
                value = m.get(metric)
                if value is not None:
                    result[metric].append((timestamp, value))

        return dict(result)

    def get_aggregated_metrics(self, session_id: int, interval_seconds: int = 60) -> List[Dict]:
        """
        获取聚合后的指标数据（按时间间隔聚合）

        Args:
            session_id: 会话ID
            interval_seconds: 聚合时间间隔（秒）

        Returns:
            聚合后的数据列表
        """
        metrics = self.db.get_metrics(session_id)

        if not metrics:
            return []

        # 按时间间隔分组
        aggregated = defaultdict(lambda: defaultdict(list))

        for m in metrics:
            timestamp = datetime.fromisoformat(m['timestamp'])
            # 计算聚合时间段
            bucket = timestamp.replace(
                second=0,
                microsecond=0
            )
            bucket = bucket.replace(
                minute=(bucket.minute // (interval_seconds // 60)) * (interval_seconds // 60)
            )

            # 收集各项指标
            for key, value in m.items():
                if key not in ['id', 'session_id', 'timestamp'] and value is not None:
                    aggregated[bucket][key].append(value)

        # 计算每个时间段的平均值
        result = []
        for bucket in sorted(aggregated.keys()):
            row = {'timestamp': bucket.isoformat()}
            for metric, values in aggregated[bucket].items():
                if isinstance(values[0], (int, float)):
                    row[metric] = round(statistics.mean(values), 2)
            result.append(row)

        return result

    def compare_sessions(self, session_ids: List[int]) -> Dict:
        """
        比较多个会话的性能指标

        Args:
            session_ids: 会话ID列表

        Returns:
            比较结果字典
        """
        comparison = {}

        for sid in session_ids:
            session = self.db.get_session(sid)
            if session:
                stats = self.get_statistics(sid)
                comparison[sid] = {
                    'session_info': {
                        'device_id': session['device_id'],
                        'package_name': session['package_name'],
                        'start_time': session['start_time'],
                        'tags': session.get('tags')
                    },
                    'statistics': stats
                }

        return comparison


class AlertRepository:
    """告警数据访问类"""

    def __init__(self, db: DatabaseManager):
        """
        初始化告警数据访问层

        Args:
            db: 数据库管理器实例
        """
        self.db = db

    def get_alert_summary(self, session_id: int = None) -> Dict:
        """
        获取告警汇总统计

        Args:
            session_id: 会话ID，可选

        Returns:
            告警统计汇总
        """
        alerts = self.db.get_alerts(session_id=session_id)

        summary = {
            'total_count': len(alerts),
            'by_type': defaultdict(int),
            'by_severity': defaultdict(int),
            'unresolved_count': 0,
            'recent_alerts': []
        }

        for alert in alerts:
            summary['by_type'][alert['alert_type']] += 1
            summary['by_severity'][alert['severity']] += 1
            if not alert['resolved']:
                summary['unresolved_count'] += 1

        # 最近的告警
        summary['recent_alerts'] = [
            {
                'type': a['alert_type'],
                'severity': a['severity'],
                'description': a['description'],
                'timestamp': a['timestamp']
            }
            for a in alerts[:10]
        ]

        # 转换defaultdict为普通dict
        summary['by_type'] = dict(summary['by_type'])
        summary['by_severity'] = dict(summary['by_severity'])

        return summary

    def get_alert_trends(self, days: int = 7) -> Dict[str, List[Tuple[datetime, int]]]:
        """
        获取告警趋势（按天统计）

        Args:
            days: 统计天数

        Returns:
            {alert_type: [(date, count), ...], ...}
        """
        alerts = self.db.get_alerts()
        cutoff_date = datetime.now() - timedelta(days=days)

        # 过滤指定时间范围的告警
        filtered_alerts = [
            a for a in alerts
            if datetime.fromisoformat(a['timestamp']) >= cutoff_date
        ]

        # 按日期和类型分组
        trends = defaultdict(lambda: defaultdict(int))

        for alert in filtered_alerts:
            date = datetime.fromisoformat(alert['timestamp']).date()
            trends[alert['alert_type']][date] += 1

        # 转换为列表格式
        result = {}
        for alert_type, dates in trends.items():
            result[alert_type] = sorted(dates.items())

        return result

    def get_performance_issues(self, session_id: int) -> Dict:
        """
        分析性能问题

        Args:
            session_id: 会话ID

        Returns:
            性能问题分析报告
        """
        alerts = self.db.get_alerts(session_id=session_id, resolved=False)

        issues = {
            'critical_issues': [],
            'warnings': [],
            'recommendations': []
        }

        for alert in alerts:
            issue = {
                'type': alert['alert_type'],
                'metric': alert['metric_name'],
                'current_value': alert['current_value'],
                'threshold': alert['threshold_value'],
                'description': alert['description'],
                'timestamp': alert['timestamp']
            }

            if alert['severity'] == 'critical':
                issues['critical_issues'].append(issue)
            else:
                issues['warnings'].append(issue)

        # 生成优化建议
        if any(a['alert_type'] == 'high_memory' for a in alerts):
            issues['recommendations'].append({
                'category': 'memory',
                'suggestion': '检查是否存在内存泄漏，考虑使用内存分析工具定位问题'
            })

        if any(a['alert_type'] == 'low_fps' for a in alerts):
            issues['recommendations'].append({
                'category': 'performance',
                'suggestion': '优化主线程操作，减少复杂计算和布局层次'
            })

        return issues


class SessionRepository:
    """会话数据访问类"""

    def __init__(self, db: DatabaseManager):
        """
        初始化会话数据访问层

        Args:
            db: 数据库管理器实例
        """
        self.db = db

    def get_session_overview(self, session_id: int) -> Dict:
        """
        获取会话概览信息

        Args:
            session_id: 会话ID

        Returns:
            会话概览数据
        """
        session = self.db.get_session(session_id)
        if not session:
            return None

        metrics = self.db.get_metrics(session_id)
        alerts = self.db.get_alerts(session_id=session_id)

        # 计算监控时长
        start_time = datetime.fromisoformat(session['start_time'])
        end_time = datetime.fromisoformat(session['end_time']) if session['end_time'] else datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 获取设备信息
        device = self.db.get_device(session['device_id'])

        overview = {
            'session_info': {
                'id': session_id,
                'device_id': session['device_id'],
                'device_name': device['name'] if device else 'Unknown',
                'platform': device['platform'] if device else 'Unknown',
                'package_name': session['package_name'],
                'start_time': session['start_time'],
                'end_time': session['end_time'],
                'duration_seconds': duration,
                'duration_formatted': self._format_duration(duration),
                'sample_interval': session['sample_interval'],
                'tags': session.get('tags', {})
            },
            'data_summary': {
                'total_samples': len(metrics),
                'alert_count': len(alerts),
                'unresolved_alerts': len([a for a in alerts if not a['resolved']])
            }
        }

        return overview

    def _format_duration(self, seconds: float) -> str:
        """格式化时长为可读字符串"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if hours > 0:
            parts.append(f"{hours}小时")
        if minutes > 0:
            parts.append(f"{minutes}分钟")
        if secs > 0 or not parts:
            parts.append(f"{secs}秒")

        return " ".join(parts)

    def search_sessions(self, device_id: str = None,
                       package_name: str = None,
                       start_date: datetime = None,
                       end_date: datetime = None,
                       tags: Dict = None) -> List[Dict]:
        """
        搜索会话

        Args:
            device_id: 设备ID过滤
            package_name: 包名过滤
            start_date: 开始日期
            end_date: 结束日期
            tags: 标签过滤

        Returns:
            匹配的会话列表
        """
        sessions = self.db.get_recent_sessions(limit=1000)

        # 应用过滤条件
        filtered = []
        for session in sessions:
            if device_id and session['device_id'] != device_id:
                continue

            if package_name and session['package_name'] != package_name:
                continue

            if start_date:
                session_time = datetime.fromisoformat(session['start_time'])
                if session_time < start_date:
                    continue

            if end_date:
                session_time = datetime.fromisoformat(session['start_time'])
                if session_time > end_date:
                    continue

            if tags:
                session_tags = session.get('tags', {})
                if not all(session_tags.get(k) == v for k, v in tags.items()):
                    continue

            filtered.append(session)

        return filtered

    def get_test_scenarios(self) -> List[Dict]:
        """
        获取所有测试场景（按tags分组）

        Returns:
            场景列表
        """
        sessions = self.db.get_recent_sessions(limit=1000)

        scenarios = defaultdict(lambda: {
            'count': 0,
            'session_ids': [],
            'devices': set(),
            'packages': set()
        })

        for session in sessions:
            tags = session.get('tags', {})
            if tags:
                # 使用tags的JSON字符串作为场景标识
                scenario_key = str(sorted(tags.items()))
                scenarios[scenario_key]['count'] += 1
                scenarios[scenario_key]['session_ids'].append(session['id'])
                scenarios[scenario_key]['devices'].add(session['device_id'])
                scenarios[scenario_key]['packages'].add(session['package_name'])
                scenarios[scenario_key]['tags'] = tags

        # 转换为列表并清理set
        result = []
        for scenario in scenarios.values():
            scenario['devices'] = list(scenario['devices'])
            scenario['packages'] = list(scenario['packages'])
            result.append(scenario)

        return result
