# -*- coding: utf-8 -*-
"""
HTML 报告导出器
生成包含 ECharts 图表的交互式 HTML 报告
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from jinja2 import Template
from logzero import logger

from ..ui.charts.chart_data_builder import ChartDataBuilder
from .database import DatabaseManager
from .repository import MetricsRepository


class HtmlExporter:
    """HTML 报告导出器"""

    def __init__(self, database: DatabaseManager):
        self.database = database
        self.repository = MetricsRepository(database)
        # 将模板字符串转换为 Jinja2 Template 对象
        template_str = self._get_default_template()
        self._template = Template(template_str)

    def export(self, session_id: int, filepath: str) -> bool:
        """
        导出 HTML 报告

        Args:
            session_id: 会话ID
            filepath: 输出文件路径

        Returns:
            是否成功
        """
        try:
            # 获取数据
            session = self.database.get_session(session_id)
            if not session:
                logger.error(f"会话 {session_id} 不存在")
                return False

            device = self.database.get_device(session['device_id'])
            statistics = self.repository.get_statistics(session_id)
            alerts = self.database.get_alerts(session_id)  # 修复：使用 database 而不是 repository

            # 构建图表配置
            charts = self._build_charts(session_id)

            # 准备模板上下文
            context = {
                'title': f'性能测试报告 - {session["package_name"]}',
                'session': session,
                'device': device,
                'statistics': statistics,
                'alerts': alerts,
                'charts': charts,
                'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # 渲染 HTML
            html_content = self._template.render(**context)

            # 写入文件
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"HTML 报告已导出: {filepath}")
            return True

        except Exception as e:
            logger.error(f"导出 HTML 报告失败: {e}", exc_info=True)
            return False

    def _build_charts(self, session_id: int) -> Dict[str, Dict]:
        """构建所有图表配置"""
        charts = {}

        try:
            # 获取趋势数据
            fps_data = self.repository.get_fps_trend(session_id)
            if fps_data:
                timestamps = [t.strftime('%H:%M') for t, _ in fps_data]
                values = [v for _, v in fps_data]
                charts['fps'] = ChartDataBuilder.build_chart_config('fps', timestamps, values)

            cpu_data = self.repository.get_cpu_trend(session_id)
            if cpu_data:
                timestamps = [t.strftime('%H:%M') for t, _, _ in cpu_data]
                app_values = [a for _, a, _ in cpu_data]
                sys_values = [s for _, _, s in cpu_data]
                charts['cpu'] = ChartDataBuilder.build_chart_config('cpu', timestamps, app_values, sys_values)

            # 其他图表（内存、网络）
            # TODO: 在下一阶段添加

        except Exception as e:
            logger.error(f"构建图表配置失败: {e}")

        return charts

    @staticmethod
    def _get_default_template() -> str:
        """获取默认 HTML 模板"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <script src="insight_eyes/desktop/resources/export/echarts.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background-color: #0a0e17;
            color: #e0e6ed;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header {
            background: linear-gradient(135deg, #121824 0%, #1a1f2e 100%);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            border: 1px solid #1a1f2e;
        }
        .header h1 { color: #00d4ff; margin-bottom: 16px; }
        .session-info { color: #94a3b8; font-size: 14px; line-height: 1.6; }
        .chart-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }
        .chart-container {
            background-color: #121824;
            border-radius: 12px;
            padding: 16px;
            border: 1px solid #1a1f2e;
        }
        .chart { width: 100%; height: 300px; }
        .alerts-section {
            background-color: #121824;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #1a1f2e;
        }
        .alerts-section h2 { color: #ef4444; margin-bottom: 16px; }
        .alert-item {
            padding: 12px;
            margin-bottom: 8px;
            background-color: rgba(239, 68, 68, 0.1);
            border-radius: 6px;
            border-left: 3px solid #ef4444;
        }
        .footer {
            text-align: center;
            color: #64748b;
            font-size: 12px;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ title }}</h1>
            <div class="session-info">
                {% if device %}
                📱 设备: {{ device.name }}<br>
                {% endif %}
                📱 应用: {{ session.package_name }}<br>
                ⏰ 时间: {{ session.start_time.strftime("%Y-%m-%d %H:%M") }}
                - {{ session.end_time.strftime("%H:%M") if session.end_time else "进行中" }}<br>
                📊 采样间隔: {{ session.sample_interval }}ms
            </div>
        </div>

        <div class="chart-grid">
            {% for chart_id, chart_config in charts.items() %}
            <div class="chart-container">
                <div id="chart-{{ chart_id }}" class="chart"></div>
            </div>
            {% endfor %}
        </div>

        {% if alerts %}
        <div class="alerts-section">
            <h2>⚠️ 告警记录 ({{ alerts|length }})</h2>
            {% for alert in alerts %}
            <div class="alert-item">
                <strong>{{ alert.timestamp.strftime("%H:%M:%S") }}</strong>
                {{ alert.message }}
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <div class="footer">
            导出时间: {{ export_time }} | Insight Eye v1.0.0
        </div>
    </div>

    <script>
        // 初始化所有图表
        {% for chart_id, chart_config in charts.items() %}
        (function() {
            var chart = echarts.init(document.getElementById('chart-{{ chart_id }}'));
            var option = {{ chart_config | tojson }};
            chart.setOption(option);

            // 响应式
            window.addEventListener('resize', function() {
                chart.resize();
            });
        })();
        {% endfor %}
    </script>
</body>
</html>'''
