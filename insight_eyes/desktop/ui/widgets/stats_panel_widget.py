# -*- coding: utf-8 -*-
"""
统计面板组件
显示会话的性能统计数据和告警记录
"""
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QScrollArea, QWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from logzero import logger


class StatsPanelWidget(QFrame):
    """右侧统计面板 - 显示性能统计数据和告警"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """初始化UI"""
        # 基础样式
        self.setStyleSheet("""
            QFrame {
                background-color: #0a0e17;
                border: none;
                border-left: 1px solid #1a1f2e;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 16)
        layout.setSpacing(16)

        # 标题
        title = QLabel("📈 性能统计")
        title.setStyleSheet("color: #00d4ff; font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setSpacing(12)
        self.content_layout.addStretch()

        scroll.setWidget(self.content)
        layout.addWidget(scroll)

    def update_stats(self, statistics: dict):
        """更新统计数据"""
        # 清空现有内容
        for i in reversed(range(self.content_layout.count() - 1)):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # 添加统计卡片
        if 'fps' in statistics:
            self._add_stat_card('FPS', statistics['fps'], 'fps')
        if 'cpu' in statistics:
            self._add_stat_card('CPU', statistics['cpu'], '%')
        if 'memory' in statistics:
            self._add_stat_card('内存', statistics['memory'], 'MB')
        if 'network' in statistics:
            self._add_network_card(statistics['network'])

    def _add_stat_card(self, title: str, stats: dict, unit: str):
        """添加统计卡片"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #121824;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(4)

        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #94a3b8; font-size: 10pt;")
        layout.addWidget(title_label)

        # 平均值
        avg = stats.get('avg', 0)
        avg_label = QLabel(f"avg: {avg}{unit}")
        avg_label.setStyleSheet(f"color: #e0e6ed; font-size: 16pt; font-weight: bold;")
        layout.addWidget(avg_label)

        # 最大最小值
        range_label = f"max: {stats.get('max', 0)}{unit}  min: {stats.get('min', 0)}{unit}"
        range_text = QLabel(range_label)
        range_text.setStyleSheet("color: #64748b; font-size: 9pt;")
        layout.addWidget(range_text)

        self.content_layout.insertWidget(self.content_layout.count() - 1, card)

    def _add_network_card(self, stats: dict):
        """添加网络统计卡片"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #121824;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(4)

        title_label = QLabel("网络")
        title_label.setStyleSheet("color: #94a3b8; font-size: 10pt;")
        layout.addWidget(title_label)

        # 上行
        up_stats = stats.get('up', {})
        up_label = f"↑ avg: {up_stats.get('avg', 0)}KB/s  max: {up_stats.get('max', 0)}KB/s"
        up_text = QLabel(up_label)
        up_text.setStyleSheet("color: #00ff87; font-size: 11pt;")
        layout.addWidget(up_text)

        # 下行
        down_stats = stats.get('down', {})
        down_label = f"↓ avg: {down_stats.get('avg', 0)}KB/s  max: {down_stats.get('max', 0)}KB/s"
        down_text = QLabel(down_label)
        down_text.setStyleSheet("color: #0062ff; font-size: 11pt;")
        layout.addWidget(down_text)

        self.content_layout.insertWidget(self.content_layout.count() - 1, card)

    def update_alerts(self, alerts: list):
        """更新告警记录"""
        # 移除旧的告警区域
        for i in range(self.content_layout.count()):
            widget = self.content_layout.itemAt(i).widget()
            if widget and widget.objectName() == 'alerts_widget':
                widget.setParent(None)
                break

        if not alerts:
            return

        # 创建告警区域
        alerts_widget = QFrame()
        alerts_widget.setObjectName('alerts_widget')
        alerts_widget.setStyleSheet("""
            QFrame {
                background-color: #121824;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        layout = QVBoxLayout(alerts_widget)
        layout.setSpacing(8)

        # 标题
        title = QLabel(f"⚠️  告警 ({len(alerts)})")
        title.setStyleSheet("color: #ef4444; font-size: 10pt; font-weight: bold;")
        layout.addWidget(title)

        # 告警列表
        for alert in alerts[:20]:  # 最多显示20条
            alert_text = QLabel(f"• {alert.get('timestamp', '')}  {alert.get('message', '')}")
            alert_text.setStyleSheet("color: #e0e6ed; font-size: 9pt;")
            alert_text.setWordWrap(True)
            layout.addWidget(alert_text)

        self.content_layout.insertWidget(self.content_layout.count() - 1, alerts_widget)
