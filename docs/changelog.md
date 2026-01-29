# 更新日志

**当前版本**: v1.0.3

## 最近更新

### 2025-01-29 - v1.0.3
**Phase 3: React Web 前端完成**

#### 新增功能
- **React Web 前端**: 与桌面版 1:1 对等的 Web 界面
- **霓虹主题系统**: 与桌面版完全一致的颜色方案
  - CPU 青色 (#00f2ff)
  - Memory 紫色 (#7000ff)
  - FPS 橙色 (#ffb400)
  - Network 绿色/蓝色 (#00ff87/#0062ff)
- **实时监控面板**: 2x2 响应式图表网格
  - ECharts 实时数据可视化
  - 平滑曲线和渐变填充效果
- **设备选择面板**:
  - Android/iOS 设备列表显示
  - 平台标识和在线状态
  - 应用包名配置
- **监控控制**: 启动/停止监控功能
- **会话历史**: 历史监控会话列表和详情
- **标签页切换**: 监控面板和报告面板

#### 技术栈
- React 19 + TypeScript 5.9
- Vite 7 构建工具
- ECharts 6 图表库
- Zustand 状态管理
- TailwindCSS 4 样式框架
- Axios HTTP 客户端
- WebSocket 实时通信

#### 架构改进
- **FastAPI 后端集成**: RESTful API + WebSocket
- **状态管理**: Zustand store 集成 WebSocket 实时数据
- **响应式设计**: 支持桌面和移动端
- **生产构建优化**: 代码分割和压缩

#### 部署配置
- 开发端口: 80
- API 代理: localhost:8000
- 环境变量配置

### 2025-01-29 - v1.0.2
**Phase 2: FastAPI 后端完成**

#### 新增功能
- **FastAPI Web 服务**: RESTful API 和 WebSocket 支持
- **设备管理 API**: 获取设备列表和详情
- **监控控制 API**: 启动/停止监控会话
- **会话管理 API**: 查询历史会话和详情
- **WebSocket 实时推送**: 监控数据实时更新
- **CORS 安全配置**: 环境变量控制跨域访问
- **API 文档**: Swagger UI 自动生成

#### 技术栈
- FastAPI 0.104+
- Uvicorn ASGI 服务器
- WebSocket 12.0+
- Pydantic 2.5+ 数据验证

#### 测试覆盖
- 8/8 API 集成测试通过
- WebSocket 连接测试通过
- 与核心层集成验证

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
