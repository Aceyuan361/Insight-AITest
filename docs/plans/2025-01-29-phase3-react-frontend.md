# Phase 3: React 前端开发实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标：** 实现与桌面版 1:1 对等的 Web 前端，支持 Mac 用户通过浏览器访问

**架构：** React + Vite + ECharts + Zustand + WebSocket，复刻桌面版霓虹赛博朋克主题

**Tech Stack：** React 18, Vite, TypeScript, ECharts, Zustand, TailwindCSS

**前置条件：**
- Phase 1 核心层重构已完成
- Phase 2 FastAPI 后端已完成
- FastAPI 服务运行在 http://localhost:8000

---

## Task 1: 创建 React + Vite 项目

**Files:**
- Create: `insight_eyes/web-frontend/` (整个项目目录)
- Create: `insight_eyes/web-frontend/package.json`
- Create: `insight_eyes/web-frontend/tsconfig.json`
- Create: `insight_eyes/web-frontend/vite.config.ts`
- Create: `insight_eyes/web-frontend/index.html`
- Create: `insight_eyes/web-frontend/src/main.tsx`

**Step 1: 在 worktree 中创建 React 项目**

```bash
cd .worktrees/1.0.3/insight_eyes

# 使用 Vite 创建 React + TypeScript 项目
npm create vite@latest web-frontend -- --template react-ts

cd web-frontend
npm install
```

**Step 2: 安装额外依赖**

```bash
cd insight_eyes/web-frontend

# ECharts - 图表库
npm install echarts

# Zustand - 状态管理
npm install zustand

# TailwindCSS - 样式
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# WebSocket 客户端
npm install events

# HTTP 客户端
npm install axios

# 时间处理
npm install dayjs
```

**Step 3: 配置 TailwindCSS**

创建 `tailwind.config.js`:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 霓虹主题色
        neon: {
          cpu: '#00f2ff',
          memory: '#7000ff',
          fps: '#ffb400',
          networkUp: '#00ff87',
          networkDown: '#0062ff',
        },
        dark: {
          bg: '#0a0a0a',
          card: '#141414',
        }
      },
      fontFamily: {
        sans: ['"Microsoft YaHei UI"', 'Segoe UI', 'Arial', 'sans-serif'],
        mono: ['Consolas', 'Monaco', 'monospace'],
      },
    },
  },
  plugins: [],
}
```

**Step 4: 配置 Vite 别名**

修改 `vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

**Step 5: 验证项目运行**

```bash
npm run dev
```

访问 http://localhost:3000 应该看到 Vite 欢迎页面

**Step 6: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/web-frontend/
git commit -m "feat(web): 创建 React + Vite 前端项目

- 使用 Vite 创建 React + TypeScript 项目
- 安装 ECharts、Zustand、TailwindCSS
- 配置 TailwindCSS 霓虹主题
- 配置 Vite 代理到 FastAPI 后端

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 2: 创建霓虹主题系统和类型定义

**Files:**
- Create: `src/theme/neon.ts`
- Create: `src/types/index.ts`
- Create: `src/config/metricCards.ts`

**Step 1: 创建霓虹主题配置**

```typescript
// src/theme/neon.ts
export const neonTheme = {
  colors: {
    // 背景色
    background: '#0a0a0a',
    cardBg: '#141414',

    // 文字色
    textPrimary: '#ffffff',
    textSecondary: '#aaaaaa',

    // 霓虹指标色（与桌面版完全一致）
    cpu: '#00f2ff',      // 青色
    memory: '#7000ff',   // 紫色
    fps: '#ffb400',      // 橙色
    networkUp: '#00ff87', // 绿色
    networkDown: '#0062ff', // 蓝色

    // 状态色
    success: '#22c55e',
    warning: '#f59e0b',
    error: '#ef4444',
  },

  fonts: {
    primary: '"Microsoft YaHei UI", "Segoe UI", Arial, sans-serif',
    mono: '"Consolas", "Monaco", monospace',
  },

  spacing: {
    cardPadding: 15,
    chartGridTop: 35,
    chartGridLeft: 55,
    chartGridRight: 20,
    chartGridBottom: 30,
  },

  sizes: {
    windowMinWidth: 1000,
    windowMinHeight: 600,
    cardMinHeight: 180,
  },
};
```

**Step 2: 创建类型定义**

