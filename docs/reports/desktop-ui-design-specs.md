# 桌面版UI设计规范 - 完整提取

**来源**: `insight_eyes/desktop/ui/panels/monitor_panel_v2.py`
**日期**: 2026-01-30
**目标**: 1:1 复刻到 Web 版

---

## 一、颜色规范 (DesignTokens)

### 背景色
| 元素 | 颜色值 | 说明 |
|------|--------|------|
| 主背景 | `#0a0a0a` | 整体页面背景 |
| 卡片背景 | `#141414` | 图表卡片背景 |

### 文字色
| 元素 | 颜色值 | 说明 |
|------|--------|------|
| 主文字 | `#ffffff` | 标题、主要数值 |
| 次要文字 | `#aaaaaa` | 统计信息、提示 |

### 霓虹主题色
| 指标 | 颜色值 | 用途 |
|------|--------|------|
| CPU | `#00f2ff` | 青色 - CPU卡片边框和图表 |
| Memory | `#7000ff` | 紫色 - 内存卡片边框和图表 |
| FPS | `#ffb400` | 橙色 - FPS卡片边框和图表 |
| Network Upload | `#00ff87` | 绿色 - 上传卡片边框和图表 |
| Network Download | `#0062ff` | 蓝色 - 下载卡片边框和图表 |

---

## 二、尺寸规范

### 窗口尺寸
| 属性 | 值 |
|------|-----|
| 最小宽度 | 1000px |
| 最小高度 | 600px |

### 卡片尺寸
| 属性 | 值 |
|------|-----|
| 最小高度 | 180px |
| 内边距 | 15px |
| 圆角 | 12px |
| 顶部边框 | 2px (霓虹色) |
| 其他边框 | 1px solid rgba(255,255,255,0.05) |

### 网格布局
| 属性 | 值 |
|------|-----|
| 水平间距 | 15px |
| 垂直间距 | 12px |
| 布局 | 2列固定 (最多6张卡片，2x3) |

### 图表网格边距
| 属性 | 值 |
|------|-----|
| 顶部 | 35px |
| 左侧 | 55px |
| 右侧 | 20px |
| 底部 | 30px |

---

## 三、字体规范

### 主标题 "REAL-TIME SYSTEM MONITOR"
```css
font-size: 1.2rem;
font-weight: 600;
color: #ffffff;
text-align: center;
padding: 0px 10px;
letter-spacing: 2px;
text-transform: uppercase;
```

### 卡片标题
```css
font-size: 1.1rem;
font-weight: 500;
color: #ffffff;
```

### 统计信息
```css
font-size: 0.85rem;
font-family: 'Roboto Mono', monospace;
color: {accent_color};  /* 与指标对应的霓虹色 */
text-align: right;
```

### 当前值（大号数字）
```css
font-size: 4rem;
font-weight: bold;
color: {accent_color};
```

### 轴标签
```css
font-size: 11px;
font-family: Arial;
color: #888;
```

---

## 四、图表样式

### 网格线
```css
show: true;
alpha: 0.08;  /* 透明度 */
```

### 曲线
```css
width: 2.5px;
color: {accent_color};
smooth: true;     /* 平滑曲线 */
antialias: true;  /* 抗锯齿 */
```

### 渐变填充
```css
color: {accent_color};
alpha: 35%;  /* 0.35 * 255 */
```

### 悬停提示
- 垂直线：虚线，`#444`，1px
- 数据点：12px，霓虹色边框和填充
- 提示框：显示时间、值、单位

---

## 五、布局结构

```
MonitorPanelV2 (QWidget)
├── QVBoxLayout (主容器)
│   ├── margin: 20px 5px 20px 10px
│   ├── spacing: 8px
│   │
│   ├── 标题 "REAL-TIME SYSTEM MONITOR"
│   │   └── 样式: 居中, 大写, 2px字间距
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

---

## 六、卡片内部结构 (NeonChartCard)

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
│       ├── 网格线: alpha=0.08
│       ├── 曲线: width=2.5px, 霓虹色
│       ├── 填充: 渐变, alpha=35%
│       └── 悬停交互
```

---

## 七、指标配置 (ALL_METRIC_CARDS)

| metric_id | title | color | y_min | y_max | y_width | decimals | unit | priority |
|-----------|-------|-------|-------|-------|---------|----------|------|----------|
| cpu | CPU Usage (%) | #00f2ff | 0 | 100 | 55 | 0 | % | 1 |
| memory | Memory Usage (MB) | #7000ff | 0 | null | 65 | 0 | MB | 2 |
| fps | Frame Rate (FPS) | #ffb400 | null | null | 55 | 0 | F | 3 |
| network_up | Network Upload (KB/s) | #00ff87 | 0 | null | 65 | 1 | KB/s | 4 |
| network_down | Network Download (KB/s) | #0062ff | 0 | null | 65 | 1 | KB/s | 5 |
| gpu | GPU Usage (%) | #ff006e | 0 | 100 | 55 | 0 | % | 6 (禁用) |

---

## 八、Web版复刻清单

### 阶段1: 基础布局
- [x] 主标题 "REAL-TIME SYSTEM MONITOR" (已添加)
- [x] 2x2网格布局 (已实现)
- [x] 水平间距 15px (已修复)
- [x] 垂直间距 12px (已修复)
- [x] 卡片圆角 12px (已修复)
- [x] 卡片内边距 15px (已修复)

### 阶段2: 卡片样式
- [ ] 卡片背景色 #141414
- [ ] 霓虹边框 2px (顶部)
- [ ] 其他边框 1px solid rgba(255,255,255,0.05)
- [ ] 卡片最小高度 180px

### 阶段3: 字体样式
- [ ] 主标题字体 (1.2rem, 600, 2px字间距, 大写)
- [ ] 卡片标题字体 (1.1rem, 500, #ffffff)
- [ ] 统计信息字体 (0.85rem, Roboto Mono, 霓虹色)
- [ ] 当前值字体 (4rem, bold, 霓虹色)

### 阶段4: 图表样式
- [ ] ECharts网格配置 (top: 35, left: 55, right: 20, bottom: 30)
- [ ] 曲线宽度 2.5px
- [ ] 抗锯齿启用
- [ ] 渐变填充 alpha=35%
- [ ] 网格线 alpha=0.08

### 阶段5: 交互功能
- [ ] 悬停提示框
- [ ] 垂直指示线
- [ ] 数据点标记

---

**注意**：
1. Web版当前缺少 **大号当前值显示**（桌面版有 4rem 的当前值）
2. Web版统计信息格式为 "最大: X | 平均: Y"，桌面版为 "Max: X | Min: Y | Avg: Z"
3. Web版图表渲染需要确保容器有明确高度
