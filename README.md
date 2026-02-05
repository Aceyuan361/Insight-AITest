# Insight-Eye Web

<div align="center">

**移动设备性能监控 Web 应用**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6.svg)](https://www.typescriptlang.org/)

</div>

---

## 简介

Insight-Eye Web 是一个跨平台的移动设备性能监控 Web 应用，支持 **Android** 和 **iOS** 设备的实时性能数据采集与可视化展示。

### 核心特性

- **多平台支持**: Android (无需 ROOT) 和 iOS (无需越狱)
- **实时监控**: WebSocket 实时推送性能数据
- **可视化展示**: 基于 ECharts 的精美图表展示
- **告警系统**: 自定义告警规则，实时异常检测
- **历史数据**: 会话记录与历史数据查询
- **多设备并发**: 支持同时监控多个设备

### 支持的监控指标

| 指标类别 | Android | iOS |
|---------|---------|-----|
| CPU | ✅ 应用/系统使用率 | ✅ 应用使用率 |
| 内存 | ✅ PSS/Native/Dalvik | ✅ physFootprint |
| FPS | ✅ 帧率 + 卡顿检测 | ✅ 系统刷新率 |
| 网络 | ✅ 上行/下行流量 | ✅ 系统流量 |
| 电池 | ✅ 电量/温度 | ✅ 电量/温度 |
| 能耗 | ✅ GPU 能耗 | ✅ CPU/GPU/网络能耗 |

---

## 快速开始

### 环境要求

- **Python**: 3.10+
- **Node.js**: 18+
- **ADB** (Android 调试桥)
- **pymobiledevice3** >= 7.0.0 (iOS 支持)

### 1. 克隆仓库

```bash
git clone -b 1.0.0 https://github.com/your-org/insight-eye-web.git
cd insight-eye-web
```

### 2. 启动后端服务

```bash
# 安装 Python 依赖
pip install -r insight_eyes/web/requirements.txt

# 启动 API 服务
python -m insight_eyes
```

后端服务将运行在 `http://localhost:8000`

API 文档: `http://localhost:8000/docs`

### 3. 启动前端服务

```bash
# 进入前端目录
cd insight_eyes/web-frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务将运行在 `http://localhost:5173`

### 4. 访问应用

打开浏览器访问 `http://localhost:5173`

---

## 项目结构

```
insight-eye-web/
├── insight_eyes/
│   ├── core/                 # 核心层 - 设备管理
│   │   ├── device_manager.py
│   │   ├── base_monitor.py
│   │   └── models/
│   ├── public/               # 平台采集器
│   │   ├── android/          # Android APM
│   │   ├── ios/              # iOS APM
│   │   └── common.py
│   ├── web/                  # Web 后端
│   │   ├── api/              # FastAPI 服务
│   │   └── websocket/        # WebSocket 服务
│   └── web-frontend/         # Web 前端
│       ├── src/
│       ├── package.json
│       └── vite.config.ts
├── docs/                     # 项目文档
├── README.md
└── requirements.txt
```

---

## 使用指南

### 设备连接

**Android 设备:**
1. 启用 USB 调试模式
2. 连接电脑
3. 在 Web 界面中选择设备

**iOS 设备:**
1. 信任电脑并启用开发者模式
2. 连接电脑
3. 在 Web 界面中选择设备

### 创建监控会话

1. 选择要监控的设备
2. 选择应用（Android）或输入 Bundle ID（iOS）
3. 点击"开始监控"
4. 实时查看性能数据

### 配置告警规则

在告警设置页面可以配置：
- CPU 使用率阈值
- 内存使用量阈值
- FPS 最低阈值
- 电池温度阈值

---

## 技术栈

### 后端

- **FastAPI** - 现代 Web 框架
- **WebSocket** - 实时通信
- **SQLite** - 数据存储
- **ADB** - Android 设备通信
- **pymobiledevice3** - iOS 设备通信

### 前端

- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **ECharts** - 数据可视化
- **TailwindCSS** - CSS 框架
- **Ant Design** - UI 组件库

---

## 开发指南

### 后端开发

```bash
# 安装开发依赖
pip install -r insight_eyes/web/requirements-dev.txt

# 运行测试
pytest

# 代码格式化
black insight_eyes/web/
```

### 前端开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 运行测试
npm run test

# 构建
npm run build
```

---

## API 文档

启动后端服务后，访问 `http://localhost:8000/docs` 查看完整的 API 文档（Swagger UI）。

### 主要 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/devices` | GET | 获取设备列表 |
| `/api/devices/{id}/apps` | GET | 获取应用列表 |
| `/api/sessions` | POST | 创建监控会话 |
| `/api/sessions/{id}/stream` | WS | 实时数据流 |
| `/api/sessions/{id}` | DELETE | 停止会话 |

---

## 常见问题

### Q: iOS 设备无法连接？

A: 请确保：
1. 设备已信任电脑
2. 已启用开发者模式
3. pymobiledevice3 版本 >= 7.0.0

### Q: Android 设备检测不到？

A: 请确保：
1. 已安装 ADB
2. USB 调试已启用
3. 已授权电脑调试

### Q: 数据显示延迟？

A: 检查网络连接和设备状态，确保 WebSocket 连接正常。

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

---

## 相关项目

- **[Insight-Eye Desktop](https://github.com/your-org/insight-eye)** - PyQt6 桌面版
- **[pymobiledevice3](https://github.com/doronz88/pymobiledevice3)** - iOS 设备通信库

---

## 联系方式

- Issue: [GitHub Issues](https://github.com/your-org/insight-eye-web/issues)
- Email: your-email@example.com

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐️ Star！**

</div>