```typescript
// src/types/index.ts
export interface Device {
  device_id: string;
  device_name: string;
  platform: 'android' | 'ios';
  status: 'online' | 'offline';
}

export interface Session {
  id: number;
  device_id: string;
  app_package: string;
  platform: string;
  status: 'created' | 'running' | 'stopped' | 'error';
  start_time: string;
  end_time?: string;
  duration?: number;
}

export interface MetricsData {
  timestamp: string;
  cpu?: number;
  memory?: number;
  fps?: number;
  network_up?: number;
  network_down?: number;
  battery?: number;
  temperature?: number;
}

export interface MetricCardConfig {
  metricId: keyof MetricsData;
  title: string;
  color: string;
  yMin?: number;
  yMax?: number;
  decimals: number;
  unit: string;
  enabled: boolean;
  priority: number;
}
```

**Step 3: 创建指标卡片配置**

```typescript
// src/config/metricCards.ts
import { MetricCardConfig } from '@/types';

export const ALL_METRIC_CARDS: MetricCardConfig[] = [
  {
    metricId: 'cpu',
    title: 'CPU Usage (%)',
    color: '#00f2ff',
    yMin: 0,
    yMax: 100,
    decimals: 0,
    unit: '%',
    enabled: true,
    priority: 1,
  },
  {
    metricId: 'memory',
    title: 'Memory Usage (MB)',
    color: '#7000ff',
    yMin: 0,
    decimals: 0,
    unit: 'MB',
    enabled: true,
    priority: 2,
  },
  {
    metricId: 'fps',
    title: 'Frame Rate (FPS)',
    color: '#ffb400',
    decimals: 0,
    unit: 'FPS',
    enabled: true,
    priority: 3,
  },
  {
    metricId: 'network_up',
    title: 'Network Upload (KB/s)',
    color: '#00ff87',
    yMin: 0,
    decimals: 1,
    unit: 'KB/s',
    enabled: true,
    priority: 4,
  },
  {
    metricId: 'network_down',
    title: 'Network Download (KB/s)',
    color: '#0062ff',
    yMin: 0,
    decimals: 1,
    unit: 'KB/s',
    enabled: true,
    priority: 5,
  },
];
```

**Step 4: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/web-frontend/src/
git commit -m "feat(web): 添加霓虹主题配置和类型定义

- 创建 neon.ts 霓虹主题配置（与桌面版一致）
- 创建 TypeScript 类型定义
- 创建指标卡片配置

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 3: 实现 Zustand 状态管理

**Files:**
- Create: `src/store/monitoringStore.ts`
- Create: `src/store/types.ts`

**Step 1: 创建监控状态管理**

```typescript
// src/store/monitoringStore.ts
import { create } from 'zustand';
import { Device, Session, MetricsData } from '@/types';

interface MonitoringState {
  // 状态
  devices: Device[];
  selectedDevice: string | null;
  isMonitoring: boolean;
  currentSession: Session | null;
  metricsData: Record<string, number[]>;
  timestamps: string[];
  wsConnection: WebSocket | null;

  // Actions
  setDevices: (devices: Device[]) => void;
  selectDevice: (deviceId: string) => void;
  startMonitoring: (deviceId: string, appPackage: string) => Promise<void>;
  stopMonitoring: () => Promise<void>;
  updateMetrics: (data: MetricsData) => void;
  clearMetrics: () => void;
}

export const useMonitoringStore = create<MonitoringState>((set, get) => ({
  // 初始状态
  devices: [],
  selectedDevice: null,
  isMonitoring: false,
  currentSession: null,
  metricsData: {},
  timestamps: [],
  wsConnection: null,

  // 设置设备列表
  setDevices: (devices) => set({ devices }),

  // 选择设备
  selectDevice: (deviceId) => set({ selectedDevice: deviceId }),

  // 开始监控
  startMonitoring: async (deviceId, appPackage) => {
    try {
      const response = await fetch('/api/monitoring/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: deviceId,
          app_package: appPackage,
          platform: 'android',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start monitoring');
      }

      const session: Session = await response.json();

      // 建立 WebSocket 连接
      const ws = new WebSocket(`ws://localhost:8000/ws/monitoring/${session.id}`);

      ws.onopen = () => {
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === 'metrics') {
          get().updateMetrics(message.data);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
      };

      set({
        isMonitoring: true,
        currentSession: session,
        wsConnection: ws,
        metricsData: {},
        timestamps: [],
      });
    } catch (error) {
      console.error('Error starting monitoring:', error);
      throw error;
    }
  },

  // 停止监控
  stopMonitoring: async () => {
    const { currentSession, wsConnection } = get();

    // 关闭 WebSocket
    if (wsConnection) {
      wsConnection.close();
    }

    // 调用 API 停止监控
    if (currentSession) {
      try {
        await fetch(`/api/monitoring/stop`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: currentSession.id }),
        });
      } catch (error) {
        console.error('Error stopping monitoring:', error);
      }
    }

    set({
      isMonitoring: false,
      currentSession: null,
      wsConnection: null,
    });
  },

  // 更新指标数据
  updateMetrics: (data) => set((state) => {
    const newMetricsData = { ...state.metricsData };
    const newTimestamps = [...state.timestamps, data.timestamp];

    // 更新每个指标
    Object.entries(data).forEach(([key, value]) => {
      if (key !== 'timestamp' && typeof value === 'number') {
        if (!newMetricsData[key]) {
          newMetricsData[key] = [];
        }
        newMetricsData[key] = [...newMetricsData[key], value].slice(-100); // 保留最近100个数据点
      }
    });

    // 保留最近100个时间戳
    const trimmedTimestamps = newTimestamps.slice(-100);

    return {
      metricsData: newMetricsData,
      timestamps: trimmedTimestamps,
    };
  }),

  // 清除指标数据
  clearMetrics: () => set({
    metricsData: {},
    timestamps: [],
  }),
}));
```

**Step 2: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/web-frontend/src/store/
git commit -m "feat(web): 实现 Zustand 状态管理

- 创建监控状态管理 store
- 实现设备管理功能
- 实现监控启动/停止功能
- 集成 WebSocket 实时数据推送

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 4: 实现 API 服务层

**Files:**
- Create: `src/services/api.ts`
- Create: `src/services/websocket.ts`

**Step 1: 创建 API 服务**

```typescript
// src/services/api.ts
import axios from 'axios';
import { Device, Session } from '@/types';

