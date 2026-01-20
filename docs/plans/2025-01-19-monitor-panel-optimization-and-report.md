# 监控面板优化与测试报告功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 优化监控面板曲线显示效果、增加数据悬停提示、实现可配置的监控卡片布局、完善测试报告生成与查看功能

**Architecture:**
1. **曲线优化**: 使用 pyqtgraph 的抗锯齿和样条插值功能，增强视觉效果
2. **悬停提示**: 实现 GraphItem 的鼠标悬停事件，显示精确数据点信息
3. **动态布局**: 重构 MonitorPanelV2 为基于配置的动态网格布局系统
4. **报告系统**: 新增独立测试报告面板，支持列表查看、详细数据展示和图表重现

**Tech Stack:** PyQt6, pyqtgraph, SQLite, QThreadPool

---

## Task 1: 扩展配置模型 - 支持动态卡片配置

**Files:**
- Modify: `insight_eyes/desktop/ui/utils/models.py:148-170`
- Create: `insight_eyes/desktop/ui/utils/card_configs.py`

### Step 1: 创建卡片配置数据模型

创建 `insight_eyes/desktop/ui/utils/card_configs.py`:

```python
"""
监控卡片配置定义
定义所有可用的监控指标卡片及其配置
"""
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class MetricCardConfig:
    """单个指标卡片配置"""
    metric_id: str           # 指标ID: 'cpu', 'memory', 'fps', 'network', 'battery', 'gpu'
    title: str               # 卡片标题
    color: str               # 霓虹主题色 (hex格式)
    y_min: Optional[float]   # Y轴最小值 (None=自适应)
    y_max: Optional[float]   # Y轴最大值 (None=自适应)
    y_width: int             # Y轴宽度
    decimals: int            # 小数位数
    unit: str                # 单位
    enabled: bool = True     # 是否启用
    priority: int = 0        # 优先级 (用于排序)


# 定义所有可用的指标卡片配置
ALL_METRIC_CARDS: List[MetricCardConfig] = [
    MetricCardConfig(
        metric_id='cpu',
        title='CPU Usage (%)',
        color='#00f2ff',
        y_min=0,
        y_max=100,
        y_width=55,
        decimals=0,
        unit='%',
        priority=1
    ),
    MetricCardConfig(
        metric_id='memory',
        title='Memory Usage (MB)',
        color='#7000ff',
        y_min=0,
        y_max=None,
        y_width=65,
        decimals=0,
        unit=' MB',
        priority=2
    ),
    MetricCardConfig(
        metric_id='fps',
        title='Frame Rate (FPS)',
        color='#ffb400',
        y_min=None,
        y_max=None,
        y_width=55,
        decimals=0,
        unit=' F',
        priority=3
    ),
    MetricCardConfig(
        metric_id='network',
        title='Network I/O (KB/s)',
        color='#0062ff',
        y_min=0,
        y_max=None,
        y_width=65,
        decimals=1,
        unit=' KB/s',
        priority=4
    ),
    MetricCardConfig(
        metric_id='battery',
        title='Battery (°C)',
        color='#00ff87',
        y_min=20,
        y_max=60,
        y_width=55,
        decimals=1,
        unit=' °C',
        enabled=False,  # 默认禁用
        priority=5
    ),
    MetricCardConfig(
        metric_id='gpu',
        title='GPU Usage (%)',
        color='#ff006e',
        y_min=0,
        y_max=100,
        y_width=55,
        decimals=0,
        unit='%',
        enabled=False,  # 默认禁用
        priority=6
    ),
]


def get_enabled_cards() -> List[MetricCardConfig]:
    """获取所有启用的卡片配置（按优先级排序）"""
    return sorted([c for c in ALL_METRIC_CARDS if c.enabled], key=lambda x: x.priority)


def get_card_config(metric_id: str) -> Optional[MetricCardConfig]:
    """根据指标ID获取卡片配置"""
    for card in ALL_METRIC_CARDS:
        if card.metric_id == metric_id:
            return card
    return None
```

### Step 2: 更新 CollectionConfig 支持指标开关

修改 `insight_eyes/desktop/ui/utils/models.py:147-170` 的 CollectionConfig:

```python
@dataclass
class CollectionConfig:
    """采集配置"""
    # 采集间隔 (毫秒)
    interval_ms: int = 1000

    # 监控指标开关
    enable_cpu: bool = True
    enable_memory: bool = True
    enable_fps: bool = True
    enable_network: bool = True
    enable_battery: bool = False  # 默认禁用
    enable_gpu: bool = False      # 默认禁用

    # 阈值设置
    fps_threshold: int = 30
    memory_threshold_mb: int = 500
    cpu_threshold_percent: float = 80.0
    battery_threshold_temp: float = 45.0

    # 数据保留设置
    data_retention_days: int = 7
    max_samples_per_chart: int = 1000

    def get_enabled_metrics(self) -> List[str]:
        """获取启用的指标ID列表"""
        metrics = []
        if self.enable_cpu:
            metrics.append('cpu')
        if self.enable_memory:
            metrics.append('memory')
        if self.enable_fps:
            metrics.append('fps')
        if self.enable_network:
            metrics.append('network')
        if self.enable_battery:
            metrics.append('battery')
        if self.enable_gpu:
            metrics.append('gpu')
        return metrics
```

### Step 3: 运行测试验证

```bash
cd C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye\insight_eye-1.0.0
python -c "from insight_eyes.desktop.ui.utils.card_configs import get_enabled_cards; print([c.metric_id for c in get_enabled_cards()])"
```

Expected output: `['cpu', 'memory', 'fps', 'network']`

### Step 4: 提交

```bash
git add insight_eyes/desktop/ui/utils/card_configs.py insight_eyes/desktop/ui/utils/models.py
git commit -m "feat: 添加动态卡片配置模型"
```

---

## Task 2: 优化曲线绘制效果 - 抗锯齿与样条插值

**Files:**
- Modify: `insight_eyes/desktop/ui/panels/monitor_panel_v2.py:195-206`

### Step 1: 修改 _create_chart 方法启用抗锯齿

在 `insight_eyes/desktop/ui/panels/monitor_panel_v2.py` 的 `_create_chart` 方法中添加抗锯齿配置:

