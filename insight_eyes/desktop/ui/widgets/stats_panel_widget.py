# -*- coding: utf-8 -*-
"""
统计面板组件
显示会话的性能统计数据和告警记录
"""
from typing import Optional
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QScrollArea, QWidget
from logzero import logger


class StatsPanelWidget(QFrame):
    """右侧统计面板 - 显示性能统计数据和告警"""

    # 布局常量
    _MARGIN = 16
    _SPACING = 16
    _CARD_SPACING = 12
    _MAX_ALERTS = 20

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化UI"""
        self.setMinimumWidth(280)  # 设置最小宽度，防止被压缩
        self.setStyleSheet("""
            QFrame {
                background-color: #0a0e17;
                border: none;
                border-left: 1px solid #1a1f2e;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(self._MARGIN, 0, self._MARGIN, self._MARGIN)
        layout.setSpacing(self._SPACING)

        title = QLabel("性能统计")
        title.setStyleSheet("color: #00d4ff; font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setSpacing(self._CARD_SPACING)
        self.content_layout.addStretch()

        scroll.setWidget(self.content)
        layout.addWidget(scroll)

    def update_stats(self, statistics: dict) -> None:
        """更新统计数据"""
        try:
            logger.info(f"[StatsPanelWidget] update_stats 被调用，数据: {statistics}")
            logger.info(f"[StatsPanelWidget] 有 fps? {'fps' in statistics}, 有 cpu? {'cpu' in statistics}, 有 memory? {'memory' in statistics}")
            self._clear_content()
            self._add_stat_cards(statistics)
            logger.info(f"[StatsPanelWidget] 统计卡片已添加，content_layout.count() = {self.content_layout.count()}")
        except Exception as e:
            logger.error(f"更新统计数据失败: {e}", exc_info=True)

    def _clear_content(self) -> None:
        """清空现有内容（修复内存泄漏和清理逻辑）"""
        # 从末尾开始，移除所有 widget（除了最后的 stretch）
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(self.content_layout.count() - 2)  # 倒数第二个
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
            del item

    def _add_stat_cards(self, statistics: dict) -> None:
        """添加统计卡片（修复插入位置问题）"""
        logger.info(f"[StatsPanelWidget] _add_stat_cards 开始，statistics keys: {list(statistics.keys())}")
        if 'fps' in statistics:
            logger.info(f"[StatsPanelWidget] 添加 FPS 卡片，数据: {statistics['fps']}")
            self._add_stat_card('FPS', statistics['fps'], 'fps')
        if 'cpu' in statistics:
            logger.info(f"[StatsPanelWidget] 添加 CPU 卡片，数据: {statistics['cpu']}")
            self._add_stat_card('CPU', statistics['cpu'], '%')
        if 'memory' in statistics:
            logger.info(f"[StatsPanelWidget] 添加内存卡片，数据: {statistics['memory']}")
            self._add_stat_card('内存', statistics['memory'], 'MB')
        if 'network' in statistics:
            logger.info(f"[StatsPanelWidget] 添加网络卡片，数据: {statistics['network']}")
            self._add_network_card(statistics['network'])
        logger.info(f"[StatsPanelWidget] _add_stat_cards 完成，count = {self.content_layout.count()}")

    def _create_card_frame(self) -> QFrame:
        """创建统一样式的卡片框架"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #121824;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        return card

    def _add_stat_card(self, title: str, stats: dict, unit: str) -> None:
        """添加统计卡片"""
        card = self._create_card_frame()
        layout = QVBoxLayout(card)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #94a3b8; font-size: 10pt;")
        layout.addWidget(title_label)

        avg = stats.get('avg', 0)
        avg_label = QLabel(f"avg: {avg}{unit}")
        avg_label.setStyleSheet(f"color: #e0e6ed; font-size: 16pt; font-weight: bold;")
        layout.addWidget(avg_label)

        range_label = f"max: {stats.get('max', 0)}{unit}  min: {stats.get('min', 0)}{unit}"
        range_text = QLabel(range_label)
        range_text.setStyleSheet("color: #64748b; font-size: 9pt;")
        layout.addWidget(range_text)

        self.content_layout.insertWidget(self.content_layout.count() - 1, card)

    def _add_network_card(self, stats: dict) -> None:
        """添加网络统计卡片"""
        card = self._create_card_frame()
        layout = QVBoxLayout(card)
        layout.setSpacing(4)

        title_label = QLabel("网络")
        title_label.setStyleSheet("color: #94a3b8; font-size: 10pt;")
        layout.addWidget(title_label)

        up_stats = stats.get('up', {})
        up_label = f"  avg: {up_stats.get('avg', 0)}KB/s  max: {up_stats.get('max', 0)}KB/s"
        up_text = QLabel(up_label)
        up_text.setStyleSheet("color: #00ff87; font-size: 11pt;")
        layout.addWidget(up_text)

        down_stats = stats.get('down', {})
        down_label = f"  avg: {down_stats.get('avg', 0)}KB/s  max: {down_stats.get('max', 0)}KB/s"
        down_text = QLabel(down_label)
        down_text.setStyleSheet("color: #0062ff; font-size: 11pt;")
        layout.addWidget(down_text)

        self.content_layout.insertWidget(self.content_layout.count() - 1, card)

    def update_alerts(self, alerts: list) -> None:
        """更新告警记录"""
        try:
            self._remove_old_alerts()
            if not alerts:
                return
            self._add_alerts_widget(alerts[:self._MAX_ALERTS])
        except Exception as e:
            logger.error(f"更新告警记录失败: {e}", exc_info=True)

    def _remove_old_alerts(self) -> None:
        """移除旧的告警区域"""
        for i in range(self.content_layout.count()):
            widget = self.content_layout.itemAt(i).widget()
            if widget and widget.objectName() == 'alerts_widget':
                widget.setParent(None)
                widget.deleteLater()
                break

    def _add_alerts_widget(self, alerts: list) -> None:
        """添加告警区域"""
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

        title = QLabel(f"告警 ({len(alerts)})")
        title.setStyleSheet("color: #ef4444; font-size: 10pt; font-weight: bold;")
        layout.addWidget(title)

        for alert in alerts:
            alert_text = QLabel(f"  {alert.get('timestamp', '')}  {alert.get('message', '')}")
            alert_text.setStyleSheet("color: #e0e6ed; font-size: 9pt;")
            alert_text.setWordWrap(True)
            layout.addWidget(alert_text)

        self.content_layout.insertWidget(self.content_layout.count() - 1, alerts_widget)
