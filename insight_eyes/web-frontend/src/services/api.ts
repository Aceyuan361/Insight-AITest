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