const API_BASE_URL = '/api';

export const api = {
  // 获取设备列表
  async getDevices(): Promise<Device[]> {
    const response = await axios.get(`${API_BASE_URL}/devices`);
    return response.data;
  },

  // 获取设备详情
  async getDevice(deviceId: string): Promise<Device> {
    const response = await axios.get(`${API_BASE_URL}/devices/${deviceId}`);
    return response.data;
  },

  // 开始监控
  async startMonitoring(deviceId: string, appPackage: string, platform: string = 'android'): Promise<Session> {
    const response = await axios.post(`${API_BASE_URL}/monitoring/start`, {
      device_id: deviceId,
      app_package: appPackage,
      platform,
    });
    return response.data;
  },

  // 停止监控
  async stopMonitoring(sessionId: number): Promise<{ status: string; session_id: number }> {
    const response = await axios.post(`${API_BASE_URL}/monitoring/stop`, null, {
      params: { session_id: sessionId },
    });
    return response.data;
  },

  // 获取会话列表
  async getSessions(limit: number = 100): Promise<Session[]> {
    const response = await axios.get(`${API_BASE_URL}/monitoring/sessions`, {
      params: { limit },
    });
    return response.data;
  },

  // 获取会话详情
  async getSession(sessionId: number): Promise<Session> {
    const response = await axios.get(`${API_BASE_URL}/monitoring/sessions/${sessionId}`);
    return response.data;
  },

  // 健康检查
  async healthCheck(): Promise<{ status: string }> {
    const response = await axios.get('/health');
    return response.data;
  },
};
```

**Step 2: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/web-frontend/src/services/
git commit -m "feat(web): 实现 API 服务层

- 创建 axios API 客户端
- 实现所有 REST API 调用
- 封装设备、监控、会话接口

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 5: 实现主窗口布局

**Files:**
- Create: `src/components/layout/MainWindow.tsx`
- Create: `src/components/layout/MenuBar.tsx`
- Create: `src/components/layout/StatusBar.tsx`
- Modify: `src/App.tsx`

**Step 1: 创建主窗口布局**

```typescript
// src/components/layout/MainWindow.tsx
import React, { useEffect } from 'react';
import { useMonitoringStore } from '@/store/monitoringStore';
import { api } from '@/services/api';
import MenuBar from './MenuBar';
import StatusBar from './StatusBar';

export default function MainWindow() {
  const { setDevices } = useMonitoringStore();

  useEffect(() => {
    // 加载设备列表
    const loadDevices = async () => {
      try {
        const devices = await api.getDevices();
        setDevices(devices);
      } catch (error) {
        console.error('Failed to load devices:', error);
      }
    };

    loadDevices();
  }, [setDevices]);

  return (
    <div className="min-h-screen bg-dark-bg text-text-primary">
      <MenuBar />
      <div className="container mx-auto px-4 py-6">
        {/* 主内容区域将在后续任务中实现 */}
        <div className="text-center text-text-secondary">
          <h1 className="text-3xl font-bold mb-4">Insight-Eye Web</h1>
          <p>性能监控工具 - Web 版</p>
        </div>
      </div>
      <StatusBar />
    </div>
  );
}
```

**Step 2: 创建菜单栏**

```typescript
// src/components/layout/MenuBar.tsx
import React from 'react';

