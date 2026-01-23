# 更新日志

## 最近更新

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

### v1.0.0
- 初始版本发布
- 支持 Android 性能监控（CPU/Memory/FPS/Network/Battery）
- 支持 iOS 基础性能监控
- PyQt6 桌面 GUI 应用
- 数据导出功能（CSV/JSON/Excel/Markdown）
