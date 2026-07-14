import axios from 'axios';
import type { Device, Session } from '@/shared/types';

const API_BASE_URL = '/api/modules/performance';

// AppInfo 接口定义
export interface AppInfo {
  package_name: string;
  name: string;
  is_running: boolean;
  pid?: number;
  status?: string;
}

// 设备管理 API
export const deviceApi = {
  // 获取设备列表
  async getDevices(): Promise<Device[]> {
    const response = await axios.get(`${API_BASE_URL}/devices`);
    return response.data;
  },

  // 刷新设备列表
  async refreshDevices(): Promise<Device[]> {
    const response = await axios.post(`${API_BASE_URL}/devices/refresh`);
    return response.data;
  },

  // 连接设备
  async connectDevice(deviceId: string): Promise<{ device_id: string; status: string }> {
    const response = await axios.post(`${API_BASE_URL}/devices/${deviceId}/connect`);
    return response.data;
  },

  // 断开设备
  async disconnectDevice(deviceId: string): Promise<{ device_id: string; status: string }> {
    const response = await axios.delete(`${API_BASE_URL}/devices/${deviceId}`);
    return response.data;
  },

  // 获取设备应用列表
  async getDeviceApps(deviceId: string, includeSystem = false): Promise<AppInfo[]> {
    const response = await axios.get(`${API_BASE_URL}/devices/${deviceId}/apps`, {
      params: { include_system: includeSystem },
    });
    return response.data;
  },
};

// MetricsData 接口定义（用于会话指标）
export interface MetricsData {
  id: number;
  session_id: number;
  timestamp: string;
  fps?: number;
  cpu_app?: number;
  memory_pss?: number;
  network_up_speed?: number;
  network_down_speed?: number;
}

// MetricStats 接口定义（用于统计数据）
export interface MetricStats {
  max: number;
  min: number;
  avg: number;
  median: number;
  count: number;
}

// AlertInfo 接口定义（用于告警数据）
export interface AlertInfo {
  id: number;
  session_id: number;
  timestamp: string;
  metric_type: string;
  severity: string;
  description: string;
  threshold?: number;
  current_value?: number;
}

// Statistics 接口定义
export interface Statistics {
  fps?: MetricStats;
  cpu_app?: MetricStats;
  memory_pss?: MetricStats;
  network_up?: MetricStats;
  network_down?: MetricStats;
}

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
  async startMonitoring(
    deviceId: string,
    appPackage: string,
    platform: string = 'android',
    samplingInterval: number = 1000,
    alertThresholds?: { fps: number; memory: number; cpu: number; temperature: number },
    projectId?: number | null
  ): Promise<Session> {
    const response = await axios.post(`${API_BASE_URL}/monitoring/start`, {
      device_id: deviceId,
      app_package: appPackage,
      platform,
      sampling_interval: samplingInterval,
      alert_thresholds: alertThresholds ? {
        fps: alertThresholds.fps,
        memory: alertThresholds.memory,
        cpu: alertThresholds.cpu,
        temperature: alertThresholds.temperature,
      } : undefined,
      project_id: projectId ?? undefined,
    });
    return response.data;
  },

  // 停止监控
  async stopMonitoring(sessionId: number): Promise<{ status: string; session_id: number }> {
    const response = await axios.post(`${API_BASE_URL}/monitoring/stop`, {
      session_id: sessionId,
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

  // 获取会话的指标数据
  async getSessionMetrics(sessionId: number, limit: number = 1000): Promise<MetricsData[]> {
    const response = await axios.get(`${API_BASE_URL}/monitoring/sessions/${sessionId}/metrics`, {
      params: { limit },
    });
    return response.data;
  },

  // 获取会话的统计数据
  async getSessionStatistics(sessionId: number): Promise<Statistics> {
    const response = await axios.get(`${API_BASE_URL}/monitoring/sessions/${sessionId}/statistics`);
    return response.data;
  },

  // 获取会话的告警记录
  async getSessionAlerts(sessionId: number): Promise<AlertInfo[]> {
    const response = await axios.get(`${API_BASE_URL}/monitoring/sessions/${sessionId}/alerts`);
    return response.data;
  },

  // 删除会话
  async deleteSession(sessionId: number): Promise<{ status: string; session_id: number }> {
    const response = await axios.delete(`${API_BASE_URL}/monitoring/sessions/${sessionId}`);
    return response.data;
  },

  // 批量删除会话
  async batchDeleteSessions(sessionIds: number[]): Promise<{ success: number; failed: number; failed_ids: number[] }> {
    const response = await axios.post(`${API_BASE_URL}/monitoring/sessions/batch-delete`, sessionIds);
    return response.data;
  },

  // 健康检查
  async healthCheck(): Promise<{ status: string }> {
    const response = await axios.get('/api/platform/health');
    return response.data;
  },
};
