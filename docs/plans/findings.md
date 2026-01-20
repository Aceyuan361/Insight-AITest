# Findings: UI优化研究笔记
<!--
  WHAT: 研究发现和技术细节记录
  WHY: 防止丢失重要信息
-->

## UI结构探索

### 主窗口布局 (main_window.py)
- 三栏布局：20% : 60% : 20%
- 分割器: `QSplitter` with `setSizes([280, 840, 280])`
- 左侧: DeviceSelectionPanel
- 中间: MonitorPanelV2
- 右侧: ConfigPanel

### 监控面板 (monitor_panel_v2.py)
- 标题位置: 447-461行，"Real-time System Monitor"
- 网格布局: 动态计算列数 (1-4列)
- 卡片类型: 6种 (CPU, Memory, FPS, Network, Battery, GPU)
- 当前布局逻辑: `_calculate_columns()` 根据卡片数量自适应

### 配置面板 (config_panel.py)
布局结构（从上到下）：
1. 采集配置区 (114-169行)
2. 阈值设置区 (171-263行)
3. **配置操作区 (265-384行)** ← 需要移除
   - 恢复默认配置
   - 导出配置
   - 导入配置
   - 自动保存开关
4. **告警记录区 (386-476行)** ← 需要扩展

### 监控指标配置 (card_configs.py)
当前指标:
- `cpu`: CPU Usage (%) - 默认启用
- `memory`: Memory Usage (MB) - 默认启用
- `fps`: Frame Rate (FPS) - 默认启用
- `network`: Network I/O (KB/s) - 默认启用
- `battery`: Battery (°C) - 默认禁用 ← 改为网络上行
- `gpu`: GPU Usage (%) - 默认禁用

## 技术要点

### 网络采集器分析
需要检查 `network_collector.py` 是否支持上行/下行分离

### 电池数据结构
从 `battery_collector.py` 获取的数据:
- `level`: 电量百分比
- `temperature`: 温度
- `current`: 电流
- `voltage`: 电压
- `capacity`: 容量

### 测试报告图表
需要查看 `report_panel.py` 中的图表实现

## 技术发现（更新）

### 网络采集器支持上行/下行分离
✅ **已确认**: `NetworkCollector.collect()` 返回：
- `upFlow`: 上行流量 (KB/s)
- `downFlow`: 下行流量 (KB/s)

### 测试报告图表组件
- **监控面板**: 使用 `NeonChartCard` (定义在 monitor_panel_v2.py)
- **测试报告**: 使用 `TrendChartWidget` (来自 trend_chart.py)
- **需要**: 确保两者样式和配置一致

### 监控面板卡片实现
`NeonChartCard` 类 (monitor_panel_v2.py 第51行):
- 霓虹主题卡片样式
- 支持悬停提示
- 使用 pyqtgraph 渲染

## 待确认问题
1. ~~网络采集器是否已分离上行/下行数据？~~ ✅ 已确认支持
2. 测试报告图表需要1:1复刻NeonChartCard样式
3. 电池信息更新频率如何？
