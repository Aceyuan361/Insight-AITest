# 测试报告 UI 优化与交互式导出实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标：** 优化测试报告详情页面的 UI 布局（分屏仪表盘），并实现支持 ECharts 的交互式 HTML 报告导出功能。

**架构：** 使用 QSplitter 实现左右分屏布局（70% 图表 + 30% 统计），会话信息改为紧凑横向布局。HTML 导出使用 Jinja2 模板引擎生成，ECharts 图表通过数据转换器将数据库数据转换为 ECharts 配置。

**技术栈：** PyQt6 (QSplitter, QFrame), Jinja2, ECharts 5.4.3, SQLite

---

## 阶段一：UI 布局改造

### Task 1: 创建右侧统计面板组件

**文件：**
- Create: `insight_eyes/desktop/ui/widgets/stats_panel_widget.py`

**Step 1: 创建统计面板类**

```python
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
```

**Step 2: 提交**

```bash
cd .worktrees/report-ui-optimization
git add insight_eyes/desktop/ui/widgets/stats_panel_widget.py
git commit -m "feat: 创建统计面板组件 StatsPanelWidget

- 支持显示 FPS/CPU/内存/网络统计数据
- 支持显示告警记录列表
- 赛博朋克风格样式

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: 修改 SessionReportWidget 为分屏布局

**文件：**
- Modify: `insight_eyes/desktop/ui/widgets/session_report_widget.py:23-100`

**Step 1: 备份原文件**

```bash
cd .worktrees/report-ui-optimization
cp insight_eyes/desktop/ui/widgets/session_report_widget.py insight_eyes/desktop/ui/widgets/session_report_widget.py.bak
```

**Step 2: 修改导入语句**

在文件开头添加：
```python
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (QSplitter, QFrame, QVBoxLayout, QHBoxLayout,
                             QLabel, QScrollArea, QPushButton, QMessageBox,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QGridLayout)
from ..widgets.stats_panel_widget import StatsPanelWidget
```

**Step 3: 修改 __init__ 方法**

找到 `def __init__(self, session_id: int, parent=None):`，替换为：

```python
def __init__(self, session_id: int, parent=None):
    super().__init__(parent)
    self.session_id = session_id
    self.database = DatabaseManager()
    self.repository = MetricsRepository(self.database)

    self._setup_ui()
    self._load_session_data()
```

**Step 4: 替换 _setup_ui 方法**

找到 `def _setup_ui(self):` 方法，完整替换为：

```python
def _setup_ui(self):
    """初始化UI - 分屏布局"""
    layout = QVBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    # 紧凑会话信息栏
    self._create_session_info_bar(layout)

    # 分隔器：左侧图表 + 右侧统计
    self.splitter = QSplitter(Qt.Orientation.Horizontal)
    self.splitter.setChildrenCollapsible(False)  # 禁止折叠到0
    layout.addWidget(self.splitter)

    # 左侧：图表区域
    self.charts_scroll = QScrollArea()
    self.charts_scroll.setWidgetResizable(True)
    self.charts_scroll.setFrameShape(QFrame.Shape.NoFrame)
    self.charts_container = QWidget()
    self.charts_layout = QGridLayout(self.charts_container)
    self.charts_layout.setSpacing(16)
    self.charts_scroll.setWidget(self.charts_container)
    self.splitter.addWidget(self.charts_scroll)

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
```

**Step 5: 添加会话信息栏方法**

在类中添加：

```python
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

    self.export_btn = QPushButton("📤 导出 HTML 报告")
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

    self.delete_btn = QPushButton("🗑️ 删除会话")
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
        import json
        settings = {
            'splitter_sizes': self.splitter.sizes()
        }
        config_path = 'config/report_layout.json'
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(settings, f)
    except Exception as e:
        logger.warning(f"保存分隔线位置失败: {e}")

def _restore_splitter_state(self):
    """恢复分隔线位置"""
    try:
        config_path = 'config/report_layout.json'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                settings = json.load(f)
                sizes = settings.get('splitter_sizes')
                if sizes and len(sizes) == 2:
                    self.splitter.setSizes(sizes)
    except Exception as e:
        logger.warning(f"恢复分隔线位置失败: {e}")
