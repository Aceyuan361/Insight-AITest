import { create } from 'zustand';
import type { Device, Session, MetricsData } from '@/types';
import { api } from '@/services/api';
import { exportHtmlReport } from '@/services/htmlExporter';

interface BatteryInfo {
  level: string;
  temperature: string;
  capacity: string;
}

interface AlarmRecord {
  id: string;
  time: string;
  level: '严重' | '警告';
  content: string;
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
  alarms: AlarmRecord[];
  enabledMetricIds: string[];  // 启用的指标ID列表
  samplingInterval: number;  // 采样间隔（毫秒）

  // Actions
  setDevices: (devices: Device[]) => void;
  selectDevice: (deviceId: string) => void;
  startMonitoring: (deviceId: string, appPackage: string, platform?: string, samplingInterval?: number) => Promise<void>;
  stopMonitoring: () => Promise<void>;
  updateMetrics: (data: MetricsData) => void;
  clearMetrics: () => void;
  setBatteryInfo: (info: BatteryInfo) => void;
  addAlarm: (alarm: AlarmRecord) => void;
  clearAlarms: () => void;
  setEnabledMetrics: (metricIds: string[]) => void;  // 新增
  setSamplingInterval: (interval: number) => void;  // 新增
}

export const useMonitoringStore = create<MonitoringState>((set, get) => ({
  // 初始状态 - 从空状态开始，让用户从真实设备列表中选择
  devices: [],
  selectedDevice: null,
  isMonitoring: false,
  currentSession: null,
  metricsData: {
    cpu: [],
    memory: [],
    fps: [],
    network_up: [],
    network_down: [],
    gpu: [],  // 新增GPU
  },
  timestamps: [],
  wsConnection: null,
  batteryInfo: {
    level: '--',
    temperature: '--',
    capacity: '--',
  },
  alarms: [],
  enabledMetricIds: ['cpu', 'memory', 'fps', 'network_up', 'network_down'],  // 默认启用前5个
  samplingInterval: 1000,  // 默认1秒

  // 设置设备列表
  setDevices: (devices) => set({ devices }),

  // 选择设备
  selectDevice: (deviceId) => set({ selectedDevice: deviceId }),

  // 设置采样间隔
  setSamplingInterval: (interval) => set({ samplingInterval: interval }),

  // 开始监控
  startMonitoring: async (deviceId, appPackage, platform = 'android', samplingIntervalParam) => {
    // C1: 防止重复启动监控
    const currentState = get();
    if (currentState.isMonitoring) {
      console.warn('Monitoring is already active. Stop current session first.');
      throw new Error('Monitoring is already active');
    }

    try {
      // 使用传入的采样间隔参数，如果没有则使用store中的默认值
      const interval = samplingIntervalParam ?? currentState.samplingInterval;
      const session: Session = await api.startMonitoring(deviceId, appPackage, platform, interval);

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

  // 停止监控（带数据统计和 HTML 导出）
  stopMonitoring: async (autoExport = true) => {
    const { currentSession, wsConnection, timestamps } = get();

    // 关闭 WebSocket
    if (wsConnection) {
      wsConnection.close();
    }

    // I2: 调用 API 停止监控，只有在成功后才清除状态
    if (currentSession) {
      try {
        // 1. 停止监控
        await api.stopMonitoring(currentSession.id);

        // 2. 获取统计数据和导出 HTML 报告（桌面版功能）
        if (autoExport && timestamps.length > 0) {
          try {
            // 获取会话详情、指标数据和设备信息
            const [sessionDetail, metrics, device, alerts] = await Promise.all([
              api.getSession(currentSession.id),
              api.getSessionMetrics(currentSession.id),
              api.getDevice(currentSession.device_id).catch(() => null),
              api.getSessionAlerts(currentSession.id).catch(() => []),
            ]);

            // 导出 HTML 报告
            await exportHtmlReport(sessionDetail, metrics, device, alerts);
            console.log('HTML report exported successfully');
          } catch (exportError) {
            console.warn('Failed to export HTML report:', exportError);
            // 导出失败不影响停止监控流程
          }
        }

        // 只有在 API 调用成功后才清除状态
        set({
          isMonitoring: false,
          currentSession: null,
          wsConnection: null,
          metricsData: {},
          timestamps: [],
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

  // 添加告警
  addAlarm: (alarm) => set((state) => ({
    alarms: [...state.alarms, alarm],
  })),

  // 清除所有告警
  clearAlarms: () => set({ alarms: [] }),

  // 设置启用的指标列表
  setEnabledMetrics: (metricIds) => set({ enabledMetricIds: metricIds }),
}));
