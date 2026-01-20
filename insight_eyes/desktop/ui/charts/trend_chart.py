"""
趋势图表组件
基于pyqtgraph的性能趋势折线图
"""
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPen
import numpy as np


class TrendChartWidget(pg.PlotWidget):
    """
    趋势图表基础类
    使用pyqtgraph绘制高性能折线图
    """

    def __init__(self, title: str, y_label: str,
                 unit: str = "",
                 threshold: Optional[float] = None,
                 max_points: int = 1000,
                 parent=None):
        """
        初始化图表

        Args:
            title: 图表标题
            y_label: Y轴标签
            unit: 单位
            threshold: 阈值线
            max_points: 最大数据点数
            parent: 父窗口
        """
        super().__init__(parent)

        self.title = title
        self.y_label = y_label
        self.unit = unit
        self.threshold = threshold
        self.max_points = max_points

        # 数据存储
        self.time_data = []  # 时间戳列表
        self.value_data = []  # 数值列表
        self.alert_points = []  # 告警点列表

        # 初始化图表设置
        self._setup_chart()

        # 创建曲线和标记
        self._create_curves()

    def _setup_chart(self):
        """设置图表基本属性"""
        # 设置标题和标签
        self.setTitle(self.title, color='w', size='12pt')
        self.setLabel('left', self.y_label, color='#94a3b8')
        self.setLabel('bottom', '时间', color='#94a3b8')

        # 显示网格
        self.showGrid(x=True, y=True, alpha=0.3)

        # 设置背景（透明，使用CSS控制）
        self.setBackground('w')

        # 设置图例
        self.addLegend(offset=(10, 10))

        # 启用自动范围
        self.enableAutoRange(axis='y')

        # 设置Y轴范围
        self.setYRange(0, 100)

        # 隐藏交互工具
        self.setMenuEnabled(False)
        self.setMouseEnabled(x=False, y=False)

    def _create_curves(self):
        """创建曲线和标记"""
        # 主数据曲线（青色霓虹效果）
        self.main_curve = self.plot(
            pen=pg.mkPen(color=(0, 212, 255, 200), width=2),
            name=self.y_label
        )

        # 填充区域（渐变效果）
        self.fill_curve = self.plot(
            pen=None,
            brush=pg.mkBrush(color=(0, 212, 255, 30)),
            name='填充'
        )

        # 阈值线
        if self.threshold is not None:
            self.add_threshold_line(self.threshold)

        # 告警点标记（红色散点）
        self.alert_scatter = pg.ScatterPlotItem(
            size=15,
            pen=pg.mkPen(color='#ef4444', width=2),
            brush=pg.mkBrush(color='#ef4444'),
            name='告警'
        )
        self.addItem(self.alert_scatter)

    def add_threshold_line(self, value: float, color: str = '#f59e0b'):
        """
        添加或更新阈值线

        Args:
            value: 阈值
            color: 颜色（十六进制）
        """
        if hasattr(self, 'threshold_line'):
            self.removeItem(self.threshold_line)

        self.threshold_line = pg.InfiniteLine(
            pos=value,
            angle=0,
            pen=pg.mkPen(color=color, width=1, style=Qt.PenStyle.DashLine),
            label=f'阈值: {value}{self.unit}',
            labelOpts={'position': 0.02, 'color': color}
        )
        self.addItem(self.threshold_line)

    def add_data_point(self, timestamp: datetime, value: float, is_alert: bool = False):
        """
        添加数据点

        Args:
            timestamp: 时间戳
            value: 数值
            is_alert: 是否为告警点
        """
        self.time_data.append(timestamp)
        self.value_data.append(value)

        # 如果超过最大点数，移除最早的数据
        if len(self.time_data) > self.max_points:
            self.time_data.pop(0)
            self.value_data.pop(0)

        # 更新曲线
        self._update_curves()

        # 记录告警点
        if is_alert and len(self.time_data) > 0:
            idx = len(self.time_data) - 1
            self.alert_points.append({
                'pos': (idx, value),
                'data': timestamp
            })
            self._update_alert_scatter()

    def _update_curves(self):
        """更新曲线显示"""
        if not self.time_data:
            return

        # 转换时间为相对秒数
        base_time = self.time_data[0]
        x_data = [(t - base_time).total_seconds() for t in self.time_data]

        # 更新主曲线
        self.main_curve.setData(x_data, self.value_data)

        # 更新填充区域
        if len(x_data) > 1:
            # 创建填充区域的数据（包括底部）
            x_fill = [x_data[0]] + x_data + [x_data[-1]]
            y_fill = [0] + list(self.value_data) + [0]
            self.fill_curve.setData(x_fill, y_fill)

        # 更新X轴范围
        self.setXRange(x_data[0], x_data[-1])

        # 设置X轴时间刻度标签
        x_axis = self.getAxis('bottom')
        ticks = []

        # 根据数据点数量决定刻度间隔
        if len(self.time_data) <= 10:
            interval = 1
        elif len(self.time_data) <= 20:
            interval = 2
        elif len(self.time_data) <= 50:
            interval = 5
        else:
            interval = 10

        for i in range(0, len(self.time_data), interval):
            if i < len(self.time_data):
                time_str = self.time_data[i].strftime("%H:%M:%S")
                ticks.append((x_data[i], time_str))

        if ticks:
            x_axis.setTicks([ticks])

    def _update_alert_scatter(self):
        """更新告警点显示"""
        if not self.alert_points:
            return

        # 准备散点数据
        spots = []
        base_time = self.time_data[0]

        for point in self.alert_points:
            x = (point['data'] - base_time).total_seconds()
            spots.append({'pos': (x, point['pos'][1])})

        self.alert_scatter.setData(spots)

    def update_data(self, timestamps: List[float], values: List[float]):
        """
        批量更新图表数据（用于显示历史静态数据）

        Args:
            timestamps: Unix 时间戳列表（秒）
            values: 指标值列表
        """
        if not timestamps or not values:
            return

        if len(timestamps) != len(values):
            raise ValueError(f"时间戳和值数量不匹配: {len(timestamps)} vs {len(values)}")

        # 清空现有数据
        self.clear_data()

        # 批量添加新数据点
        for ts, val in zip(timestamps, values):
            # 将 Unix 时间戳转换为 datetime
            dt = datetime.fromtimestamp(ts)
            self.time_data.append(dt)
            self.value_data.append(val)

        # 如果超过最大点数，保留最新的数据
        if len(self.time_data) > self.max_points:
            # 从后面保留 max_points 个数据点
            self.time_data = self.time_data[-self.max_points:]
            self.value_data = self.value_data[-self.max_points:]

        # 更新曲线显示
        self._update_curves()

    def clear_data(self):
        """清空所有数据"""
        self.time_data.clear()
        self.value_data.clear()
        self.alert_points.clear()
        self._update_curves()
        self.alert_scatter.setData([])

    def get_latest_value(self) -> Optional[float]:
        """获取最新数值"""
        if self.value_data:
            return self.value_data[-1]
        return None

    def get_average(self) -> float:
        """计算平均值"""
        if self.value_data:
            return sum(self.value_data) / len(self.value_data)
        return 0.0

    def get_max(self) -> float:
        """获取最大值"""
        if self.value_data:
            return max(self.value_data)
        return 0.0

    def get_min(self) -> float:
        """获取最小值"""
        if self.value_data:
            return min(self.value_data)
        return 0.0


