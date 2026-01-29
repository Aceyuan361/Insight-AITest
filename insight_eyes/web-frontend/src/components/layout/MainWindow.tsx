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
