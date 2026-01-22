# -*- coding: utf-8 -*-
"""
会话报告详情组件
展示单个监控会话的完整报告

重构版本：修复布局问题
- 添加滚动区域
- 图表自适应布局
- 修复字体和间距问题
"""
from typing import Optional, Dict, List
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QTabWidget, QScrollArea,
    QPushButton, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
import pyqtgraph as pg
from logzero import logger

from insight_eyes.desktop.data.database import DatabaseManager
from insight_eyes.desktop.ui.charts.trend_chart import TrendChartWidget


class SessionReportWidget(QWidget):
    """会话报告详情组件

    功能：
    - 显示会话基本信息
    - 显示性能指标汇总
    - 显示趋势图表（FPS、CPU、内存、网络）
    - 支持导出和删除操作
    """

    # 信号
    export_requested = pyqtSignal(int)  # session_id
    delete_requested = pyqtSignal(int)  # session_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.session_id: Optional[int] = None
        self.session_data: Optional[Dict] = None
        self.metrics_data: List[Dict] = []

        self._init_ui()

    def _init_ui(self):
        """初始化UI - 重构布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 1. 顶部操作栏（导出、删除按钮）
        header_bar = self._create_header_bar()
        main_layout.addWidget(header_bar)

        # 2. 滚动区域（包含所有内容）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #1a1f2e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #3b4252;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4c566a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(20)

        # 3. 会话信息卡片
        info_card = self._create_info_card()
        scroll_layout.addWidget(info_card)

        # 4. 性能统计表格卡片（可折叠）
        stats_card = self._create_stats_card()
        scroll_layout.addWidget(stats_card)

        # 5. 图表区域（使用 QGridLayout 自适应）
        charts_widget = self._create_charts_widget()
        scroll_layout.addWidget(charts_widget)

        scroll_layout.addStretch()  # 弹性空间

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)  # 占据剩余空间

    def _create_header_bar(self) -> QFrame:
        """创建顶部操作栏"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addStretch()

        # 导出按钮
        self.export_btn = QPushButton("📤 导出报告")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d4ff;
                color: #0a0e17;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #00b8e6;
            }
            QPushButton:pressed {
                background-color: #0099cc;
            }
            QPushButton:disabled {
                background-color: #3b4252;
                color: #6c7086;
            }
        """)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._on_export_clicked)
        layout.addWidget(self.export_btn)

        # 删除按钮
        self.delete_btn = QPushButton("🗑️ 删除会话")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:pressed {
                background-color: #b91c1c;
            }
            QPushButton:disabled {
                background-color: #3b4252;
                color: #6c7086;
            }
        """)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self.delete_btn)

        return header

    def _create_info_card(self) -> QFrame:
        """创建会话信息卡片"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #141414;
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.05);
                padding: 20px;
            }
            QLabel {
                color: #e0e6ed;
                background-color: transparent;
            }
        """)

        layout = QGridLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        title_label = QLabel("📊 会话信息")
        title_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #00d4ff;")
        layout.addWidget(title_label, 0, 0, 1, 4)

        # 设备信息
        layout.addWidget(QLabel("设备:"), 1, 0)
        self.device_label = QLabel("-")
        self.device_label.setStyleSheet("color: #ffffff; font-weight: 500;")
        layout.addWidget(self.device_label, 1, 1)

        # 应用信息
        layout.addWidget(QLabel("应用:"), 1, 2)
        self.app_label = QLabel("-")
        self.app_label.setStyleSheet("color: #ffffff; font-weight: 500;")
        layout.addWidget(self.app_label, 1, 3)

        # 开始时间
        layout.addWidget(QLabel("开始时间:"), 2, 0)
        self.start_time_label = QLabel("-")
        self.start_time_label.setStyleSheet("color: #e0e6ed;")
        layout.addWidget(self.start_time_label, 2, 1)

        # 结束时间
        layout.addWidget(QLabel("结束时间:"), 2, 2)
        self.end_time_label = QLabel("-")
        self.end_time_label.setStyleSheet("color: #e0e6ed;")
        layout.addWidget(self.end_time_label, 2, 3)

        # 持续时间
        layout.addWidget(QLabel("持续时间:"), 3, 0)
        self.duration_label = QLabel("-")
        self.duration_label.setStyleSheet("color: #e0e6ed;")
        layout.addWidget(self.duration_label, 3, 1)

        # 采样间隔
        layout.addWidget(QLabel("采样间隔:"), 3, 2)
        self.interval_label = QLabel("-")
        self.interval_label.setStyleSheet("color: #e0e6ed;")
        layout.addWidget(self.interval_label, 3, 3)

        return card

    def _create_stats_card(self) -> QFrame:
        """创建性能统计卡片（修复字体和间距问题）"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #141414;
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.05);
                padding: 20px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        title_label = QLabel("📈 性能指标详情")
        title_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #00d4ff;")
        layout.addWidget(title_label)

        # 统计表格（使用 QTableWidget 确保文字完整显示）
        self.stats_table = QTableWidget()
        self.stats_table.setMinimumHeight(350)  # 设置最小高度，确保滚动时有足够空间
        self.stats_table.setColumnCount(4)
        self.stats_table.setHorizontalHeaderLabels(["指标", "最大值", "最小值", "平均值"])
        self.stats_table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                border: none;
                gridline-color: rgba(255,255,255,0.08);
            }
            QTableWidget::item {
                padding: 10px;
                color: #e0e6ed;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #1a1a1a;
                color: #00d4ff;
                padding: 12px;
                border: none;
                border-bottom: 2px solid rgba(0,212,255,0.3);
                font-weight: 600;
                font-size: 13px;
            }
        """)

        # 调整列宽
        header = self.stats_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.stats_table.setColumnWidth(0, 150)
        self.stats_table.setColumnWidth(1, 120)
        self.stats_table.setColumnWidth(2, 120)

        # 设置行高（确保文字不被切割）
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.verticalHeader().setDefaultSectionSize(45)

        # 禁止编辑
        self.stats_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.stats_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.stats_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout.addWidget(self.stats_table)

        return card

    def _create_charts_widget(self) -> QWidget:
        """创建图表区域（动态创建，根据实际采集的指标显示）"""
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")

        # 使用垂直布局，稍后动态添加图表
        self.charts_layout = QVBoxLayout(widget)
        self.charts_layout.setSpacing(15)

        # 保存图表卡片的字典
        self.chart_cards = {}

        return widget

    def _create_charts_from_metrics(self, metrics_data: list):
        """
        根据实际采集的指标动态创建图表

        Args:
            metrics_data: 指标数据列表
        """
        try:
            # 清除现有图表
            self._clear_charts()

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

            # 限制最多显示6个图表（2×3布局）
            chart_widgets = []
            grid_widget = QWidget()
            grid_layout = QGridLayout(grid_widget)
            grid_layout.setSpacing(15)

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
                    grid_layout.addWidget(card, row, col)
                    self.chart_cards[metric_id] = card
                    chart_widgets.append(card)

                    # 计算下一个位置（固定2列）
                    col += 1
                    if col >= 2:
                        col = 0
                        row += 1

            # 设置stretch
            for i in range(2):
                grid_layout.setColumnStretch(i, 1)
            for i in range(row + 1):
                grid_layout.setRowStretch(i, 1)

            # 添加到布局
            self.charts_layout.addWidget(grid_widget)

            logger.info(f"创建了 {len(chart_widgets)} 个图表: {list(self.chart_cards.keys())}")

        except Exception as e:
            logger.error(f"动态创建图表失败: {e}", exc_info=True)

    def _clear_charts(self):
        """清除所有图表"""
        try:
            # 清除旧的图表卡片
            for card in self.chart_cards.values():
                card.setParent(None)
                card.deleteLater()
            self.chart_cards.clear()

            # 清除布局中的所有控件
            while self.charts_layout.count():
                item = self.charts_layout.takeAt(0)
                if item:
                    item.setParent(None)
                    item.deleteLater()

        except Exception as e:
            logger.warning(f"清除图表失败: {e}")

    def _create_chart_container(self, title: str, color: str) -> QFrame:
        """创建图表容器"""
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: #141414;
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.05);
                border-top: 2px solid {color};
            }}
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {color};")
        layout.addWidget(title_label)

        # 图表
        chart = TrendChartWidget(
            title=title,
            y_label=title,
            unit=""
        )
        chart.setMinimumHeight(250)
        chart.setStyleSheet("background-color: transparent; border: none;")
        layout.addWidget(chart, 1)

        # 保存图表引用（用于后续更新）
        setattr(self, f"{title.lower().replace(' ', '_')}_chart_widget", chart)

        return container

    def load_session(self, session_id: int):
        """加载会话数据

        Args:
            session_id: 会话ID
        """
        try:
            self.session_id = session_id

            # 加载会话信息
            self.session_data = self.db.get_session(session_id)
            if not self.session_data:
                logger.warning(f"会话 {session_id} 不存在")
                return

            # 加载指标数据
            self.metrics_data = self.db.get_metrics(session_id)

            logger.info(f"加载会话 {session_id} 的数据: {len(self.metrics_data)} 条指标")

            # 更新UI
            self._update_info()
            self._update_stats_table()
            # 先动态创建图表，再更新数据
            self._create_charts_from_metrics(self.metrics_data)
            self._update_charts()

            # 启用按钮
            self.export_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)

        except Exception as e:
            logger.error(f"加载会话数据失败: {e}")
            import traceback
            traceback.print_exc()

    def _update_info(self):
        """更新会话信息"""
        if not self.session_data:
            return

        # 设备信息
        device = self.db.get_device(self.session_data['device_id'])
        if device:
            self.device_label.setText(f"{device['name']} ({device['platform']})")
        else:
            self.device_label.setText(self.session_data['device_id'])

        # 应用信息
        self.app_label.setText(self.session_data['package_name'])

        # 时间信息（数据库存储UTC时间，需要转换为本地时间）
        from datetime import timezone
        start_time_utc = datetime.fromisoformat(self.session_data['start_time'])
        start_time_utc = start_time_utc.replace(tzinfo=timezone.utc)
        start_time = start_time_utc.astimezone().replace(tzinfo=None)
        self.start_time_label.setText(start_time.strftime("%Y-%m-%d %H:%M:%S"))

        if self.session_data['end_time']:
            end_time_utc = datetime.fromisoformat(self.session_data['end_time'])
            end_time_utc = end_time_utc.replace(tzinfo=timezone.utc)
            end_time = end_time_utc.astimezone().replace(tzinfo=None)
            self.end_time_label.setText(end_time.strftime("%Y-%m-%d %H:%M:%S"))

            # 计算持续时间
            duration = (end_time - start_time).total_seconds()
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)
            if hours > 0:
                self.duration_label.setText(f"{hours}小时{minutes}分{seconds}秒")
            else:
                self.duration_label.setText(f"{minutes}分{seconds}秒")
        else:
            self.end_time_label.setText("进行中")
            self.duration_label.setText("-")

        # 采样间隔
        interval = self.session_data.get('sample_interval', 1000)
        self.interval_label.setText(f"{interval}ms")

    def _update_stats_table(self):
        """更新性能指标统计表格"""
        if not self.metrics_data:
            return

        # 准备数据
        stats_data = []

        # FPS统计
        fps_values = [m['fps'] for m in self.metrics_data if m['fps'] is not None]
        if fps_values:
            stats_data.append({
                '指标': 'FPS',
                '最大值': f"{max(fps_values):.1f}",
                '最小值': f"{min(fps_values):.1f}",
                '平均值': f"{sum(fps_values)/len(fps_values):.1f}",
                'color': '#ffb400'
            })

        # 卡顿统计
        jank_counts = [m['fps_jank_count'] for m in self.metrics_data if m['fps_jank_count'] is not None]
        if jank_counts:
            total_janks = sum(jank_counts)
            stats_data.append({
                '指标': '卡顿次数',
                '最大值': f"{max(jank_counts)}",
                '最小值': f"{min(jank_counts)}",
                '平均值': f"{total_janks}",
                'color': '#ef4444'
            })

        # CPU统计
        cpu_values = [m['cpu_app'] for m in self.metrics_data if m['cpu_app'] is not None]
        if cpu_values:
            stats_data.append({
                '指标': 'CPU使用率',
                '最大值': f"{max(cpu_values):.1f}%",
                '最小值': f"{min(cpu_values):.1f}%",
                '平均值': f"{sum(cpu_values)/len(cpu_values):.1f}%",
                'color': '#00f2ff'
            })

        # 内存统计
        memory_values = [m['memory_pss'] for m in self.metrics_data if m['memory_pss'] is not None]
        if memory_values:
            stats_data.append({
                '指标': '内存使用',
                '最大值': f"{max(memory_values):.0f} MB",
                '最小值': f"{min(memory_values):.0f} MB",
                '平均值': f"{sum(memory_values)/len(memory_values):.0f} MB",
                'color': '#7000ff'
            })

        # 网络统计
        up_speeds = [m['network_up_speed'] for m in self.metrics_data if m['network_up_speed'] is not None]
        down_speeds = [m['network_down_speed'] for m in self.metrics_data if m['network_down_speed'] is not None]

        if up_speeds:
            stats_data.append({
                '指标': '上行速率',
                '最大值': f"{max(up_speeds):.1f} KB/s",
                '最小值': f"{min(up_speeds):.1f} KB/s",
                '平均值': f"{sum(up_speeds)/len(up_speeds):.1f} KB/s",
                'color': '#00ff87'
            })

        if down_speeds:
            stats_data.append({
                '指标': '下行速率',
                '最大值': f"{max(down_speeds):.1f} KB/s",
                '最小值': f"{min(down_speeds):.1f} KB/s",
                '平均值': f"{sum(down_speeds)/len(down_speeds):.1f} KB/s",
                'color': '#0062ff'
            })

        # 填充表格
        self.stats_table.setRowCount(len(stats_data))
        for row, data in enumerate(stats_data):
            # 指标名称
            item = QTableWidgetItem(data['指标'])
            item.setForeground(QColor(data['color']))
            self.stats_table.setItem(row, 0, item)

            # 最大值
            self.stats_table.setItem(row, 1, QTableWidgetItem(data['最大值']))

            # 最小值
            self.stats_table.setItem(row, 2, QTableWidgetItem(data['最小值']))

            # 平均值
            self.stats_table.setItem(row, 3, QTableWidgetItem(data['平均值']))

    def _update_charts(self):
        """更新图表数据（使用动态chart_cards字典）"""
        if not self.metrics_data or not self.chart_cards:
            return

        try:
            # 清空所有图表的数据
            for card in self.chart_cards.values():
                card.clear_data()

            # 遍历所有指标数据点
            for metric in self.metrics_data:
                # 提取时间戳（数据库存储的是UTC时间，需要转换为本地时间）
                timestamp_str = metric.get('timestamp')
                if timestamp_str:
                    try:
                        if isinstance(timestamp_str, str):
                            # SQLite 的 CURRENT_TIMESTAMP 返回 UTC 时间，格式为 "YYYY-MM-DD HH:MM:SS"
                            # 需要将其解析为 UTC 时间，然后转换为本地时间
                            utc_timestamp = datetime.fromisoformat(timestamp_str)
                            # 标记为 UTC 时间
                            from datetime import timezone
                            utc_timestamp = utc_timestamp.replace(tzinfo=timezone.utc)
                            # 转换为本地时间（东八区）
                            timestamp = utc_timestamp.astimezone().replace(tzinfo=None)
                        else:
                            # 假设是 Unix 时间戳（已经是 UTC）
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

            logger.info(f"图表数据更新完成，共 {len(self.metrics_data)} 个数据点")

        except Exception as e:
            logger.error(f"更新图表失败: {e}")
            import traceback
            traceback.print_exc()

    def _on_export_clicked(self):
        """导出按钮点击"""
        if self.session_id:
            self.export_requested.emit(self.session_id)

    def _on_delete_clicked(self):
        """删除按钮点击"""
        if self.session_id:
            self.delete_requested.emit(self.session_id)

    def clear(self):
        """清空显示"""
        self.session_id = None
        self.session_data = None
        self.metrics_data = []

        # 清空标签
        self.device_label.setText("-")
        self.app_label.setText("-")
        self.start_time_label.setText("-")
        self.end_time_label.setText("-")
        self.duration_label.setText("-")
        self.interval_label.setText("-")

        # 清空表格
        self.stats_table.setRowCount(0)

        # 清空动态图表
        self._clear_charts()

        # 禁用按钮
        self.export_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
