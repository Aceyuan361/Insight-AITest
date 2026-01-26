# -*- coding: utf-8 -*-
"""
会话报告详情组件 - 分屏布局版本
展示单个监控会话的完整报告

重构版本：分屏布局
- 左侧：图表区域（可滚动）
- 右侧：统计面板（固定）
- 顶部：紧凑会话信息栏
- 底部：操作按钮
"""
from typing import Optional, Dict, List
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea, QSplitter,
    QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
import pyqtgraph as pg
from logzero import logger

from insight_eyes.desktop.data.database import DatabaseManager
from insight_eyes.desktop.data.repository import MetricsRepository
from insight_eyes.desktop.ui.widgets.stats_panel_widget import StatsPanelWidget
import os
import json


class SessionReportWidget(QWidget):
    """会话报告详情组件 - 分屏布局版本

    功能：
    - 显示会话基本信息（紧凑格式）
    - 左侧显示性能趋势图表
    - 右侧显示性能统计汇总和告警
    - 支持导出和删除操作
    - 记住分隔线位置
    """

    # 信号
    export_requested = pyqtSignal(int)  # session_id
    delete_requested = pyqtSignal(int)  # session_id

    def __init__(self, session_id: int, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.database = DatabaseManager()
        self.repository = MetricsRepository(self.database)

        self._setup_ui()
        self._load_session_data()

    def _setup_ui(self):
        """初始化UI - 分屏布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 紧凑会话信息栏
        self._create_session_info_bar(layout)

        # 分隔器：左侧图表 + 右侧统计
        from PyQt6.QtWidgets import QSplitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        layout.addWidget(self.splitter)

        # 左侧：图表区域（不使用滚动组件）
        self.charts_container = QWidget()
        self.charts_layout = QGridLayout(self.charts_container)
        self.charts_layout.setSpacing(16)
        self.charts_layout.setContentsMargins(16, 16, 16, 16)
        self.splitter.addWidget(self.charts_container)

        # 右侧：统计面板
        self.stats_panel = StatsPanelWidget()
        self.splitter.addWidget(self.stats_panel)

        # 设置初始比例 (70:30)
        self.splitter.setSizes([700, 300])
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)

        # 底部按钮
        self._create_action_buttons(layout)

        # 恢复保存的分隔线位置
        self._restore_splitter_state()

        # 监听分隔线变化
        self.splitter.splitterMoved.connect(self._save_splitter_state)

    def _create_session_info_bar(self, parent_layout):
        """创建紧凑会话信息栏"""
        info_bar = QFrame()
        info_bar.setStyleSheet("""
            QFrame {
                background-color: #0a0e17;
                border-bottom: 1px solid #1a1f2e;
                padding: 12px 16px;
            }
        """)
        layout = QHBoxLayout(info_bar)
        layout.setSpacing(16)

        self.session_info_label = QLabel("加载中...")
        self.session_info_label.setStyleSheet("color: #94a3b8; font-size: 10pt;")
        layout.addWidget(self.session_info_label)
        layout.addStretch()

        parent_layout.addWidget(info_bar)

    def _create_action_buttons(self, parent_layout):
        """创建底部操作按钮"""
        button_bar = QFrame()
        button_bar.setStyleSheet("""
            QFrame {
                background-color: #0a0e17;
                border-top: 1px solid #1a1f2e;
                padding: 12px 16px;
            }
        """)
        layout = QHBoxLayout(button_bar)

        self.export_btn = QPushButton("导出 HTML 报告")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #121824;
                color: #00d4ff;
                border: 1px solid #00d4ff;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #00d4ff;
                color: #0a0e17;
            }
        """)
        self.export_btn.clicked.connect(self._export_html_report)
        layout.addWidget(self.export_btn)

        layout.addStretch()

        self.delete_btn = QPushButton("删除会话")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #121824;
                color: #ef4444;
                border: 1px solid #ef4444;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #0a0e17;
            }
        """)
        self.delete_btn.clicked.connect(self._delete_session)
        layout.addWidget(self.delete_btn)

        parent_layout.addWidget(button_bar)

    def _save_splitter_state(self):
        """保存分隔线位置"""
        try:
            settings = {
                'splitter_sizes': self.splitter.sizes()
            }
            # 使用用户配置目录
            config_dir = os.path.join(os.path.expanduser('~'), '.config', 'insight_eye')
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, 'report_layout.json')
            with open(config_path, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            logger.warning(f"保存分隔线位置失败: {e}")

    def _restore_splitter_state(self):
        """恢复分隔线位置"""
        try:
            # 使用用户配置目录
            config_dir = os.path.join(os.path.expanduser('~'), '.config', 'insight_eye')
            config_path = os.path.join(config_dir, 'report_layout.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    settings = json.load(f)
                    sizes = settings.get('splitter_sizes')
                    if sizes and len(sizes) == 2:
                        self.splitter.setSizes(sizes)
        except Exception as e:
            logger.warning(f"恢复分隔线位置失败: {e}")

    def _load_session_data(self):
        """加载会话数据"""
        try:
            # 获取会话信息
            session = self.database.get_session(self.session_id)
            if not session:
                QMessageBox.warning(self, "错误", "会话不存在")
                return

            # 更新会话信息栏（紧凑格式）
            device = self.database.get_device(session['device_id'])
            device_name = device['name'] if device else f"设备({session['device_id'][:8]})"  # 显示设备ID前8位

            # 解析时间字符串（数据库返回 ISO 格式字符串，需要转换为本地时间）
            from datetime import timezone

            start_dt = datetime.fromisoformat(session['start_time'])
            end_dt = datetime.fromisoformat(session['end_time']) if session['end_time'] else None

            # 转换为本地时间用于显示
            def to_local(dt):
                if dt is None:
                    return None
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(tz=None).replace(tzinfo=None)

            start_local = to_local(start_dt)
            end_local = to_local(end_dt) if end_dt else None

            start_time = start_local.strftime('%Y-%m-%d %H:%M')
            end_time = end_local.strftime('%H:%M') if end_local else None

            # 计算监控时长（基于实际指标数据的时间范围）
            metrics = self.database.get_metrics(self.session_id)
            if metrics and len(metrics) >= 2:
                first_ts = metrics[0].get('timestamp')
                last_ts = metrics[-1].get('timestamp')

                if first_ts and last_ts:
                    if isinstance(first_ts, str):
                        first_dt = datetime.fromisoformat(first_ts)
                    else:
                        first_dt = first_ts

                    if isinstance(last_ts, str):
                        last_dt = datetime.fromisoformat(last_ts)
                    else:
                        last_dt = last_ts

                    # 确保有时区信息
                    if first_dt.tzinfo is None:
                        first_dt = first_dt.replace(tzinfo=timezone.utc)
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)

                    duration_seconds = (last_dt - first_dt).total_seconds()
                    duration = self._format_duration_from_seconds(int(duration_seconds))
                else:
                    duration = self._calculate_duration(start_dt, end_dt)
            else:
                duration = self._calculate_duration(start_dt, end_dt)

            # 构建显示文本，如果未结束则不显示结束时间
            if end_time:
                info_text = f"设备: {device_name} | 应用: {session['package_name']} | 时间: {start_time}-{end_time} | 时长: {duration}"
            else:
                info_text = f"设备: {device_name} | 应用: {session['package_name']} | 时间: {start_time} | 时长: {duration}"

            self.session_info_label.setText(info_text)

            # 获取统计数据
            statistics = self.repository.get_statistics(self.session_id)

            # 转换统计数据格式为 StatsPanelWidget 期望的格式
            formatted_stats = {}

            if 'fps' in statistics:
                formatted_stats['fps'] = statistics['fps']

            if 'cpu_app' in statistics:
                formatted_stats['cpu'] = statistics['cpu_app']

            if 'memory_pss' in statistics:
                formatted_stats['memory'] = statistics['memory_pss']

            if 'network_up' in statistics or 'network_down' in statistics:
                formatted_stats['network'] = {
                    'up': statistics.get('network_up', {}),
                    'down': statistics.get('network_down', {})
                }

            self.stats_panel.update_stats(formatted_stats)

            # 获取告警
            alerts = self.database.get_alerts(session_id=self.session_id)
            self.stats_panel.update_alerts(alerts)

            # 加载图表（保留现有逻辑）
            self._load_charts()

        except Exception as e:
            logger.error(f"加载会话数据失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"加载会话数据失败: {e}")

    def _format_duration_from_seconds(self, total_seconds: int) -> str:
        """将秒数格式化为时长字符串"""
        # 小于60秒显示秒
        if total_seconds < 60:
            return f"{total_seconds}秒"
        # 小于60分钟显示分钟和秒
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        if minutes < 60:
            return f"{minutes}分{seconds}秒"
        # 大于60分钟显示小时、分钟和秒
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}小时{mins}分{seconds}秒"

    def _calculate_duration(self, start_time, end_time):
        """计算持续时间（精确到秒）"""
        from datetime import timezone

        if not end_time:
            # 使用 UTC 当前时间，而不是本地时间
            end_time = datetime.now(timezone.utc)

        # 确保两个时间都有时区信息
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        delta = end_time - start_time
        total_seconds = int(delta.total_seconds())

        # 小于60秒显示秒
        if total_seconds < 60:
            return f"{total_seconds}秒"

        # 小于60分钟显示分钟和秒
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        if minutes < 60:
            return f"{minutes}分{seconds}秒"

        # 大于60分钟显示小时、分钟和秒
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}小时{mins}分{seconds}秒"

    def _load_charts(self):
        """加载图表"""
        try:
            # 获取指标数据
            metrics_data = self.database.get_metrics(self.session_id)

            if not metrics_data:
                logger.warning(f"会话 {self.session_id} 没有指标数据")
                return

            # 分析哪些指标有数据
            available_metrics = set()
            for metric in metrics_data:
                if metric.get('fps') is not None:
                    available_metrics.add('fps')
                if metric.get('cpu_app') is not None:
                    available_metrics.add('cpu')
                if metric.get('memory_pss') is not None:
                    available_metrics.add('memory')
                if metric.get('network_up_speed') is not None:
                    available_metrics.add('network_up')
                if metric.get('network_down_speed') is not None:
                    available_metrics.add('network_down')

            if not available_metrics:
                logger.warning("没有可用的指标数据")
                return

            # 导入组件
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
            from insight_eyes.desktop.ui.panels.monitor_panel_v2 import NeonChartCard
            from insight_eyes.desktop.ui.utils.card_configs import get_card_config

            # 按优先级排序并创建图表
            priority_order = ['cpu', 'fps', 'memory', 'network_down', 'network_up', 'gpu']
            sorted_metrics = sorted(available_metrics, key=lambda x: priority_order.index(x) if x in priority_order else 999)

            # 保存图表卡片的字典
            self.chart_cards = {}

            # 限制最多显示6个图表（2×3布局）
            row, col = 0, 0
            for metric_id in sorted_metrics[:6]:  # 最多6个
                config = get_card_config(metric_id)
                if config:
                    card = NeonChartCard(
                        config.title,
                        config.color,
                        y_axis_config={
                            'min': config.y_min,
                            'max': config.y_max,
                            'width': config.y_width,
                            'decimals': config.decimals,
                            'unit': config.unit
                        }
                    )
                    card.setMinimumHeight(200)
                    self.charts_layout.addWidget(card, row, col)
                    self.chart_cards[metric_id] = card

                    # 计算下一个位置（固定2列）
                    col += 1
                    if col >= 2:
                        col = 0
                        row += 1

            # 设置stretch
            for i in range(2):
                self.charts_layout.setColumnStretch(i, 1)
            for i in range(row + 1):
                self.charts_layout.setRowStretch(i, 1)

            # 更新图表数据
            self._update_charts(metrics_data)

            logger.info(f"创建了 {len(self.chart_cards)} 个图表: {list(self.chart_cards.keys())}")

        except Exception as e:
            logger.error(f"加载图表失败: {e}", exc_info=True)

    def _update_charts(self, metrics_data):
        """更新图表数据"""
        if not metrics_data or not hasattr(self, 'chart_cards'):
            return

        try:
            # 清空所有图表的数据
            for card in self.chart_cards.values():
                card.clear_data()

            # 遍历所有指标数据点
            for metric in metrics_data:
                # 提取时间戳（数据库存储的是UTC时间，需要转换为本地时间）
                timestamp_str = metric.get('timestamp')
                if timestamp_str:
                    try:
                        if isinstance(timestamp_str, str):
                            utc_timestamp = datetime.fromisoformat(timestamp_str)
                            from datetime import timezone
                            utc_timestamp = utc_timestamp.replace(tzinfo=timezone.utc)
                            timestamp = utc_timestamp.astimezone().replace(tzinfo=None)
                        else:
                            from datetime import timezone
                            timestamp = datetime.fromtimestamp(timestamp_str, tz=timezone.utc).astimezone().replace(tzinfo=None)
                    except (ValueError, TypeError, OSError) as e:
                        logger.debug(f"时间戳解析失败，使用当前时间: {e}")
                        timestamp = datetime.now()
                else:
                    timestamp = datetime.now()

                # 提取指标数据
                fps_val = metric['fps'] or 0
                cpu_val = metric['cpu_app'] or 0
                mem_val = metric['memory_pss'] or 0
                up_val = metric['network_up_speed'] or 0
                down_val = metric['network_down_speed'] or 0
                gpu_val = metric.get('gpu_usage') or 0

                # 根据实际存在的图表卡片添加数据（传递时间戳）
                if 'fps' in self.chart_cards:
                    self.chart_cards['fps'].add_data_point(fps_val, timestamp)
                if 'cpu' in self.chart_cards:
                    self.chart_cards['cpu'].add_data_point(cpu_val, timestamp)
                if 'memory' in self.chart_cards:
                    self.chart_cards['memory'].add_data_point(mem_val, timestamp)
                if 'network_up' in self.chart_cards:
                    self.chart_cards['network_up'].add_data_point(up_val, timestamp)
                if 'network_down' in self.chart_cards:
                    self.chart_cards['network_down'].add_data_point(down_val, timestamp)
                if 'gpu' in self.chart_cards:
                    self.chart_cards['gpu'].add_data_point(gpu_val, timestamp)

            logger.info(f"图表数据更新完成，共 {len(metrics_data)} 个数据点")

        except Exception as e:
            logger.error(f"更新图表失败: {e}", exc_info=True)

    def _export_html_report(self):
        """导出 HTML 报告"""
        try:
            from PyQt6.QtWidgets import QFileDialog, QApplication
            from insight_eyes.desktop.data.html_exporter import HtmlExporter
            import webbrowser
            import os

            # 选择保存路径
            default_filename = f"session_{self.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "导出 HTML 报告",
                default_filename,
                "HTML 文件 (*.html)"
            )

            if not filepath:
                return

            # 显示进度
            self.export_btn.setEnabled(False)
            self.export_btn.setText("导出中...")
            QApplication.processEvents()

            # 导出
            exporter = HtmlExporter(self.database)
            success = exporter.export(self.session_id, filepath)

            if success:
                # 询问是否打开
                reply = QMessageBox.question(
                    self,
                    "打开报告",
                    f"HTML 报告已导出到:\n{filepath}\n\n是否立即打开？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    # 转换路径格式为浏览器可接受的格式
                    browser_path = filepath.replace(os.sep, '/')
                    if not browser_path.startswith('/'):
                        browser_path = f"file:///{browser_path}"
                    webbrowser.open(browser_path)
            else:
                QMessageBox.critical(self, "导出失败", "导出 HTML 报告时发生错误")

        except Exception as e:
            logger.error(f"导出 HTML 报告失败: {e}", exc_info=True)
            QMessageBox.critical(self, "导出失败", f"导出时发生错误:\n{e}")
        finally:
            self.export_btn.setEnabled(True)
            self.export_btn.setText("导出 HTML 报告")

    def _delete_session(self):
        """删除会话"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除会话 {self.session_id} 吗？\n此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 发射信号，让 SessionManager 处理删除
            self.delete_requested.emit(self.session_id)

    def load_session(self, session_id: int):
        """加载会话数据（兼容旧接口）

        Args:
            session_id: 会话ID
        """
        self.session_id = session_id
        self._load_session_data()

    def clear(self):
        """清空显示"""
        self.session_id = None
        self.session_info_label.setText("")

        # 清空图表
        if hasattr(self, 'chart_cards'):
            for card in self.chart_cards.values():
                card.setParent(None)
                card.deleteLater()
            self.chart_cards.clear()

        # 清空统计面板
        self.stats_panel.update_stats({})
        self.stats_panel.update_alerts([])