```

**Step 6: 修改 _load_session_data 方法**

找到并修改：

```python
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
        device_name = device['name'] if device else '未知设备'
        start_time = session['start_time'].strftime('%Y-%m-%d %H:%M')
        end_time = session['end_time'].strftime('%H:%M') if session['end_time'] else '进行中'
        duration = self._calculate_duration(session['start_time'], session['end_time'])

        info_text = f"📱 {device_name} │ 📱 {session['package_name']} │ ⏰ {start_time}-{end_time} │ ⏱️ {duration}"
        self.session_info_label.setText(info_text)

        # 获取统计数据
        statistics = self.repository.get_statistics(self.session_id)
        self.stats_panel.update_stats(statistics)

        # 获取告警
        alerts = self.repository.get_alerts(self.session_id)
        self.stats_panel.update_alerts(alerts)

        # 加载图表（现有逻辑保持不变）
        self._load_charts()

    except Exception as e:
        logger.error(f"加载会话数据失败: {e}", exc_info=True)
        QMessageBox.critical(self, "错误", f"加载会话数据失败: {e}")

def _calculate_duration(self, start_time, end_time):
    """计算持续时间"""
    if not end_time:
        end_time = datetime.now()
    delta = end_time - start_time
    minutes = int(delta.total_seconds() / 60)
    if minutes < 60:
        return f"{minutes}分钟"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}小时{mins}分钟"
```

**Step 7: 添加导出 HTML 方法（占位）**

```python
def _export_html_report(self):
    """导出 HTML 报告"""
    QMessageBox.information(self, "开发中", "HTML 报告导出功能将在下一阶段实现")
```

**Step 8: 提交**

```bash
cd .worktrees/report-ui-optimization
git add insight_eyes/desktop/ui/widgets/session_report_widget.py
git rm insight_eyes/desktop/ui/widgets/session_report_widget.py.bak
git commit -m "refactor: SessionReportWidget 改为分屏布局

主要改动：
- 使用 QSplitter 实现左右分屏（70% 图表 + 30% 统计）
- 会话信息改为紧凑横向单行显示
- 集成 StatsPanelWidget 显示统计数据
- 支持保存/恢复分隔线位置
- 移除原有的会话信息卡片和统计表格

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: 测试 UI 布局

**Step 1: 运行应用测试**

```bash
cd .worktrees/report-ui-optimization
python -m insight_eyes.desktop.main
```

**Step 2: 手动验证**

- [ ] 打开任意测试报告
- [ ] 验证会话信息显示为单行紧凑格式
- [ ] 拖动分隔线，验证左右比例可调整
- [ ] 关闭并重新打开报告，验证分隔线位置被保存
- [ ] 验证统计数据正确显示
- [ ] 验证告警记录正确显示

**Step 3: 提交测试修复（如有）**

如有问题，修复后提交。

---

## 阶段二：HTML 导出核心功能

### Task 4: 下载并集成 ECharts

**文件：**
- Create: `insight_eyes/desktop/resources/export/echarts.min.js`

**Step 1: 创建资源目录**

```bash
cd .worktrees/report-ui-optimization
mkdir -p insight_eyes/desktop/resources/export
```

**Step 2: 下载 ECharts**

```bash
cd .worktrees/report-ui-optimization/insight_eyes/desktop/resources/export
curl -o echarts.min.js https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js
```

**Step 3: 验证下载**

```bash
cd .worktrees/report-ui-optimization
ls -lh insight_eyes/desktop/resources/export/echarts.min.js
# 预期输出：文件大小约 1MB
```

**Step 4: 提交**

```bash
cd .worktrees/report-ui-optimization
git add insight_eyes/desktop/resources/export/echarts.min.js
git commit -m "chore: 添加 ECharts 5.4.3 库文件

用于交互式 HTML 报告生成

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: 创建 ECharts 数据转换器

**文件：**
- Create: `insight_eyes/desktop/ui/charts/chart_data_builder.py`

**Step 1: 创建数据转换器**

```python
# -*- coding: utf-8 -*-
"""
ECharts 图表数据构建器
将数据库数据转换为 ECharts 配置格式
"""
from typing import List, Dict, Any
from datetime import datetime
import json
from logzero import logger


