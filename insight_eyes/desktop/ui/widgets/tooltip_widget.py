"""
图表数据点悬停提示组件
"""
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QFont


class ChartTooltip(QLabel):
    """图表悬停提示框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(20, 20, 20, 230);
                border: 1px solid rgba(0, 212, 255, 0.5);
                border-radius: 8px;
                color: #ffffff;
                padding: 8px 12px;
                font-size: 12px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
        """)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    def show_tooltip(self, pos: QPoint, data: dict):
        """
        显示提示

        Args:
            pos: 屏幕位置
            data: 数据字典 {title, time, value, unit}
        """
        text = f"""<div style="line-height: 1.5;">
            <div style="color: #00d4ff; font-weight: bold; margin-bottom: 4px;">{data.get('title', '')}</div>
            <div>时间: {data.get('time', '')}</div>
            <div>数值: <span style="color: #00ff87; font-weight: bold;">{data.get('value', '')}{data.get('unit', '')}</span></div>
        </div>"""

        self.setText(text)
        self.adjustSize()
        self.move(pos + QPoint(15, 15))
        self.show()

    def hide_tooltip(self):
        """隐藏提示"""
        self.hide()