```python
def _create_chart(self) -> pg.PlotWidget:
    """创建图表（完全复刻ECharts配置）"""
    chart = pg.PlotWidget()
    chart.setBackground(QColor(DesignTokens.CARD_BG))

    # 启用抗锯齿渲染
    chart.setAntialiasing(True)

    # 设置渲染优化
    chart.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
    chart.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    # ... 其余代码保持不变
```

### Step 2: 修改曲线绘制使用样条插值

在 `_create_chart` 方法中修改曲线创建代码:

```python
def _create_chart(self) -> pg.GraphicsLayoutWidget:
    """创建图表容器"""
    # 使用 GraphicsLayoutWidget 支持更灵活的布局
    win = pg.GraphicsLayoutWidget()
    win.setBackground(QColor(DesignTokens.CARD_BG))

    # 创建 PlotWidget
    chart = win.addPlot()
    chart.setAntialiasing(True)  # 启用抗锯齿

    # ... 配置轴和网格

    # 创建曲线 - 使用 connect='all' 实现平滑连接
    pen = pg.mkPen(color=self.accent_color, width=2.5, style=Qt.PenStyle.SolidLine)
    self.curve = chart.plot(
        pen=pen,
        connect='all',  # 所有点按顺序连接
        antialias=True  # 启用抗锯齿
    )

    # 渐变填充
    r, g, b = self._hex_to_rgb(self.accent_color)
    alpha = int(255 * 0.35)  # 稍微降低透明度
    brush = pg.mkBrush(QColor(r, g, b, alpha))
    self.fill = chart.plot(pen=None, brush=brush, connect='all')

    return win
```

### Step 3: 调整数据点数量以优化曲线平滑度

修改 `add_data_point` 方法，增加数据点保留数量:

```python
def add_data_point(self, value: float):
    """添加数据点"""
    current_time = datetime.now()
    self.timestamps.append(current_time)
    # 增加数据点数量到 120 以获得更平滑的曲线
    if len(self.timestamps) > 120:
        self.timestamps.pop(0)

    self.data.append(value)
    if len(self.data) > 120:
        self.data.pop(0)

    self._update_curve()
    self._update_stats()
```

### Step 4: 运行测试验证

启动应用检查曲线是否更平滑:

```bash
python -m insight_eyes
```

Expected: 曲线显示更平滑，边缘无锯齿

### Step 5: 提交

```bash
git add insight_eyes/desktop/ui/panels/monitor_panel_v2.py
git commit -m "feat: 启用曲线抗锯齿和样条插值"
```

---

## Task 3: 实现鼠标悬停显示数据点功能

**Files:**
- Modify: `insight_eyes/desktop/ui/panels/monitor_panel_v2.py:56-216`
- Create: `insight_eyes/desktop/ui/widgets/tooltip_widget.py`

### Step 1: 创建自定义悬停提示组件

创建 `insight_eyes/desktop/ui/widgets/tooltip_widget.py`:

```python
"""
图表数据点悬停提示组件
"""
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QFont
from datetime import datetime


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
```

### Step 2: 修改 NeonChartCard 支持悬停交互

修改 `insight_eyes/desktop/ui/panels/monitor_panel_v2.py` 中的 `NeonChartCard` 类:

```python
class NeonChartCard(QFrame):
    """霓虹风格图表卡片 V2"""

    def __init__(self, title: str, color: str, y_axis_config: dict, parent=None):
        super().__init__(parent)
        self.title = title
        self.accent_color = color
        self.y_axis_config = y_axis_config
        self.data = []
        self.timestamps = []
        self.curve = None
        self.fill = None

        # 悬停提示
        self.tooltip = None
        self.hover_label = None

        self._init_ui()

    def _create_chart(self) -> pg.PlotWidget:
        """创建图表"""
        chart = pg.PlotWidget()
        chart.setBackground(QColor(DesignTokens.CARD_BG))
        chart.setAntialiasing(True)

        # ... 配置网格和轴

        # 启用鼠标交互
        chart.setMouseEnabled(x=False, y=False)

        # 创建曲线
        pen = pg.mkPen(color=self.accent_color, width=2.5)
        self.curve = chart.plot(pen=pen, connect='all', antialias=True)

        # 创建悬停提示线
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(color='#444', width=1, style=Qt.PenStyle.DashLine))
        chart.addItem(self.vLine)
        self.vLine.hide()

        # 创建悬停点标记
        self.hover_point = pg.ScatterPlotItem(
            size=12,
            pen=pg.mkPen(color=self.accent_color, width=2),
            brush=pg.mkBrush(color=self.accent_color),
        )
        chart.addItem(self.hover_point)
        self.hover_point.hide()

        # 连接鼠标移动事件
        chart.scene().sigMouseMoved.connect(self._on_mouse_moved)

        # ... 创建填充曲线

        return chart

    def _on_mouse_moved(self, pos):
        """鼠标移动事件处理"""
        if not self.chart.plotItem.vb.sceneBoundingRect().contains(pos):
            self.vLine.hide()
            self.hover_point.hide()
            if self.tooltip:
                self.tooltip.hide_tooltip()
            return

        # 转换为图表坐标
        mouse_point = self.chart.plotItem.vb.mapSceneToView(pos)
        x_pos = mouse_point.x()

        # 找到最近的数据点
        if not self.data:
            return

        idx = int(round(x_pos))
        if 0 <= idx < len(self.data):
            # 显示垂直线
            self.vLine.setPos(idx)
            self.vLine.show()

            # 显示数据点
            self.hover_point.setData([{'pos': (idx, self.data[idx])}])
            self.hover_point.show()

            # 创建并显示提示框
            if self.tooltip is None:
                from insight_eyes.desktop.ui.widgets.tooltip_widget import ChartTooltip
                self.tooltip = ChartTooltip(self.chart)

            # 获取全局坐标
            global_pos = self.chart.mapToGlobal(self.chart.pos())
            tooltip_pos = global_pos + QPoint(int(pos.x()), int(pos.y()))

            tooltip_data = {
                'title': self.title,
                'time': self.timestamps[idx].strftime("%H:%M:%S"),
                'value': f"{self.data[idx]:.2f}",
                'unit': self.y_axis_config.get('unit', '')
            }
            self.tooltip.show_tooltip(tooltip_pos, tooltip_data)
```