class FPSTrendChart(TrendChartWidget):
    """FPS趋势图"""

    def __init__(self, max_points: int = 1000):
        super().__init__(
            title="FPS 趋势",
            y_label="帧率",
            unit=" fps",
            threshold=30,  # 低于30fps告警
            max_points=max_points
        )
        # 设置Y轴范围
        self.setYRange(0, 70)

    def add_data_point(self, timestamp: datetime, fps: int, jank: int = 0):
        """
        添加FPS数据点

        Args:
            timestamp: 时间戳
            fps: FPS值
            jank: 卡顿次数
        """
        is_alert = fps < self.threshold
        super().add_data_point(timestamp, fps, is_alert)


class MemoryTrendChart(TrendChartWidget):
    """内存趋势图"""

    def __init__(self, max_points: int = 1000):
        super().__init__(
            title="内存趋势",
            y_label="内存",
            unit=" MB",
            threshold=500,  # 超过500MB告警
            max_points=max_points
        )
        self.setYRange(0, 1000)

    def add_data_point(self, timestamp: datetime, memory_mb: float):
        """
        添加内存数据点

        Args:
            timestamp: 时间戳
            memory_mb: 内存值（MB）
        """
        is_alert = memory_mb > self.threshold
        super().add_data_point(timestamp, memory_mb, is_alert)


class CPUTrendChart(TrendChartWidget):
    """CPU趋势图"""

    def __init__(self, max_points: int = 1000):
        super().__init__(
            title="CPU 趋势",
            y_label="CPU使用率",
            unit=" %",
            threshold=80,  # 超过80%告警
            max_points=max_points
        )
        self.setYRange(0, 100)

    def add_data_point(self, timestamp: datetime, cpu_percent: float):
        """
        添加CPU数据点

        Args:
            timestamp: 时间戳
            cpu_percent: CPU使用率（%）
        """
        is_alert = cpu_percent > self.threshold
        super().add_data_point(timestamp, cpu_percent, is_alert)


