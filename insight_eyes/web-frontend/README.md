# Insight Eye - Web Frontend

Web-based performance monitoring dashboard for Insight Eye. Built with React + TypeScript + Vite, featuring a cyberpunk neon theme UI with real-time performance metrics visualization.

## 功能状态 (v1.0.3)

### ✅ 已完成功能

| 功能模块 | 状态 | 说明 |
|---------|------|------|
| 设备选择面板 | ✅ | Android/iOS设备扫描、应用枚举、运行状态检测 |
| 监控面板 | ✅ | 2x2图表网格布局、实时数据更新、霓虹主题 |
| 报告面板 | ⚠️ | 会话历史列表、状态显示、时间格式化（缺失高级管理功能） |
| 配置面板 | ⚠️ | 采集设置、阈值设置（缺失导入/导出） |
| iOS进程检测 | ✅ | SysmonService集成，支持应用运行状态检测 |
| WebSocket实时推送 | ✅ | 监控数据实时更新 |

### 📊 Web端 vs 桌面端功能对比

Web端已实现桌面端 **85%** 的核心功能。主要缺失：
- 数据导出（Excel/CSV）
- 会话管理高级功能（删除、批量删除）
- 配置导入/导出
- 设备断线重连

详见 `docs/reports/web-desktop-comprehensive-analysis.md`

## Prerequisites

- **Node.js**: 22+ (Check with `node --version`)
- **npm**: 10+ (Check with `npm --version`)
- **Backend**: FastAPI server running on http://localhost:8000
- **Python**: 3.11+ with virtual environment

## Installation

1. 安装依赖:
```bash
cd insight_eyes/web-frontend
npm install
```

2. 确保后端服务运行:
```bash
cd .worktrees/1.0.3
venv/Scripts/uvicorn.exe insight_eyes.web.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Development

启动开发服务器:
```bash
npm run dev
```

应用将在 http://localhost:80 可用

开发服务器代理:
- API 请求 (`/api/*`) → http://localhost:8000
- WebSocket 连接 (`/ws/*`) → ws://localhost:8000

## Build

生产构建:
```bash
npm run build
```

构建文件将输出到 `dist/` 目录

预览生产构建:
```bash
npm run preview
```

## Project Structure

```
web-frontend/
├── src/
│   ├── components/
│   │   ├── charts/          # ECharts 图表组件
│   │   │   ├── RealTimeChart.tsx    # 实时图表
│   │   │   └── NeonChartCard.tsx    # 霓虹风格卡片
│   │   ├── layout/          # 布局组件
│   │   │   ├── MainWindow.tsx       # 主窗口
│   │   │   ├── MenuBar.tsx          # 顶部菜单栏
│   │   │   └── StatusBar.tsx        # 底部状态栏
│   │   ├── panels/          # 面板组件
│   │   │   ├── DeviceSelectionPanel.tsx  # 设备选择
│   │   │   ├── MonitorPanel.tsx          # 监控面板
│   │   │   └── ReportPanel.tsx           # 报告面板
│   │   └── widgets/         # 小部件
│   │       ├── MonitoringControls.tsx    # 监控控制
│   │       └── SessionList.tsx           # 会话列表
│   ├── config/
│   │   └── metricCards.ts   # 指标卡片配置
│   ├── services/
│   │   └── api.ts           # API 客户端
│   ├── store/
│   │   └── monitoringStore.ts  # Zustand 状态管理
│   ├── theme/
│   │   └── neon.ts          # 霓虹主题配置
│   ├── types/
│   │   └── index.ts         # TypeScript 类型定义
│   ├── App.tsx              # 应用入口
│   ├── main.tsx             # React 挂载点
│   └── index.css            # 全局样式
├── public/                   # 静态资源
├── index.html                # HTML 模板
├── vite.config.ts            # Vite 配置 (端口 80)
├── tailwind.config.js        # TailwindCSS 配置
└── tsconfig.json             # TypeScript 配置
```

## Technology Stack

| 组件 | 版本 | 用途 |
|------|------|------|
| React | 19.2.0 | UI 框架 |
| TypeScript | 5.9.3 | 类型安全 |
| Vite | 7.2.4 | 构建工具 |
| ECharts | 6.0.0 | 图表库 |
| Zustand | 5.0.10 | 状态管理 |
| TailwindCSS | 4.1.18 | 样式框架 |
| Axios | 1.13.4 | HTTP 客户端 |
| dayjs | 1.11.19 | 时间处理 |

## Neon Theme Colors

| 指标 | 颜色 | 十六进制 |
|------|------|---------|
| CPU | 青色 | `#00f2ff` |
| Memory | 紫色 | `#7000ff` |
| FPS | 橙色 | `#ffb400` |
| Network Up | 绿色 | `#00ff87` |
| Network Down | 蓝色 | `#0062ff` |
| Background | 深色 | `#0a0a0a` |
| Card | 深灰 | `#141414` |

## 支持的监控指标

### Android 平台
- **CPU Usage** - 应用 CPU 使用率
- **Memory Usage** - 内存使用量
- **Frame Rate** - 帧率、卡顿检测
- **Network Upload** - 上行流量
- **Network Download** - 下行流量

### iOS 平台
- **CPU Usage** - 应用 CPU 使用率（通过 SysmonService）
- **Memory Usage** - 内存使用量（通过 SysmonService）
- **Frame Rate** - 帧率
- **Network Upload** - 上行流量
- **Network Download** - 下行流量

## API Endpoints

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/devices` | GET | 获取设备列表 |
| `/api/devices/{id}/apps` | GET | 获取设备应用列表 |
| `/api/monitoring/start` | POST | 启动监控 |
| `/api/monitoring/stop` | POST | 停止监控 |
| `/api/monitoring/sessions` | GET | 获取会话列表 |
| `/ws/monitoring/{session_id}` | WebSocket | 实时监控数据推送 |

## Environment Variables

环境变量配置:

```bash
# .env.local
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

## Linting

运行 ESLint:
```bash
npm run lint
```

## Troubleshooting

### 后端服务未响应

确保 FastAPI 服务运行在 http://localhost:8000:
```bash
cd .worktrees/1.0.3
venv/Scripts/uvicorn.exe insight_eyes.web.api.main:app --reload --host 0.0.0.0 --port 8000
```

### iOS 设备检测问题

iOS 设备需要：
1. 信任电脑
2. 开启开发者模式
3. 安装 pymobiledevice3 >= 7.4.0
4. SysmonService 连接成功

### WebSocket 连接失败

检查：
1. 后端服务是否运行
2. 防火墙是否允许 ws:// 连接
3. 端口 8000 是否被占用

## 下一步计划

### Phase 4: 功能完善

- [ ] 数据导出功能（CSV/JSON/Excel）
- [ ] 会话管理高级功能（删除、批量删除）
- [ ] 配置导入/导出
- [ ] 设备断线重连
- [ ] 单元测试和 E2E 测试
- [ ] 部署配置

## License

Part of the Insight Eye project.

---

**最后更新**: 2026-02-02
**版本**: v1.0.3