export default function MenuBar() {
  return (
    <nav className="bg-dark-card border-b border-gray-800">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <h1 className="text-xl font-bold text-neon-cpu">Insight-Eye</h1>
            <span className="ml-2 text-sm text-text-secondary">v1.0.3</span>
          </div>

          {/* 菜单项 */}
          <div className="flex items-center space-x-6">
            <a href="#" className="text-text-secondary hover:text-white transition-colors">
              监控
            </a>
            <a href="#" className="text-text-secondary hover:text-white transition-colors">
              报告
            </a>
            <a href="#" className="text-text-secondary hover:text-white transition-colors">
              设置
            </a>
          </div>

          {/* 状态指示 */}
          <div className="flex items-center">
            <div className="flex items-center">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
              <span className="ml-2 text-sm text-text-secondary">在线</span>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
```

**Step 3: 创建状态栏**

```typescript
// src/components/layout/StatusBar.tsx
import React from 'react';
import { useMonitoringStore } from '@/store/monitoringStore';

export default function StatusBar() {
  const { isMonitoring, currentSession } = useMonitoringStore();

  return (
    <footer className="fixed bottom-0 left-0 right-0 bg-dark-card border-t border-gray-800">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-8">
          {/* 监控状态 */}
          <div className="flex items-center text-sm">
            {isMonitoring ? (
              <>
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                <span className="ml-2 text-text-secondary">
                  监控中 - Session #{currentSession?.id}
                </span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 bg-gray-500 rounded-full"></span>
                <span className="ml-2 text-text-secondary">未监控</span>
              </>
            )}
          </div>

          {/* 设备信息 */}
          <div className="text-sm text-text-secondary">
            {currentSession ? (
              <>
                <span>{currentSession.device_id}</span>
                <span className="mx-2">|</span>
                <span>{currentSession.app_package}</span>
              </>
            ) : (
              <span>未选择设备</span>
            )}
          </div>

          {/* 时间 */}
          <div className="text-sm text-text-secondary font-mono">
            {new Date().toLocaleTimeString()}
          </div>
        </div>
      </div>
    </footer>
  );
}
```

**Step 4: 修改 App.tsx**

```typescript
// src/App.tsx
import MainWindow from '@/components/layout/MainWindow';
import './index.css';

function App() {
  return <MainWindow />;
}

export default App;
```

**Step 5: 创建全局样式**

```css
/* src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  font-family: 'Microsoft YaHei UI', 'Segoe UI', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: #0a0a0a;
  color: #ffffff;
}

* {
  box-sizing: border-box;
}

/* 霓虹发光效果 */
.neon-glow {
  text-shadow: 0 0 10px currentColor;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #141414;
}

::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #444;
}
```

**Step 6: 验证布局**

```bash
npm run dev
```

访问 http://localhost:3000 应该看到：
- 顶部菜单栏（Insight-Eye Logo + 菜单项）
- 中间主内容区（标题）
- 底部状态栏（监控状态）

**Step 7: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/web-frontend/src/
git commit -m "feat(web): 实现主窗口布局

- 创建 MainWindow 主窗口组件
- 创建 MenuBar 顶部菜单栏
- 创建 StatusBar 底部状态栏
- 实现全局样式（TailwindCSS + 霓虹效果）
- 自动加载设备列表

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 6: 实现设备选择面板

**Files:**
- Create: `src/components/panels/DeviceSelectionPanel.tsx`

**Step 1: 创建设备选择面板**

```typescript
// src/components/panels/DeviceSelectionPanel.tsx
import React, { useState, useEffect } from 'react';
import { useMonitoringStore } from '@/store/monitoringStore';
import { api } from '@/services/api';
import { Device } from '@/types';

export default function DeviceSelectionPanel() {
  const { devices, selectedDevice, selectDevice, isMonitoring } = useMonitoringStore();
  const [appPackage, setAppPackage] = useState('com.example.app');
  const [loading, setLoading] = useState(false);

  const handleRefresh = async () => {
    setLoading(true);
    try {
      const updatedDevices = await api.getDevices();
      useMonitoringStore.getState().setDevices(updatedDevices);
    } catch (error) {
      console.error('Failed to refresh devices:', error);
    } finally {
      setLoading(false);
    }
  };

  const selectedDeviceData = devices.find(d => d.device_id === selectedDevice);

  return (
    <div className="bg-dark-card rounded-lg border border-gray-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-neon-cpu">设备选择</h2>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
        >
          {loading ? '刷新中...' : '刷新设备'}
        </button>
      </div>

      {/* 设备列表 */}
      <div className="space-y-2 mb-6">
        {devices.length === 0 ? (
          <div className="text-center text-text-secondary py-8">
            未检测到设备，请连接设备后点击刷新
          </div>
        ) : (
          devices.map((device) => (
            <div
              key={device.device_id}
              onClick={() => !isMonitoring && selectDevice(device.device_id)}
              className={`p-4 rounded-lg border transition-all cursor-pointer ${
                selectedDevice === device.device_id
                  ? 'border-neon-cpu bg-gray-800'
                  : 'border-gray-800 hover:border-gray-700'
              } ${isMonitoring ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center">
                    <h3 className="font-bold text-lg">{device.device_name || device.device_id}</h3>
                    <span className={`ml-2 px-2 py-1 text-xs rounded ${
                      device.platform === 'android'
                        ? 'bg-green-900 text-green-300'
                        : 'bg-blue-900 text-blue-300'
                    }`}>
                      {device.platform.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-sm text-text-secondary mt-1">{device.device_id}</p>
                </div>
                <div className={`w-3 h-3 rounded-full ${
                  device.status === 'online' ? 'bg-green-500' : 'bg-gray-500'
                }`} />
              </div>
            </div>
          ))
        )}
      </div>

      {/* 应用包名输入 */}
      <div className="border-t border-gray-800 pt-4">
        <label className="block text-sm font-medium text-text-secondary mb-2">
          应用包名 / Bundle ID
        </label>
        <input
          type="text"
          value={appPackage}
          onChange={(e) => setAppPackage(e.target.value)}
          placeholder="com.example.app"
          disabled={isMonitoring}
          className="w-full px-4 py-2 bg-gray-900 border border-gray-800 rounded-lg focus:border-neon-cpu focus:outline-none disabled:opacity-50"
        />
      </div>
    </div>
  );
}
```

**Step 2: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/web-frontend/src/components/panels/
git commit -m "feat(web): 实现设备选择面板

- 创建设备选择面板组件
- 显示设备列表（Android/iOS）
- 支持选择设备和输入应用包名
- 监控中禁用设备选择

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 7: 实现霓虹图表卡片组件

**Files:**
- Create: `src/components/charts/NeonChartCard.tsx`
- Create: `src/components/charts/RealTimeChart.tsx`

**Step 1: 创建实时图表组件**

```typescript
// src/components/charts/RealTimeChart.tsx
import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { MetricCardConfig } from '@/types';

interface RealTimeChartProps {
  data: number[];
  timestamps: string[];
  config: MetricCardConfig;
}

export default function RealTimeChart({ data, timestamps, config }: RealTimeChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // 初始化图表
    chartInstance.current = echarts.init(chartRef.current);

    return () => {
      chartInstance.current?.dispose();
    };
  }, []);

  useEffect(() => {
    if (!chartInstance.current) return;

    const option: echarts.EChartsOption = {
      grid: {
        top: 10,
        left: 10,
        right: 10,
        bottom: 20,
      },
      xAxis: {
        type: 'category',
        data: timestamps.map(t => {
          const date = new Date(t);
          return `${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
        }),
        show: false,
      },
      yAxis: {
        type: 'value',
        min: config.yMin,
        max: config.yMax,
        splitLine: {
          show: true,
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.05)',
          },
        },
        axisLabel: {
          color: '#aaaaaa',
          fontSize: 10,
        },
      },
      series: [
        {
          type: 'line',
          data: data,
          smooth: true,
          symbol: 'none',
          lineStyle: {
            color: config.color,
            width: 2,
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: config.color + '40' },
              { offset: 1, color: config.color + '00' },
            ]),
          },
        },
      ],
      animation: false,
    };

    chartInstance.current.setOption(option);
  }, [data, timestamps, config]);

  return (
    <div ref={chartRef} className="w-full h-full" />
  );
}
```

**Step 2: 创建霓虹图表卡片**

```typescript
// src/components/charts/NeonChartCard.tsx
import React from 'react';
import { MetricCardConfig } from '@/types';
import RealTimeChart from './RealTimeChart';

