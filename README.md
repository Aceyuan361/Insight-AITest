# Insight-Eye Web / 移动设备性能监控 Web 应用

<div align="center">

**Mobile Device Performance Monitoring Web Application**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6.svg)](https://www.typescriptlang.org/)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/Aceyuan361/Insight_eye/releases)

</div>

---

## 简介 / Introduction

**中文** | Insight-Eye Web 是一个跨平台的移动设备性能监控 Web 应用，支持 **Android** 和 **iOS** 设备的实时性能数据采集与可视化展示。

**English** | Insight-Eye Web is a cross-platform mobile device performance monitoring web application that supports real-time performance data collection and visualization for **Android** and **iOS** devices.

### 核心特性 / Key Features

**中文**:
- **多平台支持**: Android (无需 ROOT) 和 iOS (无需越狱)
- **实时监控**: WebSocket 实时推送性能数据
- **可视化展示**: 基于 ECharts 的精美图表展示
- **告警系统**: 自定义告警规则，实时异常检测
- **历史数据**: 会话记录与历史数据查询
- **Web 界面**: 赛博朋克霓虹风格设计

**English**:
- **Multi-Platform Support**: Android (No ROOT required) and iOS (No jailbreak required)
- **Real-time Monitoring**: WebSocket-based real-time performance data streaming
- **Visualization**: Beautiful charts powered by ECharts
- **Alert System**: Custom alert rules with real-time anomaly detection
- **Historical Data**: Session records and historical data analysis
- **Web Interface**: Cyberpunk neon-styled design

### 支持的监控指标 / Supported Metrics

| 指标类别 / Metrics | Android | iOS |
|---------|---------|-----|
| CPU / CPU Usage | ✅ 应用/系统 / App/System | ✅ 应用 / App |
| 内存 / Memory | ✅ PSS/Native/Dalvik | ✅ physFootprint |
| FPS / Frame Rate | ✅ 帧率+卡顿检测 / FPS+Jank | ✅ 系统刷新率 / System Refresh Rate |
| 网络 / Network | ✅ 上行/下行流量 / Up/Down | ✅ 系统流量 / System |
| 电池 / Battery | ✅ 电量/温度 / Level/Temp | ✅ 电量/温度 / Level/Temp |
| GPU | ✅ 部分设备支持 / Partial Support | ❌ 不支持 / Not Supported |
| 能耗 / Energy | ✅ GPU 能耗 / GPU | ✅ CPU/GPU/网络 / CPU/GPU/Network |

---

## 应用截图 / Screenshots

### 实时监控面板 / Real-time Monitoring Dashboard
**中文**: 实时监控设备性能数据，包括 CPU、内存、FPS、网络等关键指标。
**English**: Monitor device performance metrics in real-time, including CPU, memory, FPS, network, and more.

![Dashboard](docs/screenshots/01-dashboard.png)

### 测试报告页 / Test Reports Page
**中文**: 查看历史监控会话，分析性能数据和趋势。
**English**: View historical monitoring sessions and analyze performance data trends.

![Reports](docs/screenshots/02-reports.png)

### 详细数据展示 / Detailed Data View
**中文**: 深入分析各项性能指标，发现潜在问题。
**English**: Deep dive into performance metrics to identify potential issues.

![Reports Detail](docs/screenshots/03-reports-detail.png)

---

## 快速开始 / Quick Start

### 环境要求 / Requirements

**中文**:
- **Python**: 3.10+
- **Node.js**: 18+ (仅开发模式 / Development only)
- **ADB** (Android 调试桥 / Android Debug Bridge)
- **pymobiledevice3** >= 7.0.0 (iOS 支持 / iOS support)

**English**:
- **Python**: 3.10+
- **Node.js**: 18+ (Development mode only)
- **ADB** (Android Debug Bridge)
- **pymobiledevice3** >= 7.0.0 (For iOS support)

### 方式一：从源码运行 / Method 1: Run from Source

**中文**:
```bash
# 1. 克隆仓库 / Clone repository
git clone -b 1.0.0 https://github.com/Aceyuan361/Insight_eye.git
cd Insight_eye

# 2. 安装 Python 依赖 / Install Python dependencies
pip install -r insight_eyes/web/requirements.txt

# 3. 启动后端服务 / Start backend service (会自动打开浏览器 / opens browser automatically)
python -m insight_eyes

# 后端运行在 / Backend runs on: http://localhost:8001
# API 文档 / API Docs: http://localhost:8001/docs

# 4. 开发模式：启动前端服务 / Development: Start frontend service
cd insight_eyes/web-frontend
npm install
npm run dev

# 前端运行在 / Frontend runs on: http://localhost:80 (or :81 if :80 occupied)
```

**English**:
```bash
# 1. Clone repository
git clone -b 1.0.0 https://github.com/Aceyuan361/Insight_eye.git
cd Insight_eye

# 2. Install Python dependencies
pip install -r insight_eyes/web/requirements.txt

# 3. Start backend service (opens browser automatically)
python -m insight_eyes

# Backend runs on: http://localhost:8001
# API Docs: http://localhost:8001/docs

# 4. Development: Start frontend service
cd insight_eyes/web-frontend
npm install
npm run dev

# Frontend runs on: http://localhost:80 (or :81 if :80 occupied)
```

### 方式二：使用 pip 安装（简化） / Method 2: Install via pip (Simplified)

**中文**:
```bash
# 1. 安装 Insight-Eye / Install Insight-Eye
pip install insight-eyes

# 2. 运行应用 / Run application (自动启动后端并打开浏览器)
insight-eye-web

# 后端运行在 / Backend runs on: http://localhost:8001
# 浏览器会自动打开 / Browser opens automatically
```

**English**:
```bash
# 1. Install Insight-Eye
pip install insight-eyes

# 2. Run application (starts backend and opens browser)
insight-eye-web

# Backend runs on: http://localhost:8001
# Browser opens automatically
```

---

## 项目结构 / Project Structure

```
insight-eye-web/
├── insight_eyes/
│   ├── core/                 # 核心层 - 设备管理 / Core - Device Management
│   │   ├── device_manager.py
│   │   ├── base_monitor.py
│   │   └── models/
│   ├── public/               # 平台采集器 / Platform Collectors
│   │   ├── android/          # Android APM
│   │   ├── ios/              # iOS APM
│   │   └── common.py
│   ├── web/                  # Web 后端 / Web Backend
│   │   ├── api/              # FastAPI 服务 / FastAPI Service
│   │   └── websocket/        # WebSocket 服务 / WebSocket Service
│   └── web-frontend/         # Web 前端 / Web Frontend
│       ├── src/
│       ├── package.json
│       └── vite.config.ts
├── docs/                     # 项目文档 / Documentation
├── README.md
└── requirements.txt
```

---

## 使用指南 / User Guide

### 设备连接 / Device Connection

**Android 设备 / Android Devices**:
1. **中文**: 启用 USB 调试模式，连接电脑，在 Web 界面中选择设备
   **English**: Enable USB debugging mode, connect to computer, select device in Web interface

**iOS 设备 / iOS Devices**:
1. **中文**: 信任电脑并启用开发者模式，连接电脑，在 Web 界面中选择设备
   **English**: Trust computer and enable Developer Mode, connect to computer, select device in Web interface

### 创建监控会话 / Create Monitoring Session

**中文**:
1. 选择要监控的设备
2. 选择应用（Android）或输入 Bundle ID（iOS）
3. 点击"开始监控"
4. 实时查看性能数据

**English**:
1. Select device to monitor
2. Select application (Android) or enter Bundle ID (iOS)
3. Click "Start Monitoring"
4. View real-time performance data

### 配置告警规则 / Configure Alert Rules

**中文**: 在配置面板可以设置：
- CPU 使用率阈值 / CPU usage threshold
- 内存使用量阈值 / Memory usage threshold
- FPS 最低阈值 / Minimum FPS threshold
- 电池温度阈值 / Battery temperature threshold

**English**: Configure alert thresholds in the settings panel:
- CPU usage percentage threshold
- Memory usage threshold
- Minimum FPS threshold
- Battery temperature threshold

---

## 技术栈 / Tech Stack

### 后端 / Backend

**中文**:
- **FastAPI** - 现代 Web 框架
- **WebSocket** - 实时通信
- **SQLite** - 数据存储
- **ADB** - Android 设备通信
- **pymobiledevice3** - iOS 设备通信

**English**:
- **FastAPI** - Modern web framework
- **WebSocket** - Real-time communication
- **SQLite** - Data storage
- **ADB** - Android device communication
- **pymobiledevice3** - iOS device communication

### 前端 / Frontend

**中文**:
- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **ECharts** - 数据可视化
- **TailwindCSS** - CSS 框架
- **Ant Design** - UI 组件库

**English**:
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **ECharts** - Data visualization
- **TailwindCSS** - CSS framework
- **Ant Design** - UI component library

---

## API 文档 / API Documentation

**中文**: 启动后端服务后，访问 `http://localhost:8001/docs` 查看完整的 API 文档（Swagger UI）。

**English**: After starting the backend service, visit `http://localhost:8001/docs` for complete API documentation (Swagger UI).

### 主要 API 端点 / Main API Endpoints

| 端点 / Endpoint | 方法 / Method | 描述 / Description |
|------|------|------|
| `/api/devices` | GET | 获取设备列表 / Get device list |
| `/api/devices/{id}/apps` | GET | 获取应用列表 / Get app list |
| `/api/monitoring/start` | POST | 开始监控 / Start monitoring |
| `/api/monitoring/stop` | POST | 停止监控 / Stop monitoring |
| `/ws/monitoring/{id}` | WS | 实时数据流 / Real-time data stream |

---

## 常见问题 / FAQ

### Q: iOS 设备无法连接？/ iOS device not connecting?

**中文**: 请确保：
1. 设备已信任电脑
2. 已启用开发者模式
3. pymobiledevice3 版本 >= 7.0.0
4. iOS 系统版本在 11.0 - 16.x 之间（不支持 iOS 17+）

**English**: Please ensure:
1. Device has trusted the computer
2. Developer Mode is enabled
3. pymobiledevice3 version >= 7.0.0
4. iOS version is between 11.0 - 16.x (iOS 17+ not supported)

### Q: Android 设备检测不到？/ Android device not detected?

**中文**: 请确保：
1. 已安装 ADB
2. USB 调试已启用
3. 已授权电脑调试

**English**: Please ensure:
1. ADB is installed
2. USB debugging is enabled
3. Computer is authorized for debugging

### Q: 为什么 iOS 不支持 GPU 监控？/ Why doesn't iOS support GPU monitoring?

**中文**: iOS 系统 API 限制，第三方应用无法访问 GPU 使用率数据。

**English**: iOS system API restrictions prevent third-party apps from accessing GPU usage data.

---

## 版本历史 / Version History

### v1.0.0 (2026-02-05)

**中文**:
- ✅ 实时告警推送
- ✅ 应用模糊搜索
- ✅ GPU 监控设备限制
- ✅ 监控面板动态布局
- ✅ iOS 启动延迟修复
- ✅ 测试报告统计功能
- ✅ 告警阈值持久化

**English**:
- ✅ Real-time alert push notifications
- ✅ Fuzzy search for applications
- ✅ GPU monitoring device restrictions
- ✅ Dynamic monitoring panel layout
- ✅ iOS startup delay fix
- ✅ Test report statistics
- ✅ Alert threshold persistence

---

## 贡献指南 / Contributing

**中文**: 欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

**English**: Issues and Pull Requests are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 许可证 / License

**中文**: 本项目采用 [MIT License](LICENSE) 开源协议。

**English**: This project is licensed under the [MIT License](LICENSE).

---

## 特别鸣谢 / Special Thanks

**中文**: 本项目的实现离不开以下优秀开源项目给予的思路和支持：

- **[solox](https://github.com/ZCOpen/SoloX)** - 移动性能自动化测试工具，为本项目提供了移动设备性能监控的核心思路
- **[pymobiledevice3](https://github.com/doronz88/pymobiledevice3)** - iOS 设备通信库，让 iOS 监控成为可能
- **[py-ios-device](https://github.com/doronz88/pymobiledevice3)** - iOS 设备管理和通信的底层支持

**English**: This project would not be possible without the inspiration and support from these excellent open-source projects:

- **[solox](https://github.com/ZCOpen/SoloX)** - Mobile performance automation testing tool, provided core concepts for mobile device performance monitoring
- **[pymobiledevice3](https://github.com/doronz88/pymobiledevice3)** - iOS device communication library, making iOS monitoring possible
- **[py-ios-device](https://github.com/doronz88/pymobiledevice3)** - Underlying support for iOS device management and communication

---

## 相关项目 / Related Projects

- **[pymobiledevice3](https://github.com/doronz88/pymobiledevice3)** - iOS device communication library / iOS 设备通信库
- **[FastAPI](https://github.com/tiangolo/fastapi)** - Modern Python web framework / 现代化 Python Web 框架
- **[ECharts](https://echarts.apache.org/)** - Data visualization library / 数据可视化库

---

## 联系方式 / Contact

- **作者 / Author**: Aceyuan361
- **Issue**: [GitHub Issues](https://github.com/Aceyuan361/Insight_eye/issues)
- **Email**: [594902674@qq.com](mailto:594902674@qq.com)

---

<div align="center">

**中文**: 如果这个项目对你有帮助，请给个 ⭐️ Star！

**English**: If this project helps you, please give it a ⭐️ Star！

</div>