class ChartDataBuilder:
    """ECharts 图表数据构建器"""

    # 赛博朋克配色
    COLORS = {
        'fps': '#ffb400',
        'cpu': '#00d4ff',
        'cpu_system': '#00bcd4',
        'memory': '#7000ff',
        'network_up': '#00ff87',
        'network_down': '#0062ff',
        'alert': '#ef4444'
    }

    @staticmethod
    def build_chart_config(metric_type: str, timestamps: List[str],
                          data: List[float], data2: List[float] = None) -> Dict[str, Any]:
        """
        构建 ECharts 图表配置

        Args:
            metric_type: 指标类型 (fps/cpu/memory/network_up/network_down)
            timestamps: 时间戳列表
            data: 主数据系列
            data2: 次数据系列（可选，用于双曲线）

        Returns:
            ECharts 配置字典
        """
        # 计算自适应Y轴范围
        y_min, y_max = ChartDataBuilder._calculate_y_axis(data, metric_type)

        # 构建配置
        config = {
            'title': {
                'text': ChartDataBuilder._get_title(metric_type),
                'textStyle': {
                    'color': '#e0e6ed',
                    'fontSize': 14
                },
                'left': 'center',
                'top': 10
            },
            'tooltip': {
                'trigger': 'axis',
                'backgroundColor': 'rgba(10, 14, 23, 0.95)',
                'borderColor': ChartDataBuilder.COLORS.get(metric_type, '#00d4ff'),
                'borderWidth': 1,
                'textStyle': {'color': '#e0e6ed', 'fontSize': 12},
                'formatter': ChartDataBuilder._get_tooltip_formatter(metric_type)
            },
            'grid': {
                'left': '3%',
                'right': '4%',
                'bottom': '3%',
                'top': '15%',
                'containLabel': True
            },
            'xAxis': {
                'type': 'category',
                'data': timestamps,
                'axisLine': {'lineStyle': {'color': '#1a1f2e'}},
                'axisLabel': {'color': '#64748b', 'fontSize': 10}
            },
            'yAxis': {
                'type': 'value',
                'min': y_min,
                'max': y_max,
                'axisLine': {'lineStyle': {'color': '#1a1f2e'}},
                'splitLine': {'lineStyle': {'color': 'rgba(255,255,255,0.05)'}},
                'axisLabel': {'color': '#64748b', 'fontSize': 10}
            },
            'series': []
        }

        # 添加数据系列
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

        min_val = min(data)
        max_val = max(data)
        padding = (max_val - min_val) * 0.1

        if metric_type == 'fps':
            # FPS 完全自适应
            return 0, max_val + padding
        elif metric_type == 'cpu':
            # CPU 固定 0-100%
            return 0, 100
        else:
            # 内存、网络等自适应
            return 0, max_val + padding

    @staticmethod
    def _get_title(metric_type: str) -> str:
        """获取图表标题"""
        titles = {
            'fps': 'FPS 趋势',
            'cpu': 'CPU 使用率',
            'memory': '内存使用',
            'network_up': '网络上行速率',
            'network_down': '网络下行速率'
        }
        return titles.get(metric_type, metric_type)

    @staticmethod
    def _get_tooltip_formatter(metric_type: str) -> str:
        """获取提示框格式化函数"""
        if metric_type in ['network_up', 'network_down']:
            unit = 'KB/s'
        elif metric_type == 'memory':
            unit = 'MB'
        elif metric_type == 'cpu':
            unit = '%'
        else:
            unit = ''

        return f"""function(params) {{
            let result = `<div style="color:#94a3b8;font-size:12px">${{params[0].name}}</div>`;
            params.forEach(item => {{
                result += `<div style="margin-top:4px">
                    <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${{item.color}};margin-right:8px"></span>
                    <span style="color:#e0e6ed">${{item.seriesName}}</span>
                    <span style="color:${{item.color}};font-weight:bold;margin-left:10px">${{item.value}}{unit}</span>
                </div>`;
            }});
            return result;
        }}"""

    @staticmethod
    def _build_series(metric_type: str, data: List[float]) -> Dict[str, Any]:
        """构建数据系列配置"""
        color = ChartDataBuilder.COLORS.get(metric_type, '#00d4ff')

        return {
            'name': ChartDataBuilder._get_series_name(metric_type),
            'type': 'line',
            'data': data,
            'smooth': True,
            'lineStyle': {
                'color': color,
                'width': 2
            },
            'areaStyle': {
                'color': {
                    'type': 'linear',
                    'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                    'colorStops': [
                        {'offset': 0, 'color': f'{color}4D'},  # 30% opacity
                        {'offset': 1, 'color': f'{color}0D'}   # 5% opacity
                    ]
                }
            },
            'symbol': 'circle',
            'symbolSize': 4
        }

    @staticmethod
    def _get_series_name(metric_type: str) -> str:
        """获取系列名称"""
        names = {
            'fps': 'FPS',
            'cpu': '应用 CPU',
            'cpu_system': '系统 CPU',
            'memory': '内存',
            'network_up': '上行速率',
            'network_down': '下行速率'
        }
        return names.get(metric_type, metric_type)
