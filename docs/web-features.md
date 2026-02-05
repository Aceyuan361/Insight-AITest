# Web 版功能更新日志

**版本**: v1.0.0
**发布日期**: 2026-02-05
**作者**: Aceyuan361

## v1.0.0 新增功能

### 1. 实时告警推送 ✅

**功能描述**：
监控过程中触发告警阈值时，实时推送告警通知到前端右下角的告警记录区域。

**技术实现**：
- 后端：`DeviceManager._check_and_save_alerts` 返回触发的告警列表
- 后端：`MetricsData` 模型添加 `is_alert` 和 `alert_data` 字段
- 后端：WebSocket 推送告警消息（type: "metrics", data: {is_alert: true, alert_data: {...}}）
- 前端：monitoringStore 处理告警消息并添加到 alarms 列表
- 前端：AlarmRecords 组件实时显示告警通知

**使用方法**：
1. 在配置面板设置告警阈值（FPS、内存、CPU、温度）
2. 开始监控
3. 当指标超过阈值时，右下角会自动显示告警通知

**文件修改**：
- `core/device_manager.py` - 告警检测和推送
- `core/models/metrics.py` - 告警字段
- `web-frontend/src/store/monitoringStore.ts` - 告警处理
- `components/widgets/AlarmRecords.tsx` - 告警显示

---

### 2. 应用模糊搜索 ✅

**功能描述**：
在应用选择面板添加搜索框，支持按应用名称或包名模糊搜索，解决有100个应用时查找困难的问题。

**技术实现**：
- 搜索框支持应用名称和包名匹配
- 实时过滤下拉列表
- 显示搜索结果数量统计

**使用方法**：
1. 选择设备后，在应用搜索框输入关键字
2. 下拉列表实时显示匹配的应用
3. 底部显示匹配结果数量（如：共 5 项）

**文件修改**：
- `components/panels/DeviceSelectionPanel.tsx` - 搜索框和过滤逻辑

---

### 3. GPU 监控设备限制 ✅

**功能描述**：
根据设备类型动态控制 GPU 监控的可用性：
- Android 设备：GPU 监控可选（部分设备支持）
- iOS 设备：GPU 监控不可用（显示 "iOS不支持"）

**技术实现**：
- ConfigPanel：检测设备类型，iOS 设备禁用 GPU 选项
- MonitorPanel：根据设备类型过滤 GPU 卡片
- 切换设备时自动更新 GPU 状态

**限制说明**：
- iOS 系统 DVT 通道无法获取 GPU 能耗数据
- CLI 能耗命令超时（20+ 秒），不适合实时监控
- Web 版界面会显示相应提示信息

**文件修改**：
- `components/panels/ConfigPanel.tsx` - GPU 选项动态控制
- `components/panels/MonitorPanel.tsx` - GPU 卡片过滤

---

### 4. 监控面板动态布局 ✅

**功能描述**：
监控面板支持动态布局，每行显示2个卡片，支持任意数量的监控卡片。

**技术实现**：
- 使用 `Array.from()` 动态生成行
- 每行最多2个卡片
- 支持扩展到6个或更多卡片

**修复问题**：
- 修复 Android 设备勾选 GPU 后第6个面板不显示的问题

**文件修改**：
- `components/panels/MonitorPanel.tsx` - 动态布局逻辑

---

### 5. iOS 启动延迟修复 ✅

**功能描述**：
修复 iOS 监控启动时约2秒延迟导致 CPU 和内存显示为 0 的问题。

**技术实现**：
- monitoringStore.updateMetrics 过滤初始 0 值
- 只有当有非0数据时才开始记录
- 避免曲线出现初始0值异常

**文件修改**：
- `web-frontend/src/store/monitoringStore.ts` - 数据过滤逻辑

---

### 6. 测试报告统计功能 ✅

**功能描述**：
测试报告页面右侧显示性能统计数据（最大值、最小值、平均值）。

**技术实现**：
- 后端：`DatabaseManager.get_session_statistics` 计算统计数据
- 支持 FPS、CPU、内存、网络上传/下载
- 返回最大值、最小值、平均值、中位数

**文件修改**：
- `core/database.py` - 统计计算方法
- `web-frontend/src/components/widgets/StatsPanel.tsx` - 统计显示

---

### 7. 告警阈值持久化 ✅

**功能描述**：
告警阈值配置保存到 localStorage，重启后保持用户配置。

**技术实现**：
- 前端：configManager 保存/加载告警阈值
- 前端：启动监控时从 localStorage 加载阈值
- 后端：session 级别的告警阈值存储
- 后端：使用 session 特定阈值进行告警检测

**文件修改**：
- `utils/configManager.ts` - 阈值持久化
- `store/monitoringStore.ts` - 阈值加载和应用
- `api/schemas.py` - AlertThresholds 模型
- `api/monitoring.py` - 阈值参数传递
- `core/device_manager.py` - session 级别阈值

---

### 8. 版本和作者信息 ✅

**功能描述**：
更新帮助文档中的版本和作者信息。

**信息**：
- 版本：1.0.0
- 作者：Aceyuan361

**文件修改**：
- `i18n/locales/zh-CN.ts` - 中文版本和作者
- `i18n/locales/en-US.ts` - 英文版本和作者

---

### 9. 系统支持版本更新 ✅

**功能描述**：
更新 iOS 系统支持范围。

**支持系统**：
- iOS 11.0 - 16.x
- 不支持 iOS 17+

**文件修改**：
- `i18n/locales/zh-CN.ts` - iOS 版本说明
- `i18n/locales/en-US.ts` - iOS 版本说明
- `docs/ios-monitoring.md` - 系统支持说明

---

## 服务端口

- **后端服务**: http://localhost:8001
- **前端服务**: http://localhost:80 或 http://localhost:81（80被占用时）

---

## 已知限制

### iOS 平台限制
1. **GPU 监控**：不支持（系统 API 限制）
2. **FPS 监控**：仅提供系统刷新率参考值
3. **网络流量**：仅系统级别数据
4. **系统版本**：不支持 iOS 17+

### Android 平台限制
1. **GPU 监控**：需要 root 或特定设备支持

---

## 后续计划

### 短期
- [ ] 添加更多图表类型（饼图、雷达图等）
- [ ] 支持自定义仪表板布局
- [ ] 添加数据导出功能（PDF、Excel）

### 长期
- [ ] 支持多设备同时监控
- [ ] 添加历史数据对比功能
- [ ] 支持自定义告警规则
- [ ] 添加性能趋势分析

---

## 相关文档

- [项目概述](./project-overview.md)
- [Android 监控](./android-monitoring.md)
- [iOS 监控](./ios-monitoring.md)
- [开发工作流](./dev-workflow.md)
- [API 文档](./API.md)