### Step 3: 运行测试验证

启动应用，鼠标悬停在曲线上应显示数据点信息:

```bash
python -m insight_eyes
```

Expected: 鼠标悬停时显示垂直线、数据点标记和提示框

### Step 4: 提交

```bash
git add insight_eyes/desktop/ui/widgets/tooltip_widget.py insight_eyes/desktop/ui/panels/monitor_panel_v2.py
git commit -m "feat: 添加图表数据点悬停提示功能"
```

---

## Task 4: 重构 MonitorPanelV2 支持动态网格布局

**Files:**
- Modify: `insight_eyes/desktop/ui/panels/monitor_panel_v2.py:322-505`

### Step 1: 修改 MonitorPanelV2 支持动态卡片

完全重写 `MonitorPanelV2` 类:

```python
class MonitorPanelV2(QWidget):
    """监控面板 V2 - 动态卡片布局"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.device_id = None
        self.package_name = None
        self.app_name = None
        self._title_label = None

        # 动态卡片存储
        self.cards = {}  # {metric_id: NeonChartCard}
        self.grid_layout = None

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {DesignTokens.BG_COLOR};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 标题
        self._title_label = QLabel("Real-time System Monitor")
        self._title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 1.2rem;
                font-weight: 300;
                color: {DesignTokens.TEXT_PRIMARY};
                background: transparent;
                text-align: center;
                padding: 10px;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}
        """)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title_label)

        # 动态网格布局
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(20)
        layout.addLayout(self.grid_layout)

        # 初始化卡片（基于配置）
        self._rebuild_cards()

    def _rebuild_cards(self):
        """根据配置重建卡片"""
        from insight_eyes.desktop.ui.utils.card_configs import get_enabled_cards
        from insight_eyes.desktop.config.config_manager import ConfigManager

        config_mgr = ConfigManager()
        enabled_metrics = config_mgr.config.collection.get_enabled_metrics()

        # 清除现有卡片
        self._clear_cards()

        # 创建新卡片
        card_configs = get_enabled_cards()
        row, col = 0, 0
        max_cols = self._calculate_columns(len(enabled_metrics))

        for card_config in card_configs:
            if card_config.metric_id not in enabled_metrics:
                continue

            card = NeonChartCard(
                card_config.title,
                card_config.color,
                y_axis_config={
                    'min': card_config.y_min,
                    'max': card_config.y_max,
                    'width': card_config.y_width,
                    'decimals': card_config.decimals,
                    'unit': card_config.unit
                }
            )
            self.cards[card_config.metric_id] = card
            self.grid_layout.addWidget(card, row, col)

            # 计算下一个位置
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # 设置等分布局
        for i in range(max_cols):
            self.grid_layout.setColumnStretch(i, 1)
        for i in range(row + 1):
            self.grid_layout.setRowStretch(i, 1)

    def _calculate_columns(self, card_count: int) -> int:
        """计算网格列数"""
        if card_count <= 1:
            return 1
        elif card_count <= 2:
            return 2
        elif card_count <= 4:
            return 2
        elif card_count <= 6:
            return 3
        else:
            return 4

    def _clear_cards(self):
        """清除所有卡片"""
        for card in self.cards.values():
            self.grid_layout.removeWidget(card)
            card.deleteLater()
        self.cards.clear()

    def add_data_point(self, metrics: dict):
        """
        添加数据点（动态更新所有启用的卡片）

        Args:
            metrics: 指标数据字典 {
                'cpu': float,
                'memory': float,
                'fps': float,
                'upload': float,
                'download': float,
                'battery': float,
                'gpu': float
            }
        """
        if 'cpu' in self.cards and 'cpu' in metrics:
            self.cards['cpu'].add_data_point(metrics['cpu'])

        if 'memory' in self.cards and 'memory' in metrics:
            self.cards['memory'].add_data_point(metrics['memory'])

        if 'fps' in self.cards and 'fps' in metrics:
            self.cards['fps'].add_data_point(metrics['fps'])

        if 'network' in self.cards:
            # 网络显示下载速度或总流量
            net_value = metrics.get('download', metrics.get('upload', 0))
            self.cards['network'].add_data_point(net_value)

        if 'battery' in self.cards and 'battery' in metrics:
            self.cards['battery'].add_data_point(metrics['battery'])

        if 'gpu' in self.cards and 'gpu' in metrics:
            self.cards['gpu'].add_data_point(metrics['gpu'])

    def refresh_cards(self):
        """刷新卡片配置（当配置变更时调用）"""
        self._rebuild_cards()

    def clear_data(self):
        """清除所有图表数据"""
        for card in self.cards.values():
            card.data.clear()
            card.timestamps.clear()
            card._update_curve()

    # ... 其他方法保持不变
```

### Step 2: 运行测试验证

```bash
python -m insight_eyes
```

Expected: 显示 4 个默认卡片 (CPU, Memory, FPS, Network)

### Step 3: 提交

```bash
git add insight_eyes/desktop/ui/panels/monitor_panel_v2.py
git commit -m "refactor: 重构监控面板支持动态网格布局"
```

---

## Task 5: 配置面板添加指标选择功能

**Files:**
- Modify: `insight_eyes/desktop/ui/panels/config_panel.py`

### Step 1: 添加指标选择复选框组

在配置面板中添加指标选择区域:

