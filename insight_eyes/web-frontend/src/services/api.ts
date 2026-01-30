import axios from 'axios';
import type { Device, Session } from '@/types';

const API_BASE_URL = '/api';

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
