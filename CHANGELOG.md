# Changelog

All notable changes to the Insight Eye project will be documented in this file.

## [1.0.3] - 2025-02-04

### 性能优化
- **测试报告页性能优化**: 会话列表加载时间从 7-8 秒优化至 <1 秒
  - 后端添加设备缓存机制（30秒 TTL）避免频繁 ADB 扫描
  - 前端实现延迟加载设备信息
  - 修改文件: `web/api/devices.py`, `web-frontend/src/components/widgets/SessionList.tsx`

### Bug 修复
- **应用名称显示问题**: 修复监控页面应用名称显示为 "app" 而非友好名称的问题
  - 添加 `getAppNameFromList` 函数从应用列表获取真正的友好名称
  - 修改文件: `web-frontend/src/components/panels/DeviceSelectionPanel.tsx`

- **监控面板统计数据重复显示**: 删除 `RealTimeChart` 中的重复统计数据显示
  - 移除统计动画状态变量和显示区域
  - 统计数据现在仅在 `NeonChartCard` 中显示一次
  - 修改文件: `web-frontend/src/components/charts/RealTimeChart.tsx`

- **告警系统调试**: 添加告警检测调试日志并优化阈值
  - 降低告警阈值以便更容易触发测试
  - 添加详细的调试日志用于追踪告警检测和保存
  - 修改文件: `core/device_manager.py`

  阈值调整:
  - FPS: 30 → 50
  - Memory: 500MB → 100MB
  - CPU: 80% → 50%
  - Temperature: 45°C → 35°C

### 数据库变更
- **sessions 表**: 添加 `app_name` 字段存储应用友好名称
- **alerts 表**: 告警系统已实现（包含 alert_type, metric_name, current_value, threshold_value, severity, description 等字段）

### 已知问题
- 告警系统需要进一步测试验证是否正常触发
- Context 使用优化需要持续关注

---

## [1.0.2] - 之前版本
- 初始 Web 版本实现
- 设备发现与连接功能完成
- 实时监控功能实现
- 测试报告页实现