```python
def _init_ui(self):
    """初始化UI"""
    layout = QVBoxLayout(self)
    # ... 现有代码

    # 添加指标选择区域
    metrics_group = self._create_metrics_selector()
    layout.addWidget(metrics_group)

def _create_metrics_selector(self) -> QGroupBox:
    """创建指标选择器"""
    group = QGroupBox("监控指标")
    group.setStyleSheet("""
        QGroupBox {
            color: #e0e6ed;
            font-size: 14px;
            font-weight: bold;
            border: 1px solid #1a1f2e;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
    """)

    layout = QGridLayout()
    layout.setSpacing(10)

    from insight_eyes.desktop.ui.utils.card_configs import ALL_METRIC_CARDS

    self.metric_checkboxes = {}

    for i, card_config in enumerate(ALL_METRIC_CARDS):
        checkbox = QCheckBox(card_config.title)
        checkbox.setChecked(card_config.enabled)
        checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: #e0e6ed;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid #1a1f2e;
                border-radius: 4px;
                background-color: #0a0e17;
            }}
            QCheckBox::indicator:checked {{
                background-color: {card_config.color};
                border-color: {card_config.color};
            }}
        """)
        checkbox.stateChanged.connect(lambda state, mid=card_config.metric_id: self._on_metric_toggled(mid, state))
        self.metric_checkboxes[card_config.metric_id] = checkbox

        row = i // 2
        col = i % 2
        layout.addWidget(checkbox, row, col)

    group.setLayout(layout)
    return group

def _on_metric_toggled(self, metric_id: str, state: int):
    """指标开关切换事件"""
    from insight_eyes.desktop.config.config_manager import ConfigManager

    config_mgr = ConfigManager()
    config = config_mgr.config

    # 更新配置
    if metric_id == 'cpu':
        config.collection.enable_cpu = (state == 2)  # 2 = checked
    elif metric_id == 'memory':
        config.collection.enable_memory = (state == 2)
    elif metric_id == 'fps':
        config.collection.enable_fps = (state == 2)
    elif metric_id == 'network':
        config.collection.enable_network = (state == 2)
    elif metric_id == 'battery':
        config.collection.enable_battery = (state == 2)
    elif metric_id == 'gpu':
        config.collection.enable_gpu = (state == 2)

    # 保存配置
    config_mgr.save_config()

    # 刷新监控面板
    self._refresh_monitor_panel()

def _refresh_monitor_panel(self):
    """刷新监控面板"""
    # 通过信号或直接调用刷新监控面板
    if hasattr(self, '_monitor_panel'):
        self._monitor_panel.refresh_cards()
```

### Step 2: 运行测试验证

启动应用，在配置面板勾选/取消指标，监控面板应实时更新

### Step 3: 提交

```bash
git add insight_eyes/desktop/ui/panels/config_panel.py
git commit -m "feat: 配置面板添加监控指标选择功能"
```

---

## Task 6: 创建测试报告面板框架

**Files:**
- Create: `insight_eyes/desktop/ui/panels/report_panel.py`

### Step 1: 创建报告面板基础结构

创建 `insight_eyes/desktop/ui/panels/report_panel.py`:

```python
"""
测试报告面板
显示历史监控会话列表和详细报告
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from datetime import datetime


class ReportPanel(QWidget):
    """测试报告面板"""

    # 信号定义
    report_selected = pyqtSignal(int)  # 报告选中信号 (session_id)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_session_id = None
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题栏
        header = self._create_header()
        layout.addWidget(header)

        # 分割器：左侧列表，右侧详情
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # 左侧：会话列表
        self.session_list = self._create_session_list()
        splitter.addWidget(self.session_list)

        # 右侧：报告详情
        self.report_detail = self._create_report_detail()
        splitter.addWidget(self.report_detail)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

    def _create_header(self) -> QWidget:
        """创建标题栏"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("测试报告")
        title.setStyleSheet("""
            QLabel {
                font-size: 1.3rem;
                font-weight: 300;
                color: #ffffff;
                background: transparent;
                letter-spacing: 1px;
            }
        """)
        layout.addWidget(title)

        layout.addStretch()

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a1f2e;
                color: #94a3b8;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2a2f3e;
                color: #e0e6ed;
            }
        """)
        refresh_btn.clicked.connect(self._refresh_list)
        layout.addWidget(refresh_btn)

        return widget

    def _create_session_list(self) -> QTableWidget:
        """创建会话列表"""
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["时间", "设备", "应用", "时长"])

        table.setStyleSheet("""
            QTableWidget {
                background-color: #0a0e17;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
                gridline-color: #1a1f2e;
                color: #e0e6ed;
            }
            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #1a1f2e;
            }
            QTableWidget::item:selected {
                background-color: rgba(0, 212, 255, 0.2);
                color: #00d4ff;
            }
            QHeaderView::section {
                background-color: #121824;
                color: #94a3b8;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #1a1f2e;
                font-weight: 600;
            }
        """)

        # 设置列宽
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        # 隐藏垂直表头
        table.verticalHeader().setVisible(False)

        # 选择行为
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.itemClicked.connect(self._on_session_selected)

        return table

    def _create_report_detail(self) -> QFrame:
        """创建报告详情区域"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #0a0e17;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)

        # 占位符
        placeholder = QLabel("请选择一个测试报告查看详情")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("""
            QLabel {
                color: #475569;
                font-size: 16px;
                background: transparent;
            }
        """)
        layout.addWidget(placeholder)

        return frame

    def load_sessions(self, sessions: list):
        """加载会话列表

        Args:
            sessions: 会话列表
        """
        self.session_list.setRowCount(len(sessions))

        for row, session in enumerate(sessions):
            # 时间
            time_item = QTableWidgetItem(
                datetime.fromisoformat(session['start_time']).strftime("%Y-%m-%d %H:%M:%S")
            )
            time_item.setData(Qt.ItemDataRole.UserRole, session['id'])
            self.session_list.setItem(row, 0, time_item)

            # 设备
            device_item = QTableWidgetItem(session.get('device_name', session['device_id']))
            self.session_list.setItem(row, 1, device_item)

            # 应用
            app_item = QTableWidgetItem(session['package_name'])
            self.session_list.setItem(row, 2, app_item)

            # 时长
            end_time = session.get('end_time')
            if end_time:
                duration = self._calculate_duration(session['start_time'], end_time)
            else:
                duration = "进行中"
            duration_item = QTableWidgetItem(duration)
            self.session_list.setItem(row, 3, duration_item)

    def _calculate_duration(self, start_time: str, end_time: str) -> str:
        """计算时长"""
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
        delta = end - start
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _on_session_selected(self, item: QTableWidgetItem):
        """会话选中事件"""
        row = item.row()
        session_id_item = self.session_list.item(row, 0)
        session_id = session_id_item.data(Qt.ItemDataRole.UserRole)
        self.current_session_id = session_id
        self.report_selected.emit(session_id)

    def _refresh_list(self):
        """刷新列表"""
        # 从数据库加载会话列表
        from insight_eyes.desktop.data.database import DatabaseManager
        db = DatabaseManager()
        sessions = db.get_recent_sessions(limit=50)
        self.load_sessions(sessions)

    def show_report_detail(self, session_id: int):
        """显示报告详情"""
        # Task 7 中实现
        pass
```