```

**Step 2: 提交**

```bash
cd .worktrees/report-ui-optimization
git add insight_eyes/desktop/ui/charts/chart_data_builder.py
git commit -m "feat: 创建 ECharts 数据转换器

- 支持将数据库数据转换为 ECharts 配置
- 自适应 Y 轴范围计算
- 赛博朋克配色方案
- 完整的提示框格式化

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: 创建 HTML 导出器

**文件：**
- Create: `insight_eyes/desktop/data/html_exporter.py`

**Step 1: 创建 HTML 导出器类**

```python
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
        self._load_template()

    def _load_template(self):
        """加载 HTML 模板"""
        template_path = os.path.join(
            os.path.dirname(__file__),
            '../resources/export/templates/report_template.html'
        )

        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                self.template = Template(f.read())
        else:
            # 使用内嵌模板（临时方案）
            self.template = Template(self._get_default_template())

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
            alerts = self.repository.get_alerts(session_id)

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
            html_content = self.template.render(**context)

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

            # 其他图表类似...

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
    <script src="../echarts.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background-color: #0a0e17;
            color: #e0e6ed;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header {
            background-color: #121824;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            border: 1px solid #1a1f2e;
        }
        .header h1 { color: #00d4ff; margin-bottom: 16px; }
        .session-info { color: #94a3b8; font-size: 14px; }
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ title }}</h1>
            <div class="session-info">
                📱 {{ device.name if device else "未知设备" }} |
                📱 {{ session.package_name }} |
                ⏰ {{ session.start_time.strftime("%Y-%m-%d %H:%M") }}
                - {{ session.end_time.strftime("%H:%M") if session.end_time else "进行中" }}
            </div>
        </div>

        <div class="chart-grid">
            {% for chart_id, chart_config in charts.items() %}
            <div class="chart-container">
                <div id="chart-{{ chart_id }}" class="chart"></div>
            </div>
            {% endfor %}
        </div>
    </div>

    <script>
        {% for chart_id, chart_config in charts.items() %}
        (function() {
            var chart = echarts.init(document.getElementById('chart-{{ chart_id }}'));
            var option = {{ chart_config | tojson }};
            chart.setOption(option);
        })();
        {% endfor %}
    </script>
</body>
</html>'''
```

**Step 2: 提交**

