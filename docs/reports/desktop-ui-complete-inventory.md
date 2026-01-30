# 桌面版UI完整元素清单

**日期**: 2026-01-30
**目标**: 1:1 复刻到 Web 版
**来源**: `.worktrees/1.0.3/insight_eyes/desktop/ui/`

---

## 目录
1. [整体布局结构](#一整体布局结构)
2. [主窗口 (MainWindow)](#二主窗口-mainwindow)
3. [设备选择面板 (DeviceSelectionPanel)](#三设备选择面板-deviceselectionpanel)
4. [监控面板 (MonitorPanelV2)](#四监控面板-monitorpanelv2)
5. [配置面板 (ConfigPanel)](#五配置面板-configpanel)
6. [图表卡片 (NeonChartCard)](#六图表卡片-neonchartcard)
7. [悬停提示 (ChartTooltip)](#七悬停提示-charttooltip)
8. [完整样式规范](#八完整样式规范)

---

## 一、整体布局结构

### 1.1 窗口层级

```
MainWindow (QMainWindow)
├── MenuBar (菜单栏)
│   ├── 文件(&F)
│   ├── 配置(&C)
│   ├── 工具(&T)
│   └── 帮助(&H)
│
├── NavigationBar (导航栏)
│   ├── 实时监控 (QPushButton)
│   └── 测试报告 (QPushButton)
│
├── QStackedWidget (视图切换)
│   ├── 监控视图 (QWidget)
│   │   └── QSplitter (分割面板 20:60:20)
│   │       ├── DeviceSelectionPanel (左侧)
│   │       ├── MonitorPanelV2 (中间)
│   │       └── ConfigPanel (右侧)
│   └── 报告视图 (ReportPanel)
│
└── StatusBar (状态栏)
```

### 1.2 分割面板比例

| 面板 | 初始宽度 | 比例 | 可调整 |
|------|---------|------|--------|
| DeviceSelectionPanel | 280px | 20% | 否 |
| MonitorPanelV2 | 840px | 60% | 是 |
| ConfigPanel | 280px | 20% | 否 |

---

## 二、主窗口 (MainWindow)

### 2.1 窗口尺寸

```python
min_width = 1400px  # 最小宽度
min_height = 900px  # 最小高度
window_width = min(1600, int(screen_width * 0.85))
window_height = min(1000, int(screen_height * 0.85))
```

### 2.2 导航栏样式

**位置**: 顶部
**布局**: QHBoxLayout
**边距**: `ContentsMargins(10, 10, 10, 10)`
**间距**: `Spacing(10)`

#### 导航按钮样式

```css
QPushButton {
    background-color: #121824;
    color: #e0e6ed;
    border: 1px solid #1a1f2e;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    min-width: 120px;
}

QPushButton:hover {
    background-color: #1a1f2e;
    border-color: #00d4ff;
    color: #00d4ff;
}

QPushButton:checked {
    background-color: #00d4ff;
    color: #0a0e17;
    border-color: #00d4ff;
}
```

### 2.3 分割面板样式

```css
QSplitter::handle {
    background-color: #1a1f2e;
}

QSplitter::handle:hover {
    background-color: #00d4ff;
}

QSplitter::handle:horizontal {
    width: 2px;
}
```

---

## 三、设备选择面板 (DeviceSelectionPanel)

### 3.1 布局结构

```
DeviceSelectionPanel (QWidget)
├── QVBoxLayout
│   ├── margin: 12px (四周)
│   ├── spacing: 16px
│   │
│   ├── 标题 "监控目标"
│   ├── 设备选择区
│   │   ├── 标签 "设备"
│   │   └── 下拉框 (QComboBox)
│   │
│   ├── 应用选择区
│   │   ├── 标签 "应用"
│   │   └── 下拉框 (QComboBox, 可搜索)
│   │
│   ├── 当前目标显示 (QFrame)
│   │   ├── 标签 "当前目标"
│   │   ├── 设备显示
│   │   └── 应用显示
│   │
│   ├── 控制按钮区 (QHBoxLayout)
│   │   ├── 开始监控按钮
│   │   └── 刷新设备按钮
│   │
│   ├── 状态显示 "● 未监控"
│   │
│   ├── 电池信息显示 (QFrame)
│   │   ├── 标题 "电池信息"
│   │   ├── 电量
│   │   ├── 温度
│   │   └── 容量
│   │
│   └── Stretch (弹性空间)
```

### 3.2 标题样式

```css
font-size: 16pt;
font-weight: 700;
color: #00d4ff;
padding: 4px 0px;
```

### 3.3 标签样式

```css
font-size: 11pt;
font-weight: 600;
color: #94a3b8;
```

### 3.4 下拉框样式

```css
QComboBox {
    background-color: #121824;
    color: #e0e6ed;
    border: 1px solid #1a1f2e;
    border-radius: 6px;
    padding: 10px 12px;
    font-size: 10pt;
}

QComboBox:hover {
    border-color: #00d4ff;
}

QComboBox:focus {
    border-color: #00d4ff;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #7dd3fc;
    margin-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #121824;
    border: 1px solid #1a1f2e;
    selection-background-color: #00d4ff;
    selection-color: #0a0e17;
}
```

### 3.5 当前目标显示框样式

```css
QFrame {
    background-color: #0a0e17;
    border: 1px solid #1a1f2e;
    border-radius: 8px;
    padding: 12px;
}

/* 内部标题 */
QLabel[标题] {
    font-size: 11pt;
    font-weight: 600;
    color: #7dd3fc;
}

/* 信息标签 */
QLabel[信息] {
    font-size: 10pt;
    color: #94a3b8;
    padding: 4px 8px;
}

/* 选中后 */
QLabel[选中] {
    color: #e0e6ed;
}
```

### 3.6 按钮样式

#### 主要按钮 (开始监控)

```css
QPushButton {
    background-color: #00d4ff;
    color: #0a0e17;
    border: none;
    border-radius: 6px;
    padding: 12px 24px;
    font-size: 11pt;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #00b8e6;
}

QPushButton:pressed {
    background-color: #0099cc;
}

QPushButton:disabled {
    background-color: #1a1f2e;
    color: #64748b;
}
```

#### 次要按钮 (刷新设备)

```css
QPushButton {
    background-color: #1a1f2e;
    color: #e0e6ed;
    border: 1px solid #2d3748;
    border-radius: 6px;
    padding: 12px 24px;
    font-size: 11pt;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #2d3748;
    border-color: #00d4ff;
}
```

### 3.7 状态标签样式

```css
/* 未监控 */
font-size: 10pt;
color: #64748b;
padding: 8px;
background-color: #0a0e17;
border-radius: 6px;

/* 监控中 */
color: #22c55e;

/* 错误 */
color: #ef4444;
```

---

## 四、监控面板 (MonitorPanelV2)

### 4.1 布局结构

```
MonitorPanelV2 (QWidget)
├── QVBoxLayout
│   ├── margin: 20px 5px 20px 10px
│   ├── spacing: 8px
│   │
│   ├── 标题 "REAL-TIME SYSTEM MONITOR"
│   │
│   └── QGridLayout (2列网格)
│       ├── horizontalSpacing: 15px
│       ├── verticalSpacing: 12px
│       │
│       ├── [0,0] NeonChartCard (CPU)
│       ├── [0,1] NeonChartCard (Memory)
│       ├── [1,0] NeonChartCard (FPS)
│       ├── [1,1] NeonChartCard (Network Up)
│       ├── [2,0] NeonChartCard (Network Down) - 可选
│       └── [2,1] NeonChartCard (GPU) - 可选
```

### 4.2 主标题样式

```css
font-size: 1.2rem;
font-weight: 600;
color: #ffffff;
text-align: center;
padding: 0px 10px;
letter-spacing: 2px;
text-transform: uppercase;
```

### 4.3 背景色

```css
QWidget {
    background-color: #0a0a0a;
}
```

---

## 五、配置面板 (ConfigPanel)

### 5.1 布局结构

```
ConfigPanel (QWidget)
├── QScrollArea
│   └── container (QWidget)
│       └── QVBoxLayout
│           ├── margin: 8px (四周)
│           ├── spacing: 12px
│           │
│           ├── 采集配置区 (QGroupBox)
│           │   ├── 采样频率 (QComboBox)
│           │   └── 监控指标 (QGroupBox with QCheckBoxes)
│           │
│           ├── 告警阈值 (QGroupBox)
│           │   ├── FPS低于 (QSpinBox)
│           │   ├── 内存超过 (QSpinBox)
│           │   ├── CPU超过 (QSpinBox)
│           │   └── 温度超过 (QDoubleSpinBox)
│           │
│           └── 告警记录 (QGroupBox)
│               ├── QListWidget
│               └── 操作按钮 (清除全部、导出)
```

### 5.2 QGroupBox 样式

```css
QGroupBox {
    background-color: transparent;
    color: #7dd3fc;
    border: 1px solid #1a1f2e;
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 4px 8px;
    background-color: #0a0e17;
}
```

### 5.3 QSpinBox/QDoubleSpinBox 样式

```css
QSpinBox {
    background-color: #121824;
    color: #e0e6ed;
    border: 1px solid #1a1f2e;
    border-radius: 6px;
    padding: 6px;
}
```

### 5.4 QCheckBox 样式

```css
QCheckBox {
    color: #e0e6ed;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #1a1f2e;
    border-radius: 4px;
    background-color: #0a0e17;
}

QCheckBox::indicator:checked {
    background-color: {metric_color};  /* 霓虹色 */
    border-color: {metric_color};
}
```

### 5.5 QListWidget 样式

```css
QListWidget {
    background-color: #121824;
    border: 1px solid #1a1f2e;
    border-radius: 6px;
    outline: none;
}

QListWidget::item {
    padding: 8px;
    border-radius: 4px;
    border: none;
    color: #e0e6ed;
}

QListWidget::item:hover {
    background-color: #1a1f2e;
}
```

### 5.6 QScrollBar 样式

```css
QScrollBar:vertical {
    background-color: #121824;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #1a1f2e;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #2d3748;
}
```

---

## 六、图表卡片 (NeonChartCard)

### 6.1 布局结构

```
NeonChartCard (QFrame)
├── QVBoxLayout
│   ├── margin: 15px (四周)
│   ├── spacing: 10px
│   │
│   ├── 标题栏 (QHBoxLayout)
│   │   ├── 标题 "CPU Usage (%)"
│   │   └── 统计 "Max: 100% | Min: 0% | Avg: 50%"
│   │
│   └── 图表 (pyqtgraph PlotWidget)
```

### 6.2 卡片样式

```css
QFrame {
    background-color: #141414;
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.05);
    border-top: 2px solid {accent_color};
    min-height: 180px;
}
```

### 6.3 标题样式

```css
/* 卡片标题 */
font-size: 1.1rem;
font-weight: 500;
color: #ffffff;

/* 统计信息 */
font-size: 0.85rem;
font-family: 'Roboto Mono', monospace;
color: {accent_color};
text-align: right;
```

### 6.4 图表样式

```python
# 背景
background-color: #141414

# 抗锯齿
antialiasing: True

# 网格线
showGrid: True
grid.alpha: 0.08

# Y轴样式
width: 55px
tickFont: Arial, 11px
tickPen: #444, 1px
textPen: #888, 1px

# X轴样式
height: 30px
tickFont: Arial, 11px
tickPen: #444, 1px
textPen: #888, 1px

# 网格边距
contentsMargins: (55, 35, 20, 30)

# 曲线样式
pen.width: 2.5px
pen.color: {accent_color}
connect: 'all'
antialias: True

# 渐变填充
brush.color: {accent_color}
brush.alpha: 35%

# 交互
menuEnabled: False
mouseEnabled: (False, False)
```

### 6.5 悬停交互

```python
# 垂直线
vLine = InfiniteLine(
    angle=90,
    movable=False,
    pen=Pen(color='#444', width=1, style=DashLine)
)

# 数据点
hover_point = ScatterPlotItem(
    size=12,
    pen=Pen(color={accent_color}, width=2),
    brush=Brush(color={accent_color}),
)

# 提示框
tooltip = ChartTooltip()
```

---

## 七、悬停提示 (ChartTooltip)

### 7.1 样式

```css
QLabel {
    background-color: rgba(20, 20, 20, 230);
    border: 1px solid rgba(0, 212, 255, 0.5);
    border-radius: 8px;
    color: #ffffff;
    padding: 8px 12px;
    font-size: 12px;
    font-family: 'Consolas', 'Monaco', monospace;
}
```

### 7.2 内容格式

```html
<div style="line-height: 1.5;">
    <div style="color: #00d4ff; font-weight: bold; margin-bottom: 4px;">
        {title}
    </div>
    <div>时间: {time}</div>
    <div>数值: <span style="color: #00ff87; font-weight: bold;">
        {value}{unit}
    </span></div>
</div>
```

### 7.3 行为

- 显示位置：鼠标位置 + (15, 15) 偏移
- 自动隐藏：2秒后
- 透明穿透：`WA_TransparentForMouseEvents`

---

## 八、完整样式规范

### 8.1 颜色常量

| 名称 | 值 | 用途 |
|------|-----|------|
| BG_COLOR | #0a0a0a | 主背景 |
| CARD_BG | #141414 | 卡片背景 |
| TEXT_PRIMARY | #ffffff | 主文字 |
| TEXT_SECONDARY | #aaaaaa | 次要文字 |
| NEON_CPU | #00f2ff | CPU霓虹色 |
| NEON_MEMORY | #7000ff | 内存霓虹色 |
| NEON_FPS | #ffb400 | FPS霓虹色 |
| NEON_NET_UP | #00ff87 | 上传霓虹色 |
| NEON_NET_DOWN | #0062ff | 下载霓虹色 |
| ACCENT_CYAN | #00d4ff | 青色强调 |
| ACCENT_BLUE | #7dd3fc | 蓝色强调 |
| ACCENT_GREEN | #22c55e | 绿色强调 |
| ACCENT_YELLOW | #f59e0b | 黄色强调 |
| ACCENT_RED | #ef4444 | 红色强调 |
| BORDER_DEFAULT | #1a1f2e | 默认边框 |
| BG_INPUT | #121824 | 输入框背景 |
| BG_PANEL | #0a0e17 | 面板背景 |
| TEXT_LABEL | #94a3b8 | 标签文字 |
| TEXT_MUTED | #64748b | 禁用文字 |

### 8.2 尺寸常量

| 名称 | 值 |
|------|-----|
| CARD_PADDING | 15px |
| CARD_BORDER_RADIUS | 12px |
| CARD_MIN_HEIGHT | 180px |
| GRID_H_SPACING | 15px |
| GRID_V_SPACING | 12px |
| BUTTON_BORDER_RADIUS | 6px |
| INPUT_BORDER_RADIUS | 6px |
| GROUP_BOX_BORDER_RADIUS | 8px |

### 8.3 字体常量

| 元素 | 大小 | 字重 | 颜色 |
|------|------|------|------|
| 主标题 | 1.2rem | 600 | #ffffff |
| 卡片标题 | 1.1rem | 500 | #ffffff |
| 统计信息 | 0.85rem | normal | {accent_color} |
| 按钮文字 | 11pt | 600 | {context_color} |
| 标签文字 | 11pt | 600 | #94a3b8 |
| 输入框文字 | 10pt | normal | #e0e6ed |

---

## 九、Web版复刻清单

### 9.1 组件映射

| 桌面版组件 | Web版组件 | 状态 |
|-----------|----------|------|
| MainWindow | App.tsx | ✅ |
| MenuBar | - | ❌ 未实现 |
| NavigationBar | Navigation.tsx | ✅ |
| DeviceSelectionPanel | DeviceSelectionPanel.tsx | ✅ |
| MonitorPanelV2 | MonitorPanel.tsx | ✅ |
| ConfigPanel | - | ❌ 未实现 |
| NeonChartCard | NeonChartCard.tsx | ⚠️ 部分实现 |
| ChartTooltip | - | ❌ 未实现 |
| StatusBar | StatusBar.tsx | ✅ |

### 9.2 待修复项

| 项目 | 优先级 | 说明 |
|------|--------|------|
| 统计格式 | P0 | 需添加 Min，改用 "Max | Min | Avg" |
| 当前值大小 | P0 | 4rem (当前 text-4xl = 2.25rem) |
| 卡片标题大小 | P1 | 1.1rem (当前 text-sm = 0.875rem) |
| 统计字体 | P1 | Roboto Mono (当前无) |
| 图表网格边距 | P0 | right=20, bottom=30 (当前 10, 20) |
| 曲线宽度 | P1 | 2.5px (当前 2px) |
| 抗锯齿 | P1 | 未设置 |
| 渐变透明度 | P1 | 35% (当前 40%) |
| 网格线透明度 | P1 | 0.08 (当前 0.05) |
| 悬停交互 | P2 | 完全缺失 |

---

**注意**: 本文档应随桌面版UI更新而同步更新。