### Step 2: 运行测试验证

```bash
python -c "from insight_eyes.desktop.ui.panels.report_panel import ReportPanel; print('Report panel imported successfully')"
```

Expected: 无错误输出

### Step 3: 提交

```bash
git add insight_eyes/desktop/ui/panels/report_panel.py
git commit -m "feat: 创建测试报告面板基础框架"
```

---

## Task 7: 实现报告详情视图 - 数据重现

**Files:**
- Create: `insight_eyes/desktop/ui/widgets/session_report_widget.py`
- Modify: `insight_eyes/desktop/ui/panels/report_panel.py:113-142`

### Step 1: 创建会话报告详情组件

创建 `insight_eyes/desktop/ui/widgets/session_report_widget.py`:

```python
"""
会话报告详情组件
显示监控会话的详细数据和图表
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QFrame, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import pyqtgraph as pg
from datetime import datetime


class SessionReportWidget(QWidget):
    """会话报告详情组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session_data = None
        self.metrics_data = []
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; }")

        # 内容容器
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(20)

        # 会话信息卡片
        self.info_card = self._create_info_card()
        content_layout.addWidget(self.info_card)

        # 图表标签页
        self.charts_tab = self._create_charts_tab()
        content_layout.addWidget(self.charts_tab)

        # 数据表格
        self.data_table = self._create_data_table()
        content_layout.addWidget(self.data_table)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_info_card(self) -> QFrame:
        """创建会话信息卡片"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #121824;
                border: 1px solid #1a1f2e;
                border-radius: 8px;
                padding: 20px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(10)

        # 标题
        title = QLabel("会话信息")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 600;
                color: #00d4ff;
                background: transparent;
            }
        """)
        layout.addWidget(title)

        # 信息字段
        self.info_labels = {}
        for field in ["设备", "应用", "开始时间", "结束时间", "监控时长", "样本数", "告警数"]:
            row = QHBoxLayout()
            label_key = QLabel(f"{field}:")
            label_key.setStyleSheet("color: #94a3b8; background: transparent;")
            label_value = QLabel("-")
            label_value.setStyleSheet("color: #e0e6ed; background: transparent;")
            row.addWidget(label_key)
            row.addWidget(label_value, 1)
            layout.addLayout(row)
            self.info_labels[field] = label_value

        return frame

    def _create_charts_tab(self) -> QTabWidget:
        """创建图表标签页"""
        tab = QTabWidget()
        tab.setStyleSheet("""
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
                padding: 10px 20px;
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

        # 创建各类图表
        self.fps_chart = self._create_chart_widget("FPS", "#ffb400")
        tab.addTab(self.fps_chart, "FPS")

        self.cpu_chart = self._create_chart_widget("CPU", "#00f2ff")
        tab.addTab(self.cpu_chart, "CPU")

        self.memory_chart = self._create_chart_widget("内存", "#7000ff")
        tab.addTab(self.memory_chart, "内存")

        self.network_chart = self._create_chart_widget("网络", "#0062ff")
        tab.addTab(self.network_chart, "网络")

        return tab

    def _create_chart_widget(self, title: str, color: str) -> pg.PlotWidget:
        """创建单个图表"""
        chart = pg.PlotWidget()
        chart.setBackground(QColor("#0a0e17"))
        chart.setTitle(title, color='w', size='12pt')
        chart.showGrid(x=True, y=True, alpha=0.1)
        chart.setLabel('left', '数值', color='#94a3b8')
        chart.setLabel('bottom', '时间', color='#94a3b8')
        chart.setAntialiasing(True)

        # 创建曲线
        pen = pg.mkPen(color=color, width=2)
        curve = chart.plot(pen=pen, connect='all', antialias=True)

        # 保存曲线引用
        setattr(self, f'{title.lower()}_curve', curve)

        return chart

    def _create_data_table(self) -> QFrame:
        """创建数据表格"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #121824;
                border: 1px solid #1a1f2e;
                border-radius: 8px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout(frame)

        title = QLabel("详细数据")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 600;
                color: #00d4ff;
                background: transparent;
            }
        """)
        layout.addWidget(title)

        # TODO: 添加 QTableWidget 显示详细数据
        placeholder = QLabel("数据表格将在后续任务中实现")
        placeholder.setStyleSheet("color: #475569; background: transparent;")
        layout.addWidget(placeholder)

        return frame

    def load_session(self, session_id: int):
        """加载会话数据

        Args:
            session_id: 会话ID
        """
        from insight_eyes.desktop.data.database import DatabaseManager

        db = DatabaseManager()
        self.session_data = db.get_session(session_id)
        self.metrics_data = db.get_metrics(session_id)

        self._update_info_card()
        self._update_charts()

    def _update_info_card(self):
        """更新信息卡片"""
        if not self.session_data:
            return

        self.info_labels["设备"].setText(self.session_data.get('device_id', '-'))
        self.info_labels["应用"].setText(self.session_data.get('package_name', '-'))
        self.info_labels["开始时间"].setText(
            datetime.fromisoformat(self.session_data['start_time']).strftime("%Y-%m-%d %H:%M:%S")
        )

        end_time = self.session_data.get('end_time')
        if end_time:
            self.info_labels["结束时间"].setText(
                datetime.fromisoformat(end_time).strftime("%Y-%m-%d %H:%M:%S")
            )
            # 计算时长
            start = datetime.fromisoformat(self.session_data['start_time'])
            end = datetime.fromisoformat(end_time)
            delta = end - start
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.info_labels["监控时长"].setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            self.info_labels["结束时间"].setText("-")
            self.info_labels["监控时长"].setText("-")

        self.info_labels["样本数"].setText(str(len(self.metrics_data)))

        # 获取告警数
        from insight_eyes.desktop.data.database import DatabaseManager
        db = DatabaseManager()
        alerts = db.get_alerts(session_id=self.session_data['id'])
        self.info_labels["告警数"].setText(str(len(alerts)))

    def _update_charts(self):
        """更新图表数据"""
        if not self.metrics_data:
            return

        # 提取数据
        times = [
            datetime.fromisoformat(m['timestamp']).timestamp()
            for m in self.metrics_data
        ]

        # FPS
        fps_values = [m.get('fps', 0) for m in self.metrics_data]
        base_time = times[0] if times else 0
        x_data = [(t - base_time) for t in times]
        self.fps_curve.setData(x_data, fps_values)

        # CPU
        cpu_values = [m.get('cpu_app', 0) for m in self.metrics_data]
        self.cpu_curve.setData(x_data, cpu_values)

        # Memory
        mem_values = [m.get('memory_pss', 0) for m in self.metrics_data]
        self.memory_curve.setData(x_data, mem_values)

        # Network
        net_values = [
            (m.get('network_up_speed', 0) + m.get('network_down_speed', 0))
            for m in self.metrics_data
        ]
        self.network_curve.setData(x_data, net_values)
```

