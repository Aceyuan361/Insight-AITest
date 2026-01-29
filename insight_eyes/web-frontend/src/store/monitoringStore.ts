import { create } from 'zustand';
import { Device, Session, MetricsData } from '@/types';
import { api } from '@/services/api';

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
  startMonitoring: (deviceId: string, appPackage: string, platform?: string) => Promise<void>;
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
  startMonitoring: async (deviceId, appPackage, platform = 'android') => {
    // C1: 防止重复启动监控
    const currentState = get();
    if (currentState.isMonitoring) {
      console.warn('Monitoring is already active. Stop current session first.');
      throw new Error('Monitoring is already active');
    }

    try {
      const session: Session = await api.startMonitoring(deviceId, appPackage, platform);

      // I1: 使用环境变量配置 WebSocket URL
      const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
      // 建立 WebSocket 连接
      const ws = new WebSocket(`${wsUrl}/ws/monitoring/${session.id}`);

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
}));
