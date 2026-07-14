import { create } from 'zustand';
import type { Device, Session, MetricsData } from '@/shared/types';
import { api } from '@/shared/api/api';

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
  activeTab: 'monitor' | 'report';  // 当前激活的标签页
  lastStoppedSessionId: number | null;  // 最近停止的会话ID

  // Actions
  setDevices: (devices: Device[]) => void;
  selectDevice: (deviceId: string) => void;
  startMonitoring: (deviceId: string, appPackage: string, platform?: string, samplingInterval?: number, projectId?: number | null) => Promise<void>;
  stopMonitoring: () => Promise<void>;
  updateMetrics: (data: MetricsData) => void;
  clearMetrics: () => void;
  setBatteryInfo: (info: BatteryInfo) => void;
  addAlarm: (alarm: AlarmRecord) => void;
  clearAlarms: () => void;
  setEnabledMetrics: (metricIds: string[]) => void;  // 新增
  setSamplingInterval: (interval: number) => void;  // 新增
  setActiveTab: (tab: 'monitor' | 'report') => void;  // 新增
  clearLastStoppedSessionId: () => void;  // 清除最近停止的会话ID
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
  activeTab: 'monitor' as 'monitor' | 'report',  // 当前激活的标签页
  lastStoppedSessionId: null,  // 最近停止的会话ID

  // 设置设备列表
  setDevices: (devices) => set({ devices }),

  // 选择设备
  selectDevice: (deviceId) => set({ selectedDevice: deviceId }),

  // 设置采样间隔
  setSamplingInterval: (interval) => set({ samplingInterval: interval }),

  // 开始监控
  startMonitoring: async (deviceId, appPackage, platform = 'android', samplingIntervalParam, projectId?) => {
    // C1: 防止重复启动监控
    const currentState = get();
    if (currentState.isMonitoring) {
      console.warn('Monitoring is already active. Stop current session first.');
      throw new Error('Monitoring is already active');
    }

    try {
      // 使用传入的采样间隔参数，如果没有则使用store中的默认值
      const interval = samplingIntervalParam ?? currentState.samplingInterval;

      // 获取告警阈值（从 configManager 加载用户配置的阈值）
      const { configManager } = await import('@/shared/utils/configManager');
      const thresholds = configManager.getAlertThresholds();

      console.log('启动监控，使用告警阈值:', thresholds);

      const session: Session = await api.startMonitoring(deviceId, appPackage, platform, interval, thresholds, projectId);

      // I1: 使用环境变量配置 WebSocket URL，否则使用相对路径通过代理
      const wsUrl = import.meta.env.VITE_WS_URL || '';
      // 建立 WebSocket 连接（相对路径会通过 Vite 代理到后端）
      const ws = new WebSocket(wsUrl ? `${wsUrl}/api/modules/performance/ws/monitoring/${session.id}` : `/api/modules/performance/ws/monitoring/${session.id}`);

      ws.onopen = () => {
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        // C2: 添加 WebSocket 消息验证
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'metrics' && message.data) {
            // 检查是否为告警数据
            if (message.data.is_alert && message.data.alert_data) {
              // 添加告警到列表
              const alert = message.data.alert_data;
              get().addAlarm({
                id: String(alert.id),
                time: alert.time,
                level: alert.level,
                content: alert.content,
              });
              console.log('收到告警:', alert);
            } else {
              // 正常指标数据
              get().updateMetrics(message.data);
            }
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

  // 停止监控（保存数据，跳转到测试报告）
  stopMonitoring: async () => {
    const { currentSession, wsConnection } = get();

    // 关闭 WebSocket
    if (wsConnection) {
      wsConnection.close();
    }

    // 调用 API 停止监控
    if (currentSession) {
      try {
        // 停止监控并保存数据到数据库
        await api.stopMonitoring(currentSession.id);

        // 跳转到测试报告页面（选中当前会话）
        set({
          isMonitoring: false,
          currentSession: null,
          wsConnection: null,
          metricsData: {},
          timestamps: [],
          activeTab: 'report',  // 切换到测试报告标签页
          lastStoppedSessionId: currentSession.id,  // 记录刚停止的会话ID
        });

        console.log(`监控已停止，会话ID: ${currentSession.id}`);
      } catch (error) {
        console.error('Error stopping monitoring:', error);
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
      if (key !== 'timestamp' && key !== 'battery' && key !== 'temperature' && typeof value === 'number') {
        if (!newMetricsData[key]) {
          newMetricsData[key] = [];
        }

        // 问题1修复：过滤iOS启动时的初始0值数据
        // 对于CPU和内存指标，只有当有非0数据时才开始记录
        // 这避免了iOS sysmon启动延迟（约2秒）导致的曲线异常
        const shouldSkip = (
          (key === 'cpu_app' || key === 'cpu' || key === 'memory_pss' || key === 'memory') &&
          value === 0 &&
          newMetricsData[key].length === 0
        );

        if (!shouldSkip) {
          newMetricsData[key] = [...newMetricsData[key], value].slice(-100); // 保留最近100个数据点
        }
      }
    });

    // 保留最近100个时间戳
    const trimmedTimestamps = newTimestamps.slice(-100);

    // 处理电池信息更新
    const batteryInfo = state.batteryInfo;
    if (data.battery !== undefined || data.temperature !== undefined) {
      batteryInfo.level = data.battery !== undefined && data.battery !== null ? `${data.battery}%` : '--';
      batteryInfo.temperature = data.temperature !== undefined && data.temperature !== null ? `${data.temperature}°C` : '--';
      batteryInfo.capacity = '--';  // 容量信息暂未采集
    }

    return {
      metricsData: newMetricsData,
      timestamps: trimmedTimestamps,
      batteryInfo,
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

  // 设置当前激活的标签页
  setActiveTab: (tab) => set({ activeTab: tab }),

  // 清除最近停止的会话ID
  clearLastStoppedSessionId: () => set({ lastStoppedSessionId: null }),
}));