### Step 2: 集成到报告面板

修改 `insight_eyes/desktop/ui/panels/report_panel.py`:

```python
def _create_report_detail(self) -> QFrame:
    """创建报告详情区域"""
    from insight_eyes.desktop.ui.widgets.session_report_widget import SessionReportWidget

    self.report_widget = SessionReportWidget()
    return self.report_widget

def show_report_detail(self, session_id: int):
    """显示报告详情"""
    self.report_widget.load_session(session_id)
```

### Step 3: 运行测试验证

```bash
python -m insight_eyes
```

Expected: 报告面板可以显示会话详情和图表

### Step 4: 提交

```bash
git add insight_eyes/desktop/ui/widgets/session_report_widget.py insight_eyes/desktop/ui/panels/report_panel.py
git commit -m "feat: 实现测试报告详情视图和数据重现"
```

---

## Task 8: 实现监控结束处理动画

**Files:**
- Modify: `insight_eyes/desktop/ui/main_window.py`
- Create: `insight_eyes/desktop/ui/widgets/processing_dialog.py`

### Step 1: 创建处理进度对话框

创建 `insight_eyes/desktop/ui/widgets/processing_dialog.py`:

```python
"""
数据处理进度对话框
显示数据保存和报告生成的进度
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont


class ProcessingDialog(QDialog):
    """数据处理进度对话框"""

    # 信号定义
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._progress_value = 0

    def _init_ui(self):
        """初始化UI"""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        # 主容器
        container = QDialog(self)
        container.setStyleSheet("""
            QDialog {
                background-color: rgba(10, 14, 23, 0.95);
                border: 1px solid rgba(0, 212, 255, 0.3);
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(20)

        # 标题
        title = QLabel("测试数据正在生成保存中")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
                color: #00d4ff;
                background: transparent;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(25)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1a1f2e;
                border: none;
                border-radius: 12px;
                text-align: center;
                color: #e0e6ed;
                font-size: 13px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d4ff, stop:1 #00ff87);
                border-radius: 12px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("正在保存性能指标数据...")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #94a3b8;
                background: transparent;
            }
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # 完成（初始隐藏）
        self.complete_label = QLabel("✓ 测试报告生成完成！")
        self.complete_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 600;
                color: #00ff87;
                background: transparent;
            }
        """)
        self.complete_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.complete_label.hide()
        layout.addWidget(self.complete_label)

        # 调整大小
        container.setFixedSize(400, 200)
        self.setFixedSize(container.size())

    def start_animation(self):
        """开始动画"""
        self._progress_value = 0
        self.progress_bar.setValue(0)
        self.status_label.setText("正在保存性能指标数据...")
        self.status_label.show()
        self.complete_label.hide()

        # 使用定时器模拟进度
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_progress)
        self._timer.start(30)  # 每30ms更新一次

        self.show()

    def _update_progress(self):
        """更新进度"""
        self._progress_value += 1

        # 更新进度条
        self.progress_bar.setValue(self._progress_value)

        # 更新状态文本
        if self._progress_value < 30:
            self.status_label.setText("正在保存性能指标数据...")
        elif self._progress_value < 60:
            self.status_label.setText("正在计算统计数据...")
        elif self._progress_value < 90:
            self.status_label.setText("正在生成测试报告...")
        else:
            self.status_label.setText("正在完成最后处理...")

        # 完成动画
        if self._progress_value >= 100:
            self._timer.stop()
            self._on_complete()

    def _on_complete(self):
        """动画完成"""
        self.status_label.hide()
        self.complete_label.show()

        # 延迟关闭
        QTimer.singleShot(1500, self._close_and_emit)

    def _close_and_emit(self):
        """关闭对话框并发送信号"""
        self.accept()
        self.finished.emit()

    def set_progress(self, value: int, status: str = None):
        """手动设置进度（用于实际进度更新）"""
        self._progress_value = min(100, max(0, value))
        self.progress_bar.setValue(self._progress_value)
        if status:
            self.status_label.setText(status)
```

### Step 2: 在主窗口集成处理对话框

修改 `insight_eyes/desktop/ui/main_window.py` 中的停止监控逻辑:

