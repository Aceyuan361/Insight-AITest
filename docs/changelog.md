# 更新日志

**当前版本**: v1.0.1

## 最近更新

### 2025-01-23
- **fix**: 修复 iOS 数据处理核心问题
  - CPU 聚合只累加目标进程数据，而非所有系统进程（从 0.35% 修正为 6-8%）
  - 添加上次有效值缓存机制，避免无数据时曲线出现 0 值跳变
- **fix**: 修复停止监控后程序未响应问题（移除阻塞的 join 调用）
- **fix**: 修复设备下拉列表重复问题（添加去重逻辑）
- **fix**: 添加 iOS 启动前进程存在性检查，未运行的应用会提示用户
- **refactor**: 实现 iOSDeviceAdapter 采集方法（collect_cpu, collect_memory）

### 2025-01-22
- **fix**: 移除 main_window.py 中硬编码的超时值
- **fix**: 增加 iOS sysmon 采集超时时间至 8 秒
- **fix**: 修复 Bundle ID 应用名提取逻辑，正确处理 .com 等常见 TLD 后缀
- **fix**: 修复 SysmonHelper parse_memory_usage 变量名错误
- **debug**: 添加 SysmonHelper 详细 debug 日志

### 2025-01-21
- **feat**: 添加 py-ios-device 降级方案用于 iOS 性能采集
- **feat**: 实现 iOS 真实性能数据采集（CPU/Memory/Energy）
- **fix**: iOS 平台值大小写不匹配数据库约束
- **fix**: iOS 监控跳过运行状态检查，增强日志输出

### 2025-01-20
- **docs**: 更新 CLAUDE.md 反映 iOS 监控支持

## 版本历史

### v1.0.1 (2025-01-23)
**iOS 监控核心增强版本**

#### 新增功能
- **iOS 流式监听架构**：实现 SysmonStreamService 和 MetricsThrottle，解决 sysmon 数据推送频率不固定问题
- **iOS 进程过滤**：CPU 数据聚合只累加目标进程数据，从 0.35% 修正为 6-8%
- **平滑处理机制**：添加上次有效值缓存，避免无数据时曲线出现 0 值跳变
- **iOS 应用枚举**：实现 IOSAppEnumerator，支持获取已安装应用列表
- **iOS 会话监控**：实现 IOSSessionMonitor，协调各采集器的数据采集

#### Bug 修复
- 修复停止监控后程序未响应问题（移除阻塞的 join 调用）
- 修复设备下拉列表重复问题（添加去重逻辑）
- 修复 Bundle ID 应用名提取逻辑，正确处理 .com 等常见 TLD 后缀
- 修复 SysmonHelper parse_memory_usage 变量名错误
- 修复 iOS 平台值大小写不匹配数据库约束
- 移除 main_window.py 中硬编码的超时值

#### 性能优化
- 增加 iOS sysmon 采集超时时间至 8 秒
- 添加 iOS 启动前进程存在性检查
- 实现 iOSDeviceAdapter 采集方法（collect_cpu, collect_memory）

#### 文档更新
- 重构 CLAUDE.md 并创建分层文档结构
- 更新所有专题文档以反映 iOS 平台支持

### v1.0.0 (2025-01-20)
**初始版本发布**

#### 核心功能
- 支持 Android 性能监控（CPU/Memory/FPS/Network/Battery）
- 支持 iOS 基础性能监控（CPU/Memory/Battery/Energy）
- PyQt6 桌面 GUI 应用（赛博朋克霓虹风格）
- 数据导出功能（CSV/JSON/Excel/Markdown）
- 设备管理和应用枚举
- 实时图表监控
- 数据库持久化存储
