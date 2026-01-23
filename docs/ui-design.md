# UI 设计规范

**版本**: v1.0.1

## 设计主题

**赛博朋克霓虹** (Cyberpunk Neon)

## 配色方案

### 主色调

| 颜色名称 | 色值 | 用途 |
|---------|------|------|
| 霓虹蓝 | `#00d4ff` | 主色调、按钮、链接 |
| 深黑背景 | `#0a0a0f` | 背景色 |
| 玻璃灰 | `#1a1a2e` | 卡片背景、面板 |
| 高亮粉 | `#ff006e` | 强调色、警告 |
| 荧光绿 | `#00ff88` | 成功状态、正常值 |
| 警告黄 | `#ffcc00` | 警告状态 |
| 危险红 | `#ff3333` | 危险状态 |

### 文字颜色

| 颜色名称 | 色值 | 用途 |
|---------|------|------|
| 主文字 | `#e0e0e0` | 主要文本 |
| 次文字 | `#a0a0a0` | 次要文本 |
| 禁用文字 | `#505050` | 禁用状态 |

## 组件样式

### 按钮

```css
/* 主按钮 */
QPushButton {
    background-color: #00d4ff;
    color: #0a0a0f;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #00e5ff;
    box-shadow: 0 0 10px #00d4ff;
}

QPushButton:pressed {
    background-color: #00b8cc;
}

/* 次按钮 */
QPushButton[secondary="true"] {
    background-color: transparent;
    border: 1px solid #00d4ff;
    color: #00d4ff;
}
```

### 卡片/面板

```css
QFrame {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4e;
    border-radius: 8px;
    padding: 12px;
}
```

### 输入框

```css
QLineEdit, QTextEdit {
    background-color: #0f0f1a;
    border: 1px solid #2a2a4e;
    border-radius: 4px;
    color: #e0e0e0;
    padding: 8px;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #00d4ff;
    box-shadow: 0 0 5px #00d4ff;
}
```

### 下拉框

```css
QComboBox {
    background-color: #0f0f1a;
    border: 1px solid #2a2a4e;
    border-radius: 4px;
    color: #e0e0e0;
    padding: 6px 12px;
}

QComboBox::drop-down {
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4e;
    selection-background-color: #00d4ff;
    selection-color: #0a0a0f;
}
```

## 图表样式

### 实时图表 (pyqtgraph)

```python
import pyqtgraph as pg

# 配置图表背景
pg.setConfigOption('background', '#0a0a0f')
pg.setConfigOption('foreground', '#e0e0e0')

# 创建图表
plot = pg.PlotWidget()
plot.setBackground('#0a0a0f')

# 配置曲线
pen = pg.mkPen(color='#00d4ff', width=2)
curve = plot.plot(pen=pen)

# 配置网格
plot.showGrid(x=True, y=True, alpha=0.3)
```

### 图表颜色映射

| 指标 | 颜色 |
|-----|------|
| CPU | `#00d4ff` (霓虹蓝) |
| Memory | `#ff006e` (高亮粉) |
| FPS | `#00ff88` (荧光绿) |
| Network | `#ffcc00` (警告黄) |
| Battery | `#00ff88` (荧光绿) / `#ff3333` (危险红) |

## 玻璃态效果

```css
/* 玻璃态面板 */
QFrame[glass="true"] {
    background-color: rgba(26, 26, 46, 0.8);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(0, 212, 255, 0.2);
    border-radius: 12px;
}
```

## 霓虹发光效果

```css
/* 霓虹边框 */
QFrame[neon="true"] {
    border: 1px solid #00d4ff;
    box-shadow: 0 0 10px #00d4ff,
                0 0 20px #00d4ff,
                inset 0 0 10px rgba(0, 212, 255, 0.2);
}

/* 文字发光 */
QLabel[glow="true"] {
    color: #00d4ff;
    text-shadow: 0 0 5px #00d4ff,
                 0 0 10px #00d4ff;
}
```

## 布局间距

```python
# 边距
MARGIN_LARGE = 24   # 大边距
MARGIN_NORMAL = 16  # 普通边距
MARGIN_SMALL = 8    # 小边距
MARGIN_TINY = 4     # 微小边距

# 间距
SPACING_LARGE = 16  # 大间距
SPACING_NORMAL = 8  # 普通间距
SPACING_SMALL = 4   # 小间距
```

## 字体

```python
# 字体大小
FONT_SIZE_TITLE = 18      # 标题
FONT_SIZE_SUBTITLE = 14   # 副标题
FONT_SIZE_BODY = 12       # 正文
FONT_SIZE_CAPTION = 10    # 说明文字

# 字体粗细
FONT_WEIGHT_BOLD = 700    # 粗体
FONT_WEIGHT_NORMAL = 400  # 正常
FONT_WEIGHT_LIGHT = 300   # 细体
```

## 动画效果

### 过渡动画
```python
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

# 淡入淡出
animation = QPropertyAnimation(widget, b"windowOpacity")
animation.setDuration(300)
animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
```

### 霓虹闪烁
```python
# 定时器实现霓虹闪烁效果
timer.timeout.connect(lambda: update_neon_intensity())
```

## 响应式设计

### 断点
```python
BREAKPOINT_MOBILE = 600   # 移动设备
BREAKPOINT_TABLET = 900   # 平板设备
BREAKPOINT_DESKTOP = 1200 # 桌面设备
```

### 自适应布局
```python
# 根据窗口大小调整布局
if width < BREAKPOINT_MOBILE:
    layout.setDirection(QBoxLayout.Direction.TopToBottom)
else:
    layout.setDirection(QBoxLayout.Direction.LeftToRight)
```

## 无障碍

### 键盘导航
- 所有交互元素支持 Tab 键导航
- 快捷键明确显示在 UI 上

### 对比度
- 文字与背景对比度 >= 4.5:1
- 重要元素对比度 >= 7:1

## 样式文件

主样式文件位置：`insight_eyes/desktop/ui/styles.qss`

### 使用示例
```python
# 加载样式
with open('insight_eyes/desktop/ui/styles.qss', 'r', encoding='utf-8') as f:
    stylesheet = f.read()
    app.setStyleSheet(stylesheet)
```

## 设计原则

1. **一致性**：统一使用赛博朋克霓虹主题
2. **可读性**：确保文字清晰可读
3. **反馈**：所有交互提供即时视觉反馈
4. **层次**：使用颜色、大小、间距建立视觉层次
5. **性能**：避免过度使用动画和效果