```bash
cd .worktrees/report-ui-optimization
git add insight_eyes/desktop/data/html_exporter.py
git commit -m "feat: 创建 HTML 导出器

- 使用 Jinja2 模板引擎
- 集成 ECharts 图表配置
- 支持会话信息、统计数据、告警记录
- 包含默认 HTML 模板

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: 在 SessionReportWidget 中集成 HTML 导出

**文件：**
- Modify: `insight_eyes/desktop/ui/widgets/session_report_widget.py`

**Step 1: 添加导入**

在文件开头添加：
```python
from ..data.html_exporter import HtmlExporter
```

**Step 2: 替换 _export_html_report 方法**

找到并替换：

```python
def _export_html_report(self):
    """导出 HTML 报告"""
    try:
        # 选择保存路径
        from PyQt6.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "导出 HTML 报告",
            f"session_{self.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
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
            QMessageBox.information(
                self,
                "导出成功",
                f"HTML 报告已导出到:\n{filepath}\n\n是否立即打开？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            # 询问是否打开
            reply = QMessageBox.question(
                self,
                "打开报告",
                "是否立即打开报告？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                import webbrowser
                webbrowser.open(f"file:///{filepath.replace(os.sep, '/')}")
        else:
            QMessageBox.critical(self, "导出失败", "导出 HTML 报告时发生错误")

    except Exception as e:
        logger.error(f"导出 HTML 报告失败: {e}", exc_info=True)
        QMessageBox.critical(self, "导出失败", f"导出时发生错误:\n{e}")
    finally:
        self.export_btn.setEnabled(True)
        self.export_btn.setText("📤 导出 HTML 报告")
```

**Step 3: 提交**

```bash
cd .worktrees/report-ui-optimization
git add insight_eyes/desktop/ui/widgets/session_report_widget.py
git commit -m "feat: 集成 HTML 导出功能到报告面板

- 添加导出按钮点击处理
- 支持选择保存路径
- 导出成功后提示是否打开
- 完整的错误处理

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: 测试 HTML 导出

**Step 1: 运行应用**

```bash
cd .worktrees/report-ui-optimization
python -m insight_eyes.desktop.main
```

**Step 2: 手动测试**

- [ ] 打开测试报告详情
- [ ] 点击"导出 HTML 报告"按钮
- [ ] 选择保存路径并保存
- [ ] 在浏览器中打开导出的 HTML 文件
- [ ] 验证图表显示正确
- [ ] 验证图表可交互（缩放、悬停提示）
- [ ] 验证样式为赛博朋克风格

**Step 3: 提交修复（如有）**

---

## 阶段三：优化与完善

### Task 9: 创建完整的 HTML 模板文件

**文件：**
- Create: `insight_eyes/desktop/resources/export/templates/report_template.html`

**Step 1: 创建模板文件**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <script src="insight_eyes/desktop/resources/export/echarts.min.js"></script>
    <style>
        /* 赛博朋克主题样式 */
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
        .header h1 {
            color: #00d4ff;
            margin-bottom: 16px;
            font-size: 24px;
        }
        .session-info {
            color: #94a3b8;
            font-size: 14px;
            line-height: 1.6;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }
        .stat-card {
            background-color: #121824;
            border-radius: 8px;
            padding: 16px;
            border: 1px solid #1a1f2e;
        }
        .stat-label { color: #64748b; font-size: 12px; margin-bottom: 8px; }
        .stat-value {
            color: #e0e6ed;
            font-size: 24px;
            font-weight: bold;
        }
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
        .alerts-section h2 {
            color: #ef4444;
            margin-bottom: 16px;
            font-size: 18px;
        }
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
        <!-- 头部 -->
        <div class="header">
            <h1>{{ title }}</h1>
            <div class="session-info">
                📱 设备: {{ device.name if device else "未知设备" }}<br>
                📱 应用: {{ session.package_name }}<br>
                ⏰ 时间: {{ session.start_time.strftime("%Y-%m-%d %H:%M") }}
                - {{ session.end_time.strftime("%H:%M") if session.end_time else "进行中" }}<br>
                📊 采样间隔: {{ session.sample_interval }}ms
            </div>
        </div>

        <!-- 关键指标 -->
        <div class="stats-grid">
            {% if statistics.fps %}
            <div class="stat-card">
                <div class="stat-label">FPS 平均值</div>
                <div class="stat-value" style="color: #ffb400;">{{ statistics.fps.avg }}</div>
            </div>
            {% endif %}
            {% if statistics.cpu %}
            <div class="stat-card">
                <div class="stat-label">CPU 平均值</div>
                <div class="stat-value" style="color: #00d4ff;">{{ statistics.cpu.avg }}%</div>
            </div>
            {% endif %}
            {% if statistics.memory %}
            <div class="stat-card">
                <div class="stat-label">内存平均值</div>
                <div class="stat-value" style="color: #7000ff;">{{ statistics.memory.avg }}MB</div>
            </div>
            {% endif %}
        </div>

        <!-- 图表区域 -->
        <div class="chart-grid">
            {% for chart_id, chart_config in charts.items() %}
            <div class="chart-container">
                <div id="chart-{{ chart_id }}" class="chart"></div>
            </div>
            {% endfor %}
        </div>

        <!-- 告警记录 -->
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

        <!-- 页脚 -->
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
</html>
```

**Step 2: 提交**

```bash
cd .worktrees/report-ui-optimization
git add insight_eyes/desktop/resources/export/templates/report_template.html
git commit -m "feat: 添加完整的 HTML 报告模板

- 赛博朋克风格样式
- 关键指标卡片
- 响应式图表布局
- 告警记录展示

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 10: 最终测试与提交

**Step 1: 完整功能测试**

```bash
cd .worktrees/report-ui-optimization
python -m insight_eyes.desktop.main
```

**测试清单：**
- [ ] UI 分屏布局正常
- [ ] 拖动分隔线流畅
- [ ] 统计面板数据正确
- [ ] HTML 导出功能正常
- [ ] 导出的 HTML 包含所有图表
- [ ] 图表可交互（缩放、提示）
- [ ] 样式符合赛博朋克主题

**Step 2: 合并到主分支**

```bash
cd .worktrees/report-ui-optimization
# 推送到远程
git push origin feature/report-ui-optimization

# 切换到主分支并合并
cd ../..
git checkout main
git merge feature/report-ui-optimization
git push origin main
```

---

## 总结

此实现计划涵盖了：
1. ✅ UI 布局优化（分屏仪表盘）
2. ✅ 紧凑会话信息栏
3. ✅ 统计面板组件
4. ✅ HTML 交互式导出
5. ✅ ECharts 图表集成
6. ✅ 赛博朋克主题样式

预计工作量：**10 个任务，约 2-3 小时**
