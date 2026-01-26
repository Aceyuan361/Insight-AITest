# -*- coding: utf-8 -*-
"""
ECharts 图表数据构建器
将数据库数据转换为 ECharts 配置格式
"""
from typing import List, Dict, Any
from logzero import logger


class ChartDataBuilder:
    """ECharts 图表数据构建器"""

    COLORS = {
        'fps': '#ffb400',
        'cpu': '#00d4ff',
        'cpu_system': '#00bcd4',
        'memory': '#7000ff',
        'network_up': '#00ff87',
        'network_down': '#0062ff',
    }

    @staticmethod
    def build_chart_config(metric_type: str, timestamps: List[str],
                          data: List[float], data2: List[float] = None) -> Dict[str, Any]:
        """构建 ECharts 图表配置"""
        y_min, y_max = ChartDataBuilder._calculate_y_axis(data, metric_type)
        
        config = {
            'title': {'text': ChartDataBuilder._get_title(metric_type), 'textStyle': {'color': '#e0e6ed'}},
            'tooltip': {'trigger': 'axis', 'backgroundColor': 'rgba(10,14,23,0.95)', 'borderColor': ChartDataBuilder.COLORS.get(metric_type, '#00d4ff')},
            'grid': {'left': '3%', 'right': '4%', 'bottom': '3%', 'top': '15%', 'containLabel': True},
            'xAxis': {'type': 'category', 'data': timestamps, 'axisLine': {'lineStyle': {'color': '#1a1f2e'}}, 'axisLabel': {'color': '#64748b'}},
            'yAxis': {'type': 'value', 'min': y_min, 'max': y_max, 'axisLine': {'lineStyle': {'color': '#1a1f2e'}}, 'splitLine': {'lineStyle': {'color': 'rgba(255,255,255,0.05)'}}},
            'series': []
        }
        
        series1 = ChartDataBuilder._build_series(metric_type, data)
        config['series'].append(series1)
        
        if data2:
            series2 = ChartDataBuilder._build_series(f'{metric_type}_system', data2)
            config['series'].append(series2)
        
        return config

    @staticmethod
    def _calculate_y_axis(data: List[float], metric_type: str) -> tuple:
        """计算自适应Y轴范围"""
        if not data:
            return 0, 100
        min_val, max_val = min(data), max(data)
        padding = (max_val - min_val) * 0.1
        if metric_type == 'fps':
            return 0, max_val + padding  # 完全自适应，支持200+ fps
        elif metric_type == 'cpu':
            return 0, 100
        else:
            return 0, max_val + padding

    @staticmethod
    def _get_title(metric_type: str) -> str:
        """获取图表标题"""
        titles = {'fps': 'FPS 趋势', 'cpu': 'CPU 使用率', 'memory': '内存使用', 'network_up': '网络上行', 'network_down': '网络下行'}
        return titles.get(metric_type, metric_type)

    @staticmethod
    def _build_series(metric_type: str, data: List[float]) -> Dict:
        """构建数据系列配置"""
        color = ChartDataBuilder.COLORS.get(metric_type, '#00d4ff')
        return {
            'name': ChartDataBuilder._get_series_name(metric_type),
            'type': 'line',
            'data': data,
            'smooth': True,
            'lineStyle': {'color': color, 'width': 2},
            'areaStyle': {'color': {'type': 'linear', 'x': 0, 'y': 0, 'x2': 0, 'y2': 1, 'colorStops': [{'offset': 0, 'color': f'{color}4D'}, {'offset': 1, 'color': f'{color}0D'}]}},
            'symbol': 'circle',
            'symbolSize': 4
        }

    @staticmethod
    def _get_series_name(metric_type: str) -> str:
        """获取系列名称"""
        names = {'fps': 'FPS', 'cpu': '应用CPU', 'cpu_system': '系统CPU', 'memory': '内存', 'network_up': '上行速率', 'network_down': '下行速率'}
        return names.get(metric_type, metric_type)