interface NeonChartCardProps {
  config: MetricCardConfig;
  data: number[];
  timestamps: string[];
}

export default function NeonChartCard({ config, data, timestamps }: NeonChartCardProps) {
  // 计算当前值和统计信息
  const currentValue = data.length > 0 ? data[data.length - 1] : 0;
  const avgValue = data.length > 0
    ? data.reduce((sum, val) => sum + val, 0) / data.length
    : 0;
  const maxValue = data.length > 0 ? Math.max(...data) : 0;

  return (
    <div
      className="relative bg-dark-card rounded-lg p-4 border-t-2 min-h-[180px]"
      style={{ borderColor: config.color }}
    >
      {/* 标题 */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-text-secondary">{config.title}</h3>
        <div className="flex items-center space-x-2 text-xs text-text-secondary">
          <span>最大: {maxValue.toFixed(config.decimals)}</span>
          <span>平均: {avgValue.toFixed(config.decimals)}</span>
        </div>
      </div>

      {/* 当前值 */}
      <div className="mb-2">
        <span
          className="text-4xl font-bold neon-glow"
          style={{ color: config.color }}
        >
          {currentValue.toFixed(config.decimals)}
        </span>
        <span className="ml-1 text-sm text-text-secondary">{config.unit}</span>
      </div>

      {/* 图表 */}
      <div className="absolute bottom-4 left-4 right-4 top-20">
        <RealTimeChart
          data={data}
          timestamps={timestamps}
          config={config}
        />
      </div>
    </div>
  );
}
```

**Step 3: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/web-frontend/src/components/charts/
git commit -m "feat(web): 实现霓虹图表卡片组件

- 创建 RealTimeChart ECharts 实时图表组件
- 创建 NeonChartCard 霓虹风格卡片组件
- 实现渐变填充和发光效果
- 显示当前值、最大值、平均值

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 8: 实现监控面板

**Files:**
- Create: `src/components/panels/MonitorPanel.tsx`
- Create: `src/components/widgets/MonitoringControls.tsx`

**Step 1: 创建监控控制组件**

```typescript
// src/components/widgets/MonitoringControls.tsx
import React from 'react';
import { useMonitoringStore } from '@/store/monitoringStore';

export default function MonitoringControls() {
  const {
    selectedDevice,
    isMonitoring,
    startMonitoring,
    stopMonitoring,
  } = useMonitoringStore();

  const [appPackage, setAppPackage] = React.useState('com.example.app');
  const [loading, setLoading] = React.useState(false);

  const handleStart = async () => {
    if (!selectedDevice) {
      alert('请先选择设备');
      return;
    }

    setLoading(true);
    try {
      await startMonitoring(selectedDevice, appPackage);
    } catch (error) {
      alert('启动监控失败: ' + error);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await stopMonitoring();
    } catch (error) {
      alert('停止监控失败: ' + error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-between mb-6">
      <div className="flex-1">
        <input
          type="text"
          value={appPackage}
          onChange={(e) => setAppPackage(e.target.value)}
          placeholder="应用包名 (如: com.example.app)"
          disabled={isMonitoring}
          className="w-full px-4 py-2 bg-gray-900 border border-gray-800 rounded-lg focus:border-neon-cpu focus:outline-none disabled:opacity-50"
        />
      </div>

      <div className="flex items-center space-x-4 ml-4">
        {!isMonitoring ? (
          <button
            onClick={handleStart}
            disabled={!selectedDevice || loading}
            className="px-6 py-2 bg-neon-cpu text-black font-bold rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? '启动中...' : '开始监控'}
          </button>
        ) : (
          <button
            onClick={handleStop}
            disabled={loading}
            className="px-6 py-2 bg-red-500 text-white font-bold rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50"
          >
            {loading ? '停止中...' : '停止监控'}
          </button>
        )}
      </div>
    </div>
  );
}
```

**Step 2: 创建监控面板**

```typescript
// src/components/panels/MonitorPanel.tsx
import React from 'react';
import { useMonitoringStore } from '@/store/monitoringStore';
import { ALL_METRIC_CARDS } from '@/config/metricCards';
import NeonChartCard from '@/components/charts/NeonChartCard';
import MonitoringControls from '@/components/widgets/MonitoringControls';

export default function MonitorPanel() {
  const { metricsData, timestamps, isMonitoring } = useMonitoringStore();

  return (
    <div className="space-y-6">
      {/* 控制栏 */}
      <MonitoringControls />

      {/* 监控状态 */}
      {!isMonitoring && (
        <div className="text-center py-12 text-text-secondary">
          <p className="text-lg">选择设备并点击"开始监控"开始性能监控</p>
        </div>
      )}

      {/* 图表网格 */}
      {isMonitoring && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {ALL_METRIC_CARDS
            .filter(card => card.enabled)
            .sort((a, b) => a.priority - b.priority)
            .map((card) => (
              <NeonChartCard
                key={card.metricId}
                config={card}
                data={metricsData[card.metricId] || []}
                timestamps={timestamps}
              />
            ))}
        </div>
      )}
    </div>
  );
}
```

**Step 3: 更新主窗口集成监控面板**

```typescript
// src/components/layout/MainWindow.tsx
import React, { useEffect } from 'react';
import { useMonitoringStore } from '@/store/monitoringStore';
import { api } from '@/services/api';
import MenuBar from './MenuBar';
import StatusBar from './StatusBar';
import DeviceSelectionPanel from '../panels/DeviceSelectionPanel';
import MonitorPanel from '../panels/MonitorPanel';

export default function MainWindow() {
  const { setDevices } = useMonitoringStore();

  useEffect(() => {
    const loadDevices = async () => {
      try {
        const devices = await api.getDevices();
        setDevices(devices);
      } catch (error) {
        console.error('Failed to load devices:', error);
      }
    };

    loadDevices();
  }, [setDevices]);

  return (
    <div className="min-h-screen bg-dark-bg text-text-primary pb-8">
      <MenuBar />

      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* 左侧：设备选择 */}
          <div className="lg:col-span-1">
            <DeviceSelectionPanel />
          </div>

          {/* 右侧：监控面板 */}
          <div className="lg:col-span-3">
            <MonitorPanel />
          </div>
        </div>
      </div>

      <StatusBar />
    </div>
  );
}
```

**Step 4: 验证功能**

```bash
npm run dev
```

访问 http://localhost:3000 应该看到：
- 左侧设备选择面板
- 右侧监控控制按钮和 2x2 图表网格
- 开始监控后实时数据显示

**Step 5: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/web-frontend/src/
git commit -m "feat(web): 实现监控面板和控制组件

- 创建 MonitoringControls 监控控制组件
- 创建 MonitorPanel 2x2 图表网格
- 集成设备选择和监控面板到主窗口
- 实现完整的监控流程

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 9: 实现会话列表和历史记录

**Files:**
- Create: `src/components/panels/ReportPanel.tsx`
- Create: `src/components/widgets/SessionList.tsx`

**Step 1: 创建会话列表组件**

```typescript
// src/components/widgets/SessionList.tsx
import React, { useEffect, useState } from 'react';
import { api } from '@/services/api';
import { Session } from '@/types';

export default function SessionList() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);

  const loadSessions = async () => {
    setLoading(true);
    try {
      const data = await api.getSessions(50);
      setSessions(data);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'text-green-400';
      case 'stopped': return 'text-gray-400';
      case 'error': return 'text-red-400';
      default: return 'text-yellow-400';
    }
  };

  return (
    <div className="bg-dark-card rounded-lg border border-gray-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-neon-cpu">会话历史</h2>
        <button
          onClick={loadSessions}
          disabled={loading}
          className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
        >
          {loading ? '加载中...' : '刷新'}
        </button>
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="text-center text-text-secondary py-8">
            暂无会话记录
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className="p-4 bg-gray-900 rounded-lg border border-gray-800 hover:border-gray-700 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold">Session #{session.id}</span>
                <span className={`text-sm ${getStatusColor(session.status)}`}>
                  {session.status.toUpperCase()}
                </span>
              </div>
              <div className="text-sm text-text-secondary space-y-1">
                <p>设备: {session.device_id}</p>
                <p>应用: {session.app_package}</p>
                <p>开始: {formatDate(session.start_time)}</p>
                {session.end_time && (
                  <p>结束: {formatDate(session.end_time)}</p>
                )}
                {session.duration && (
                  <p>时长: {Math.floor(session.duration / 60)}分{session.duration % 60}秒</p>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

**Step 2: 创建报告面板**

```typescript
// src/components/panels/ReportPanel.tsx
import React from 'react';
import SessionList from '../widgets/SessionList';

export default function ReportPanel() {
  return (
    <div className="space-y-6">
      <div className="bg-dark-card rounded-lg border border-gray-800 p-6">
        <h2 className="text-2xl font-bold text-neon-cpu mb-4">性能报告</h2>
        <p className="text-text-secondary">
          查看历史监控会话和性能数据报告
        </p>
      </div>

      <SessionList />
    </div>
  );
}
```

**Step 3: 添加标签页切换**

```typescript
// src/components/layout/MainWindow.tsx
import React, { useEffect, useState } from 'react';
import { useMonitoringStore } from '@/store/monitoringStore';
import { api } from '@/services/api';
import MenuBar from './MenuBar';
import StatusBar from './StatusBar';
import DeviceSelectionPanel from '../panels/DeviceSelectionPanel';
import MonitorPanel from '../panels/MonitorPanel';
import ReportPanel from '../panels/ReportPanel';

type Tab = 'monitor' | 'report';

export default function MainWindow() {
  const { setDevices } = useMonitoringStore();
  const [activeTab, setActiveTab] = useState<Tab>('monitor');

  useEffect(() => {
    const loadDevices = async () => {
      try {
        const devices = await api.getDevices();
        setDevices(devices);
      } catch (error) {
        console.error('Failed to load devices:', error);
      }
    };

    loadDevices();
  }, [setDevices]);

  return (
    <div className="min-h-screen bg-dark-bg text-text-primary pb-8">
      <MenuBar />

      {/* 标签页切换 */}
      <div className="bg-dark-card border-b border-gray-800">
        <div className="container mx-auto px-4">
          <div className="flex space-x-8">
            <button
              onClick={() => setActiveTab('monitor')}
              className={`py-4 px-2 border-b-2 transition-colors ${
                activeTab === 'monitor'
                  ? 'border-neon-cpu text-neon-cpu'
                  : 'border-transparent text-text-secondary hover:text-white'
              }`}
            >
              监控面板
            </button>
            <button
              onClick={() => setActiveTab('report')}
              className={`py-4 px-2 border-b-2 transition-colors ${
                activeTab === 'report'
                  ? 'border-neon-cpu text-neon-cpu'
                  : 'border-transparent text-text-secondary hover:text-white'
              }`}
            >
              报告中心
            </button>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-6">
        {activeTab === 'monitor' ? (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <div className="lg:col-span-1">
              <DeviceSelectionPanel />
            </div>
            <div className="lg:col-span-3">
              <MonitorPanel />
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto">
            <ReportPanel />
          </div>
        )}
      </div>

      <StatusBar />
    </div>
  );
}
```

**Step 4: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/web-frontend/src/
git commit -m "feat(web): 实现会话列表和报告面板

- 创建 SessionList 会话历史组件
- 创建 ReportPanel 报告面板
- 添加标签页切换（监控/报告）
- 显示历史监控记录

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 10: 生产构建和优化

**Files:**
- Create: `insight_eyes/web-frontend/.env.production`
- Modify: `insight_eyes/web-frontend/package.json`
- Create: `insight_eyes/web-frontend/README.md`

**Step 1: 创建生产环境配置**

```bash
# insight_eyes/web-frontend/.env.production
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

**Step 2: 更新 package.json 添加构建脚本**

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0"
  }
}
```

**Step 3: 创建 README**

```markdown
# Insight-Eye Web 前端

## 开发

```bash
npm install
npm run dev
```

访问 http://localhost:3000

## 构建

```bash
npm run build
```

构建产物在 `dist/` 目录

## 部署

将 `dist/` 目录部署到静态文件服务器

## 技术栈

- React 18 + TypeScript
- Vite
- ECharts
- Zustand
- TailwindCSS
```

**Step 4: 执行生产构建**

```bash
cd insight_eyes/web-frontend
npm run build
```

**Step 5: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/web-frontend/
git commit -m "feat(web): 完成生产构建配置

- 添加生产环境配置
- 更新 package.json 脚本
- 创建 README 文档
- 验证生产构建

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Phase 3 总结

### 完成的工作

1. ✅ 创建 React + Vite 项目
2. ✅ 配置 TailwindCSS 霓虹主题
3. ✅ 实现主窗口布局（菜单栏、状态栏）
4. ✅ 实现设备选择面板
5. ✅ 实现监控面板（2x2 网格）
6. ✅ 实现霓虹图表卡片（ECharts）
7. ✅ 实现 Zustand 状态管理
8. ✅ 集成 WebSocket 实时数据
9. ✅ 实现会话列表和报告面板

### 技术栈

- **前端框架**: React 18 + TypeScript
- **构建工具**: Vite
- **图表库**: ECharts
- **状态管理**: Zustand
- **样式**: TailwindCSS
- **实时通信**: WebSocket

### 验收标准

- [ ] Web 应用正常启动
- [ ] 设备列表正常显示
- [ ] 可以选择设备和启动监控
- [ ] 实时图表正常显示
- [ ] WebSocket 数据实时更新
- [ ] 会话历史正常显示
- [ ] 生产构建成功

---

**计划版本**: 1.0
**创建日期**: 2025-01-29
**预计工时**: 2周（80小时）