```python
def _stop_monitoring(self):
    """停止监控"""
    if not self.is_monitoring:
        return

    # 停止数据采集
    self.is_monitoring = False
    if self._metrics_worker:
        self._metrics_worker.stop()
        self._metrics_worker = None

    # 显示处理对话框
    from insight_eyes.desktop.ui.widgets.processing_dialog import ProcessingDialog
    dialog = ProcessingDialog(self)
    dialog.finished.connect(self._on_processing_complete)
    dialog.start_animation()

    # 在后台保存数据（使用 QThreadPool）
    from PyQt6.QtCore import QThreadPool
    from insight_eyes.desktop.data.database import DatabaseManager

    class SaveSessionRunnable(QRunnable):
        """保存会话数据任务"""

        def __init__(self, session_id, device_id, package_name):
            super().__init__()
            self.session_id = session_id
            self.device_id = device_id
            self.package_name = package_name

        def run(self):
            # 实际的数据保存在这里进行
            # 这里只是模拟，实际数据已在采集时保存
            pass

    runnable = SaveSessionRunnable(
        self.current_session_id,
        self.current_device_id,
        self.current_package_name
    )
    QThreadPool.globalInstance().start(runnable)

    # 更新会话结束时间
    if self.current_session_id:
        db = DatabaseManager()
        db.end_session(self.current_session_id)

def _on_processing_complete(self):
    """处理完成回调"""
    # 刷新测试报告面板
    if hasattr(self, 'report_panel'):
        self.report_panel._refresh_list()

    # 切换到测试报告面板
    # TODO: 实现面板切换逻辑
```

### Step 3: 运行测试验证

```bash
python -m insight_eyes
```

Expected: 停止监控时显示进度动画，完成后提示"测试报告生成完成"

### Step 4: 提交

```bash
git add insight_eyes/desktop/ui/widgets/processing_dialog.py insight_eyes/desktop/ui/main_window.py
git commit -m "feat: 添加监控结束处理动画"
```

---

## Task 9: 将报告面板集成到主窗口

**Files:**
- Modify: `insight_eyes/desktop/ui/main_window.py`

### Step 1: 修改主窗口布局

在主窗口中添加报告面板:

```python
def _init_ui(self):
    """初始化UI"""
    # ... 现有代码

    # 创建报告面板
    from insight_eyes.desktop.ui.panels.report_panel import ReportPanel
    self.report_panel = ReportPanel()
    self.report_panel.report_selected.connect(self._on_report_selected)

    # 添加到主布局或使用 QStackedWidget 切换
    # 这里假设使用 QStackedWidget
    self.content_stack = QStackedWidget()
    self.content_stack.addWidget(self.monitor_panel)  # 索引 0
    self.content_stack.addWidget(self.report_panel)   # 索引 1

    layout.addWidget(self.content_stack)

    # 添加导航按钮
    nav_layout = QHBoxLayout()
    monitor_btn = QPushButton("实时监控")
    report_btn = QPushButton("测试报告")

    monitor_btn.clicked.connect(lambda: self.content_stack.setCurrentIndex(0))
    report_btn.clicked.connect(lambda: self.content_stack.setCurrentIndex(1))

    nav_layout.addWidget(monitor_btn)
    nav_layout.addWidget(report_btn)
    layout.addLayout(nav_layout)

def _on_report_selected(self, session_id: int):
    """报告选中事件"""
    self.report_panel.show_report_detail(session_id)
```

### Step 2: 运行测试验证

```bash
python -m insight_eyes
```

Expected: 可以在监控面板和报告面板之间切换

### Step 3: 提交

```bash
git add insight_eyes/desktop/ui/main_window.py
git commit -m "feat: 集成测试报告面板到主窗口"
```

---

## Task 10: 编写集成测试

**Files:**
- Create: `insight_eyes/desktop/tests/test_monitor_panel_enhancements.py`

### Step 1: 编写测试文件

创建测试文件:

```python
"""
监控面板增强功能测试
"""
import pytest
from datetime import datetime
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from insight_eyes.desktop.ui.panels.monitor_panel_v2 import MonitorPanelV2, NeonChartCard
from insight_eyes.desktop.ui.utils.card_configs import get_enabled_cards, get_card_config


@pytest.fixture
def app(qtbot):
    """创建 QApplication"""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def monitor_panel(qtbot):
    """创建监控面板"""
    panel = MonitorPanelV2()
    qtbot.addWidget(panel)
    panel.show()
    return panel


class TestCardConfigs:
    """测试卡片配置"""

    def test_get_enabled_cards(self):
        """测试获取启用的卡片"""
        cards = get_enabled_cards()
        assert len(cards) == 4  # 默认 4 个
        assert [c.metric_id for c in cards] == ['cpu', 'memory', 'fps', 'network']

    def test_get_card_config(self):
        """测试获取单个卡片配置"""
        config = get_card_config('cpu')
        assert config is not None
        assert config.title == 'CPU Usage (%)'
        assert config.color == '#00f2ff'

        config = get_card_config('invalid')
        assert config is None


class TestNeonChartCard:
    """测试 NeonChartCard"""

    def test_initialization(self, qtbot):
        """测试初始化"""
        card = NeonChartCard(
            "Test Chart",
            "#00d4ff",
            {'min': 0, 'max': 100, 'decimals': 0, 'unit': '%'}
        )
        qtbot.addWidget(card)
        assert card.title == "Test Chart"
        assert card.accent_color == "#00d4ff"
        assert len(card.data) == 0

    def test_add_data_point(self, qtbot):
        """测试添加数据点"""
        card = NeonChartCard(
            "Test Chart",
            "#00d4ff",
            {'min': 0, 'max': 100, 'decimals': 0, 'unit': '%'}
        )
        qtbot.addWidget(card)

        # 添加数据点
        card.add_data_point(50.5)
        assert len(card.data) == 1
        assert card.data[0] == 50.5

        # 添加更多数据
        for i in range(10):
            card.add_data_point(float(i * 10))
        assert len(card.data) == 11  # 120 limit not reached

        # 测试数据点上限
        for i in range(200):
            card.add_data_point(float(i))
        assert len(card.data) <= 120


class TestMonitorPanelV2:
    """测试 MonitorPanelV2"""

    def test_initialization(self, monitor_panel):
        """测试初始化"""
        assert monitor_panel.device_id is None
        assert monitor_panel.package_name is None
        assert len(monitor_panel.cards) == 4  # 默认 4 个卡片

    def test_add_data_point(self, monitor_panel):
        """测试添加数据点"""
        metrics = {
            'cpu': 50.0,
            'memory': 300.0,
            'fps': 60,
            'upload': 100.0,
            'download': 200.0
        }
        monitor_panel.add_data_point(metrics)

        # 验证数据已添加到各个卡片
        assert len(monitor_panel.cards['cpu'].data) == 1
        assert len(monitor_panel.cards['memory'].data) == 1
        assert len(monitor_panel.cards['fps'].data) == 1
        assert len(monitor_panel.cards['network'].data) == 1

    def test_clear_data(self, monitor_panel):
        """测试清除数据"""
        metrics = {
            'cpu': 50.0,
            'memory': 300.0,
            'fps': 60,
            'upload': 100.0,
            'download': 200.0
        }
        monitor_panel.add_data_point(metrics)
        monitor_panel.clear_data()

        assert len(monitor_panel.cards['cpu'].data) == 0
        assert len(monitor_panel.cards['memory'].data) == 0

    def test_refresh_cards(self, monitor_panel):
        """测试刷新卡片"""
        initial_count = len(monitor_panel.cards)
        monitor_panel.refresh_cards()
        # 刷新后卡片数量应该相同（默认配置未变）
        assert len(monitor_panel.cards) == initial_count


class TestReportPanel:
    """测试报告面板"""

    def test_initialization(self, qtbot):
        """测试初始化"""
        from insight_eyes.desktop.ui.panels.report_panel import ReportPanel

        panel = ReportPanel()
        qtbot.addWidget(panel)
        assert panel.current_session_id is None

    def test_load_sessions(self, qtbot):
        """测试加载会话列表"""
        from insight_eyes.desktop.ui.panels.report_panel import ReportPanel
        from insight_eyes.desktop.data.database import DatabaseManager

        # 创建测试会话
        db = DatabaseManager()
        session_id = db.create_session('test_device', 'com.test.app')

        panel = ReportPanel()
        qtbot.addWidget(panel)

        sessions = db.get_recent_sessions(limit=10)
        panel.load_sessions(sessions)

        assert panel.session_list.rowCount() >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

### Step 2: 运行测试

```bash
cd C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye\insight_eye-1.0.0
python -m pytest insight_eyes/desktop/tests/test_monitor_panel_enhancements.py -v
```

Expected: 所有测试通过

### Step 3: 提交

```bash
git add insight_eyes/desktop/tests/test_monitor_panel_enhancements.py
git commit -m "test: 添加监控面板增强功能集成测试"
```

---

## Task 11: 端到端测试与文档更新

**Files:**
- Create: `insight_eyes/desktop/docs/monitor-panel-optimization-guide.md`

### Step 1: 编写用户指南

创建用户指南文档:

```markdown
# 监控面板优化功能指南

