import { create } from 'zustand';
import type { Device, Session, MetricsData } from '@/types';
import { api } from '@/services/api';

interface BatteryInfo {
  level: string;
  temperature: string;
  capacity: string;
}

// 生成模拟时间序列数据
function generateMockData() {
  const dataPoints = 60; // 60个数据点
  const now = Date.now();
  const timestamps: string[] = [];
  const metricsData: Record<string, number[]> = {
    cpu: [],
    memory: [],
    fps: [],
    network_up: [],
    network_down: [],
  };

  for (let i = 0; i < dataPoints; i++) {
    const time = new Date(now - (dataPoints - i) * 1000);
    timestamps.push(time.toISOString());

    // CPU: 0-100之间的波动数据，模拟真实使用情况
    metricsData.cpu.push(Math.max(5, Math.min(95, 30 + Math.sin(i / 5) * 25 + Math.random() * 20)));

    // Memory: 150-350MB之间波动
    metricsData.memory.push(Math.max(150, Math.min(350, 250 + Math.sin(i / 8) * 80 + Math.random() * 30)));

    // FPS: 55-60之间，偶尔掉帧
    const fpsValue = Math.random() > 0.9 ? Math.floor(Math.random() * 20 + 40) : Math.floor(Math.random() * 5 + 55);
    metricsData.fps.push(fpsValue);

    // Network Upload: 0-50 KB/s
    metricsData.network_up.push(Math.max(0, Math.min(50, Math.random() * 30)));

    // Network Download: 0-200 KB/s
    metricsData.network_down.push(Math.max(0, Math.min(200, Math.random() * 100 + 20)));
  }

  return { timestamps, metricsData };
}

interface MonitoringState {
  // 状态
  devices: Device[];
  selectedDevice: string | null;
  isMonitoring: boolean;
  currentSession: Session | null;
  metricsData: Record<string, number[]>;
  timestamps: string[];
  wsConnection: WebSocket | null;
  batteryInfo: BatteryInfo;

  // Actions
  setDevices: (devices: Device[]) => void;
  selectDevice: (deviceId: string) => void;
  startMonitoring: (deviceId: string, appPackage: string, platform?: string) => Promise<void>;
  stopMonitoring: () => Promise<void>;
  updateMetrics: (data: MetricsData) => void;
  clearMetrics: () => void;
  setBatteryInfo: (info: BatteryInfo) => void;
}

// 生成初始模拟数据
const initialMockData = generateMockData();

export const useMonitoringStore = create<MonitoringState>((set, get) => ({
  // 初始状态 - 使用模拟数据以便UI展示
  devices: [
    {
      device_id: 'ios-device-00008030',
      name: 'iOS Device (00008030)',
      type: 'ios',
      status: 'online',
    },
  ],
  selectedDevice: 'ios-device-00008030',
  isMonitoring: true, // 默认显示监控状态
  currentSession: {
    id: 1,
    device_id: 'ios-device-00008030',
    app_package: 'com.ss.android.ugc.aweme',
    app_name: '抖音',
    platform: 'ios',
    status: 'running',
    start_time: new Date(Date.now() - 60000).toISOString(),
  },
  metricsData: initialMockData.metricsData,
  timestamps: initialMockData.timestamps,
  wsConnection: null,
  batteryInfo: {
    level: '100',
    temperature: '25.0',
    capacity: '--',
  },

  // 设置设备列表
  setDevices: (devices) => set({ devices }),

  // 选择设备
  selectDevice: (deviceId) => set({ selectedDevice: deviceId }),

  // 开始监控
  startMonitoring: async (deviceId, appPackage, platform = 'android') => {
    // C1: 防止重复启动监控
    const currentState = get();
    if (currentState.isMonitoring) {
      console.warn('Monitoring is already active. Stop current session first.');
      throw new Error('Monitoring is already active');
    }

    try {
      const session: Session = await api.startMonitoring(deviceId, appPackage, platform);

      // I1: 使用环境变量配置 WebSocket URL，否则使用相对路径通过代理
      const wsUrl = import.meta.env.VITE_WS_URL || '';
      // 建立 WebSocket 连接（相对路径会通过 Vite 代理到后端）
      const ws = new WebSocket(wsUrl ? `${wsUrl}/ws/monitoring/${session.id}` : `/ws/monitoring/${session.id}`);

      ws.onopen = () => {
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        // C2: 添加 WebSocket 消息验证
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'metrics' && message.data) {
            get().updateMetrics(message.data);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        // 当 WebSocket 意外断开时，清除监控状态
        const state = get();
        if (state.wsConnection === ws) {
          set({
            isMonitoring: false,
            wsConnection: null,
          });
        }
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

    // I2: 调用 API 停止监控，只有在成功后才清除状态
    if (currentSession) {
      try {
        await api.stopMonitoring(currentSession.id);

        // 只有在 API 调用成功后才清除状态
        set({
          isMonitoring: false,
          currentSession: null,
          wsConnection: null,
        });
      } catch (error) {
        console.error('Error stopping monitoring:', error);
        // API 调用失败时重新抛出错误，不清除状态
        throw error;
      }
    } else {
      // 如果没有当前会话，直接清除状态
      set({
        isMonitoring: false,
        currentSession: null,
        wsConnection: null,
      });
    }
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

  // 设置电池信息
  setBatteryInfo: (info) => set({ batteryInfo: info }),
}));