class NetworkTrendChart(TrendChartWidget):
    """网络流量趋势图"""

    def __init__(self, max_points: int = 1000):
        super().__init__(
            title="网络流量趋势",
            y_label="流量速率",
            unit=" KB/s",
            max_points=max_points
        )
        # 不设置固定阈值
        self.setYRange(0, 100)

        # 上行和下行两条曲线
        self.upload_curve = self.plot(
            pen=pg.mkPen(color=(34, 197, 94, 200), width=2),  # 绿色
            name='上行'
        )
        self.download_curve = self.plot(
            pen=pg.mkPen(color=(59, 130, 246, 200), width=2),  # 蓝色
            name='下行'
        )

        # 上传和下载数据
        self.upload_data = []
        self.download_data = []

    def add_data_point(self, timestamp: datetime, upload_kbs: float, download_kbs: float):
        """
        添加网络流量数据点

        Args:
            timestamp: 时间戳
            upload_kbs: 上行速率（KB/s）
            download_kbs: 下行速率（KB/s）
        """
        self.upload_data.append(upload_kbs)
        self.download_data.append(download_kbs)

        # 总流量用于告警
        total_rate = upload_kbs + download_kbs
        super().add_data_point(timestamp, total_rate, False)

        # 如果超过最大点数，移除最早的数据
        if len(self.upload_data) > self.max_points:
            self.upload_data.pop(0)
            self.download_data.pop(0)

        # 更新上行和下行曲线
        if self.time_data:
            base_time = self.time_data[0]
            x_data = [(t - base_time).total_seconds() for t in self.time_data]
            self.upload_curve.setData(x_data, self.upload_data)
            self.download_curve.setData(x_data, self.download_data)

            # 自动调整Y轴范围
            max_rate = max(max(self.upload_data), max(self.download_data))
            self.setYRange(0, max_rate * 1.2)

    def clear_data(self):
        """清空所有数据"""
        super().clear_data()
        self.upload_data.clear()
        self.download_data.clear()


class BatteryTrendChart(TrendChartWidget):
    """电池温度趋势图"""

    def __init__(self, max_points: int = 1000):
        super().__init__(
            title="电池温度趋势",
            y_label="温度",
            unit=" °C",
            threshold=45,  # 超过45°C告警
            max_points=max_points
        )
        self.setYRange(20, 60)

    def add_data_point(self, timestamp: datetime, temperature: float):
        """
        添加温度数据点

        Args:
            timestamp: 时间戳
            temperature: 温度（°C）
        """
        is_alert = temperature > self.threshold
        super().add_data_point(timestamp, temperature, is_alert)


class ChartsContainer(QWidget):
    """
    图表容器
    包含多个标签页的趋势图
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.charts = {}
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 创建图表（使用标签页切换）
        from PyQt6.QtWidgets import QTabWidget

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                background-color: #0a0e17;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #121824;
                color: #94a3b8;
                border: 1px solid #1a1f2e;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 16px;
                margin-right: 4px;
            }
            QTabBar::tab:hover {
                background-color: #1a1f2e;
                color: #e0e6ed;
            }
            QTabBar::tab:selected {
                background-color: #0a0e17;
                color: #00d4ff;
                border-color: #00d4ff;
            }
        """)

        # 添加各类图表
        self.fps_chart = FPSTrendChart()
        self.tab_widget.addTab(self.fps_chart, "FPS")
        self.charts["fps"] = self.fps_chart

        self.memory_chart = MemoryTrendChart()
        self.tab_widget.addTab(self.memory_chart, "内存")
        self.charts["memory"] = self.memory_chart

        self.cpu_chart = CPUTrendChart()
        self.tab_widget.addTab(self.cpu_chart, "CPU")
        self.charts["cpu"] = self.cpu_chart

        self.network_chart = NetworkTrendChart()
        self.tab_widget.addTab(self.network_chart, "网络")
        self.charts["network"] = self.network_chart

        self.battery_chart = BatteryTrendChart()
        self.tab_widget.addTab(self.battery_chart, "电池")
        self.charts["battery"] = self.battery_chart

        layout.addWidget(self.tab_widget)

    def update_charts(self, metrics_data: dict):
        """
        更新所有图表

        Args:
            metrics_data: 包含时间戳和各项指标的字典
        """
        timestamp = metrics_data.get("timestamp", datetime.now())

        # 更新FPS
        if "fps" in metrics_data:
            fps = metrics_data["fps"]
            if isinstance(fps, dict):
                self.fps_chart.add_data_point(
                    timestamp,
                    fps.get("fps", 0),
                    fps.get("jank", 0)
                )

        # 更新内存
        if "memory" in metrics_data:
            memory = metrics_data["memory"]
            if isinstance(memory, dict):
                self.memory_chart.add_data_point(
                    timestamp,
                    memory.get("total_mb", 0)
                )

        # 更新CPU
        if "cpu" in metrics_data:
            cpu = metrics_data["cpu"]
            if isinstance(cpu, dict):
                self.cpu_chart.add_data_point(
                    timestamp,
                    cpu.get("app_cpu_rate", 0)
                )

        # 更新网络
        if "network" in metrics_data:
            network = metrics_data["network"]
            if isinstance(network, dict):
                self.network_chart.add_data_point(
                    timestamp,
                    network.get("upload_rate_kbs", 0),
                    network.get("download_rate_kbs", 0)
                )

        # 更新电池
        if "battery" in metrics_data:
            battery = metrics_data["battery"]
            if isinstance(battery, dict):
                self.battery_chart.add_data_point(
                    timestamp,
                    battery.get("temperature", 0)
                )

    def clear_all_charts(self):
        """清空所有图表数据"""
        for chart in self.charts.values():
            chart.clear_data()
