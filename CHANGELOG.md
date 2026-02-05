# Changelog

All notable changes to the Insight-Eye Web project will be documented in this file.

## [1.0.0-web] - 2025-02-05

### 🎉 首次开源发布

项目从桌面版完全分离，专注于 Web 应用开发。

### 重大变更
- **项目架构重组**: 创建独立的 1.0.0 分支专注于 Web 应用
- **代码分离**: 移除所有桌面端代码，保留核心层和平台采集器

### 重大变更 - 项目分离
- **项目架构重组**: 将 Web 应用从桌面版中完全分离
  - 创建独立的 1.0.0 分支专注于 Web 应用开发
  - 移除所有桌面端代码 (desktop/)
  - 保留核心层 (core/) 和平台采集器 (public/)

### 代码变更
- ✅ 保留模块:
  - `core/` - 核心设备管理和监控基类
  - `public/` - Android/iOS 平台采集器
  - `web/` - Web 后端服务 (FastAPI + WebSocket)
  - `web-frontend/` - Web 前端 (React + TypeScript)

- ❌ 移除模块:
  - `desktop/` - 完整桌面应用代码
  - `tests/` - 桌面端测试代码
  - `build.py` - 桌面端打包脚本
  - `insight_eye.spec` - PyInstaller 配置

### 配置更新
- 更新 `__init__.py` 版本为 `1.0.0-web`
- 更新 `__main__.py` 为 Web 服务入口
- 创建 Web 版专用 `README.md`
- 移除 PyQt6、PyInstaller 等桌面依赖

### 项目定位
- **本分支 (1.0.0)**: 专注 Web 应用，开源友好
- **main 分支**: 保留桌面应用版本

### 开源配置 ✨
- **LICENSE**: 添加 MIT 开源协议
- **贡献指南**: 完整的 CONTRIBUTING.md
- **Issue 模板**: Bug 报告、功能请求、问题提问
- **PR 模板**: 标准化的 Pull Request 模板
- **行为准则**: 贡献者契约行为准则
- **安全策略**: 漏洞报告和安全策略
- **CI/CD**: GitHub Actions 自动化测试
- **依赖更新**: Dependabot 自动更新配置

### 文档完善 📚
- **README.md**: 完整的项目说明和使用指南
- **API.md**: 详细的 API 文档
- **SUPPORT.md**: 帮助和支持文档
- **应用截图**: 添加应用界面展示截图

### Git 配置
- 更新作者邮箱为 594902674@qq.com
- 统一仓库链接为 Aceyuan361/Insight_eye

---
- 后端: FastAPI + WebSocket + SQLite
- 前端: React 18 + TypeScript + Vite + ECharts
- 平台: Android (ADB) + iOS (pymobiledevice3)

---

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
