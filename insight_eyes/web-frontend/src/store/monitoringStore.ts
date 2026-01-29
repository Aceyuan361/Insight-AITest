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