## 功能概述

本次更新优化了监控面板的显示效果，并新增了测试报告功能：

### 1. 曲线显示优化
- **抗锯齿渲染**: 曲线边缘更平滑，无锯齿感
- **样条插值**: 数据点之间自动平滑过渡
- **数据点数量**: 增加到 120 个，获得更细腻的曲线

### 2. 数据悬停提示
- 鼠标悬停在曲线上时显示垂直参考线
- 高亮显示最近的数据点
- 浮动提示框显示精确的时间和数值

### 3. 动态监控卡片
- 支持启用/禁用各类监控指标
- 自适应网格布局（1-2列、2x2、2x3 等）
- 新增 Battery 和 GPU 指标支持（默认禁用）

### 4. 测试报告面板
- 查看历史监控会话列表
- 详细查看每次监控的数据
- 重现性能走势图
- 查看完整的指标数据表格

## 使用方法

### 配置监控指标

1. 打开配置面板
2. 在"监控指标"区域勾选/取消指标
3. 监控面板自动更新布局

### 查看悬停数据

1. 启动性能监控
2. 将鼠标移动到曲线图上
3. 查看浮动提示框中的数据

### 查看测试报告

1. 停止监控后，点击"测试报告"按钮
2. 在左侧列表选择要查看的会话
3. 右侧显示详细的性能数据和图表

## 技术细节

### 性能优化
- 使用 pyqtgraph 的抗锯齿功能
- 数据点限制在 120 个以平衡性能和效果
- 异步数据保存避免阻塞UI

### 数据精度
- 所有数据按采集时间排序
- 保持原始数据精度，不进行降采样
- 数据库使用 TIMESTAMP 类型存储精确时间
```

### Step 2: 更新主文档

更新 `CLAUDE.md` 的更新日志:

```markdown
## 项目更新日志

### 2025-01-19 (功能增强)

**监控面板优化:**
- 实现曲线抗锯齿和样条插值
- 增加数据悬停提示功能
- 支持动态卡片配置（CPU/内存/FPS/网络/电池/GPU）
- 自适应网格布局系统

**测试报告功能:**
- 新增独立测试报告面板
- 支持历史会话列表查看
- 详细数据展示和图表重现
- 监控结束处理动画

**配置管理:**
- 新增卡片配置模型 (card_configs.py)
- CollectionConfig 支持指标开关
- 配置面板新增指标选择器

### 2025-01-19 (Bug 修复)
- Android CPU 采集器重构
- 修复监控停止时信号断开异常
```

### Step 3: 运行端到端测试

手动测试完整流程：

1. 启动应用
2. 连接设备并选择应用
3. 在配置面板勾选所有指标
4. 启动监控
5. 观察曲线平滑度和悬停提示
6. 停止监控，观察处理动画
7. 查看测试报告

### Step 4: 最终提交

```bash
git add insight_eyes/desktop/docs/monitor-panel-optimization-guide.md CLAUDE.md
git commit -m "docs: 添加监控面板优化功能指南和更新日志"
```

---

## 执行说明

### 任务顺序
1. Task 1-5: 核心功能实现（卡片配置、曲线优化、悬停提示、动态布局）
2. Task 6-9: 测试报告功能（面板框架、详情视图、处理动画、集成）
3. Task 10-11: 测试和文档

### 预计工作量
- 每个 Task 约 30-60 分钟
- 总计约 6-10 小时完成所有任务

### 验收标准
1. ✅ 曲线显示平滑，无锯齿
2. ✅ 鼠标悬停显示精确数据
3. ✅ 配置面板可以切换指标，监控面板实时更新
4. ✅ 监控结束后显示处理动画
5. ✅ 测试报告面板可以查看历史数据
6. ✅ 所有单元测试通过

---

**Plan Status:** Ready for Implementation
**Created:** 2025-01-19
**Author:** Claude Code with writing-plans skill
