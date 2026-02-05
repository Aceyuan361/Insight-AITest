# Insight-Eye Web

<div align="center">

**Mobile Device Performance Monitoring Web Application**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6.svg)](https://www.typescriptlang.org/)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/Aceyuan361/Insight_eye/releases)

**[中文文档](./README.zh-CN.md)** | English

</div>

---

## Introduction

Insight-Eye Web is a cross-platform mobile device performance monitoring web application that supports real-time performance data collection and visualization for **Android** and **iOS** devices.

### Key Features

- **Multi-Platform Support**: Android (No ROOT required) and iOS (No jailbreak required)
- **Real-time Monitoring**: WebSocket-based real-time performance data streaming
- **Visualization**: Beautiful charts powered by ECharts
- **Alert System**: Custom alert rules with real-time anomaly detection
- **Historical Data**: Session records and historical data analysis
- **Web Interface**: Cyberpunk neon-styled design

### Supported Metrics

| Metrics | Android | iOS |
|---------|---------|-----|
| CPU Usage | ✅ App/System | ✅ App |
| Memory | ✅ PSS/Native/Dalvik | ✅ physFootprint |
| Frame Rate | ✅ FPS+Jank detection | ✅ System refresh rate |
| Network | ✅ Up/Down traffic | ✅ System traffic |
| Battery | ✅ Level/Temp | ✅ Level/Temp |
| GPU | ✅ Partial support | ❌ Not supported |
| Energy | ✅ GPU | ✅ CPU/GPU/Network |

---

## Screenshots

### Real-time Monitoring Dashboard
Monitor device performance metrics in real-time, including CPU, memory, FPS, network, and more.

![Dashboard](docs/screenshots/01-dashboard.png)

### Test Reports Page
View historical monitoring sessions and analyze performance data trends.

![Reports](docs/screenshots/02-reports.png)

### Detailed Data View
Deep dive into performance metrics to identify potential issues.

![Reports Detail](docs/screenshots/03-reports-detail.png)

---

## Quick Start

### Requirements

- **Python**: 3.10+
- **Node.js**: 18+ (Development mode only)
- **ADB** (Android Debug Bridge)
- **pymobiledevice3** >= 7.0.0 (For iOS support)

### Method 1: Run from Source

```bash
# 1. Clone repository
git clone -b 1.0.0 https://github.com/Aceyuan361/Insight_eye.git
cd Insight_eye

# 2. Install Python dependencies
pip install -r requirements.txt

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

### Method 2: Install via pip (Simplified)

```bash
# 1. Install Insight-Eye
pip install insight-eyes

# 2. Run application (starts backend and opens browser)
insight-eye-web

# Backend runs on: http://localhost:8001
# Browser opens automatically
```

---

## Project Structure

```
insight-eye-web/
├── insight_eyes/
│   ├── __main__.py           # Entry point
│   ├── core/                 # Core - Device Management & Data Models
│   │   ├── device_manager.py # Device management
│   │   ├── base_monitor.py   # Base monitoring class
│   │   ├── database.py       # SQLite database
│   │   └── models/           # Data models
│   ├── public/               # Platform Collectors
│   │   ├── adb/              # ADB wrapper
│   │   ├── android/          # Android APM
│   │   ├── ios/              # iOS APM
│   │   └── common.py         # Common utilities
│   ├── web/                  # Web Backend (FastAPI)
│   │   ├── api/
│   │   │   ├── main.py       # FastAPI application
│   │   │   ├── devices.py    # Device management API
│   │   │   ├── monitoring.py # Monitoring control API
│   │   │   └── schemas.py    # Pydantic models
│   │   └── websocket/        # WebSocket service
│   └── web-frontend/         # Web Frontend (React)
│       ├── src/
│       │   ├── components/   # React components
│       │   ├── config/       # Configuration
│       │   ├── i18n/         # Internationalization
│       │   ├── services/     # API services
│       │   ├── store/        # Zustand state management
│       │   ├── theme/        # Neon theme
│       │   ├── types/        # TypeScript types
│       │   └── utils/        # Utilities
│       ├── public/           # Static assets
│       ├── tests/            # E2E tests
│       ├── package.json
│       ├── vite.config.ts
│       └── tailwind.config.js
├── docs/                     # Documentation
├── README.md                 # English documentation
├── README.zh-CN.md           # Chinese documentation
├── pyproject.toml            # Package configuration
└── requirements.txt          # Python dependencies
```

---

## User Guide

### Device Connection

**Android Devices**:
1. Enable USB debugging mode
2. Connect to computer
3. Select device in Web interface

**iOS Devices**:
1. Trust computer and enable Developer Mode
2. Connect to computer
3. Select device in Web interface

### Create Monitoring Session

1. Select device to monitor
2. Select application (Android) or enter Bundle ID (iOS)
3. Click "Start Monitoring"
4. View real-time performance data

### Configure Alert Rules

Configure alert thresholds in the settings panel:
- CPU usage percentage threshold
- Memory usage threshold
- Minimum FPS threshold
- Battery temperature threshold

---

## Tech Stack

### Backend

- **FastAPI** - Modern web framework
- **WebSocket** - Real-time communication
- **SQLite** - Data storage
- **ADB** - Android device communication
- **pymobiledevice3** - iOS device communication

### Frontend

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **ECharts** - Data visualization
- **TailwindCSS** - CSS framework
- **Ant Design** - UI component library

---

## API Documentation

After starting the backend service, visit `http://localhost:8001/docs` for complete API documentation (Swagger UI).

### Main API Endpoints

| Endpoint | Method | Description |
|------|------|------|
| `/api/devices` | GET | Get device list |
| `/api/devices/{id}/apps` | GET | Get app list |
| `/api/monitoring/start` | POST | Start monitoring |
| `/api/monitoring/stop` | POST | Stop monitoring |
| `/ws/monitoring/{id}` | WS | Real-time data stream |

---

## FAQ

### Q: iOS device not connecting?

Please ensure:
1. Device has trusted the computer
2. Developer Mode is enabled
3. pymobiledevice3 version >= 7.0.0
4. iOS version is between 11.0 - 16.x (iOS 17+ not supported)

### Q: Android device not detected?

Please ensure:
1. ADB is installed
2. USB debugging is enabled
3. Computer is authorized for debugging

### Q: Why doesn't iOS support GPU monitoring?

iOS system API restrictions prevent third-party apps from accessing GPU usage data.

---

## Contributing

Issues and Pull Requests are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Acknowledgments

This project would not be possible without the inspiration and support from these excellent open-source projects:

- **[solox](https://github.com/ZCOpen/SoloX)** - Mobile performance automation testing tool, provided core concepts for mobile device performance monitoring
- **[pymobiledevice3](https://github.com/doronz88/pymobiledevice3)** - iOS device communication library, making iOS monitoring possible
- **[py-ios-device](https://github.com/doronz88/pymobiledevice3)** - Underlying support for iOS device management and communication

---

## Related Projects

- **[pymobiledevice3](https://github.com/doronz88/pymobiledevice3)** - iOS device communication library
- **[FastAPI](https://github.com/tiangolo/fastapi)** - Modern Python web framework
- **[ECharts](https://echarts.apache.org/)** - Data visualization library

---

## Contact

- **Author**: Aceyuan361
- **Issues**: [GitHub Issues](https://github.com/Aceyuan361/Insight_eye/issues)
- **Email**: [594902674@qq.com](mailto:594902674@qq.com)

---

<div align="center">

If this project helps you, please give it a ⭐️ Star！

</div>
