"""
仪表盘组件
用于显示单个性能指标的圆形仪表盘
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QRadialGradient
import math


class MetricGauge(QWidget):
    """
    单个指标仪表盘
    显示圆形进度条和数值
    """

    # 状态变化信号
    status_changed = pyqtSignal(str)  # normal, warning, critical

    def __init__(self, title: str, unit: str,
                 normal_range: tuple, warning_range: tuple,
                 max_value: float = 100.0,
                 parent=None):
        """
        初始化仪表盘

        Args:
            title: 指标标题
            unit: 单位
            normal_range: 正常范围 (min, max)
            warning_range: 警告范围 (min, max)
            max_value: 最大值（用于进度条）
            parent: 父窗口
        """
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.normal_range = normal_range
        self.warning_range = warning_range
        self.max_value = max_value
        self.current_value = 0.0
        self.target_value = 0.0
        self.current_status = "normal"

        # 动画相关
        self.animation_step = 0
        self.animation_steps = 20  # 动画帧数
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)

        self._init_ui()
        self.setFixedSize(200, 180)

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 标题标签
        self.title_label = QLabel(self.title)
        self.title_label.setProperty("class", "metric-label")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # 仪表盘绘制区域（通过paintEvent绘制）
        layout.addStretch()

        # 数值标签
        self.value_label = QLabel("0")
        self.value_label.setProperty("class", "metric-value")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)

        # 单位标签
        self.unit_label = QLabel(self.unit)
        self.unit_label.setProperty("class", "metric-label")
        self.unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.unit_label)

    def set_value(self, value: float, animate: bool = True):
        """
        设置数值

        Args:
            value: 新数值
            animate: 是否启用动画
        """
        self.target_value = max(0, min(value, self.max_value))

        if animate and self.animation_step == 0:
            self.animation_step = 0
            self.animation_timer.start(20)  # 20ms更新一次，共400ms
        else:
            self.current_value = self.target_value
            self._update_display()

    def _update_animation(self):
        """更新动画帧"""
        if self.animation_step < self.animation_steps:
            # 使用缓动函数
            progress = self.animation_step / self.animation_steps
            eased = 1 - (1 - progress) ** 3  # ease-out cubic

            self.current_value = self.current_value + (self.target_value - self.current_value) * eased
            self.animation_step += 1
            self._update_display()
        else:
            self.current_value = self.target_value
            self._update_display()
            self.animation_timer.stop()
            self.animation_step = 0

    def _update_display(self):
        """更新显示"""
        # 更新数值标签
        self.value_label.setText(f"{self.current_value:.1f}")

        # 确定状态
        if self.normal_range[0] <= self.current_value <= self.normal_range[1]:
            new_status = "normal"
            color = QColor("#22c55e")  # 绿色
        elif self.warning_range[0] <= self.current_value <= self.warning_range[1]:
            new_status = "warning"
            color = QColor("#f59e0b")  # 黄色
        else:
            new_status = "critical"
            color = QColor("#ef4444")  # 红色

        # 更新数值颜色
        self.value_label.setStyleSheet(f"color: {color.name()};")

        # 状态变化时发出信号
        if new_status != self.current_status:
            self.current_status = new_status
            self.status_changed.emit(new_status)

        # 重绘仪表盘
        self.update()

    def paintEvent(self, event):
        """绘制仪表盘"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 获取绘制区域
        rect = self.rect()
        center_x = rect.width() // 2
        center_y = rect.height() // 2 - 10
        radius = min(rect.width(), rect.height()) // 2 - 20

        # 根据状态确定颜色
        if self.current_status == "normal":
            gauge_color = QColor("#22c55e")
        elif self.current_status == "warning":
            gauge_color = QColor("#f59e0b")
        else:
            gauge_color = QColor("#ef4444")

        # 绘制背景圆环
        painter.setPen(QPen(QColor("#1a1f2e"), 12))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(int(center_x - radius), int(center_y - radius),
                       int(radius * 2), int(radius * 2), 0, 360 * 16)

        # 绘制进度圆环
        if self.max_value > 0:
            progress = self.current_value / self.max_value
            start_angle = 90 * 16  # 从顶部开始
            span_angle = int(-progress * 360 * 16)

            pen = QPen(gauge_color, 12)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(int(center_x - radius), int(center_y - radius),
                           int(radius * 2), int(radius * 2), start_angle, span_angle)

        # 绘制内圈装饰（霓虹效果）
        painter.setPen(QPen(QColor(gauge_color.red(), gauge_color.green(), gauge_color.blue(), 50), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(int(center_x - radius + 8), int(center_y - radius + 8),
                           int(radius * 2 - 16), int(radius * 2 - 16))


class MetricCard(QFrame):
    """
    指标卡片
    包含标题、数值、单位，并带有状态指示
    """

    def __init__(self, title: str, unit: str,
                 normal_range: tuple, warning_range: tuple,
                 max_value: float = 100.0,
                 icon: str = "",
                 parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.normal_range = normal_range
        self.warning_range = warning_range
        self.max_value = max_value
        self.current_value = 0.0
        self.icon = icon

        self._init_ui()
        self.setProperty("class", "metric-card")
        self.set_level("normal")

    def _init_ui(self):
        """初始化UI"""
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setFixedSize(140, 90)  # 调整为更紧凑的尺寸

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)

        # 标题
        self.title_label = QLabel(self.title)
        self.title_label.setProperty("class", "metric-label")
        self.title_label.setStyleSheet("font-size: 10pt; color: #94a3b8;")
        layout.addWidget(self.title_label)

        # 数值
        self.value_label = QLabel("--")
        self.value_label.setProperty("class", "metric-value")
        self.value_label.setStyleSheet("font-size: 20pt; font-weight: 600;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.value_label)

        # 单位
        self.unit_label = QLabel(self.unit)
        self.unit_label.setProperty("class", "metric-label")
        self.unit_label.setStyleSheet("font-size: 8pt; color: #64748b;")
        layout.addWidget(self.unit_label)

        layout.addStretch()

    def set_value(self, value: float):
        """设置数值"""
        self.current_value = value
        self.value_label.setText(f"{value:.1f}")

        # 确定状态并更新样式
        if self.normal_range[0] <= value <= self.normal_range[1]:
            self.set_level("normal")
            color = "#22c55e"
        elif self.warning_range[0] <= value <= self.warning_range[1]:
            self.set_level("warning")
            color = "#f59e0b"
        else:
            self.set_level("critical")
            color = "#ef4444"

        self.value_label.setStyleSheet(f"font-size: 24pt; color: {color};")

    def set_level(self, level: str):
        """设置卡片状态级别"""
        self.setProperty("level", level)
        self.style().unpolish(self)
        self.style().polish(self)


class MetricsDashboard(QWidget):
    """
    核心指标仪表盘
    横向排列多个指标卡片
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.metrics = {}
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 标题已移至父容器 (monitor_panel.py)，避免重复

        # 指标卡片容器 - 横向布局
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        # 创建四个指标卡片 - 横向排列
        # FPS
        self.fps_card = MetricCard(
            title="FPS",
            unit="帧/秒",
            normal_range=(50, 65),
            warning_range=(30, 50),
            max_value=65
        )
        cards_layout.addWidget(self.fps_card)
        self.metrics["fps"] = self.fps_card

        # CPU
        self.cpu_card = MetricCard(
            title="CPU",
            unit="%",
            normal_range=(0, 60),
            warning_range=(60, 80),
            max_value=100
        )
        cards_layout.addWidget(self.cpu_card)
        self.metrics["cpu"] = self.cpu_card

        # 内存
        self.memory_card = MetricCard(
            title="内存",
            unit="MB",
            normal_range=(0, 300),
            warning_range=(300, 500),
            max_value=1000
        )
        cards_layout.addWidget(self.memory_card)
        self.metrics["memory"] = self.memory_card

        # 网络
        self.network_card = MetricCard(
            title="网络",
            unit="KB/s",
            normal_range=(0, 100),
            warning_range=(100, 500),
            max_value=1000
        )
        cards_layout.addWidget(self.network_card)
        self.metrics["network"] = self.network_card

        cards_layout.addStretch()
        layout.addLayout(cards_layout)

    def update_metrics(self, metrics_data: dict):
        """
        更新所有指标

        Args:
            metrics_data: 包含各项指标的字典
        """
        # 更新FPS
        if "fps" in metrics_data:
            fps = metrics_data["fps"]
            if isinstance(fps, dict):
                self.fps_card.set_value(fps.get("fps", 0))
            else:
                self.fps_card.set_value(fps)

        # 更新CPU
        if "cpu" in metrics_data:
            cpu = metrics_data["cpu"]
            if isinstance(cpu, dict):
                self.cpu_card.set_value(cpu.get("app_cpu_rate", 0))
            else:
                self.cpu_card.set_value(cpu)

        # 更新内存
        if "memory" in metrics_data:
            memory = metrics_data["memory"]
            if isinstance(memory, dict):
                self.memory_card.set_value(memory.get("total_mb", 0))
            else:
                self.memory_card.set_value(memory)

        # 更新网络
        if "network" in metrics_data:
            network = metrics_data["network"]
            if isinstance(network, dict):
                total_rate = network.get("upload_rate_kbs", 0) + network.get("download_rate_kbs", 0)
                self.network_card.set_value(total_rate)
            else:
                self.network_card.set_value(network)

    def reset(self):
        """重置所有指标"""
        for card in self.metrics.values():
            card.set_value(0)
            card.set_level("normal")
