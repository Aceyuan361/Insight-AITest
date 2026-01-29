import React, { useEffect, useState } from 'react';
import { useMonitoringStore } from '@/store/monitoringStore';
import { api } from '@/services/api';
import MenuBar from './MenuBar';
import StatusBar from './StatusBar';
import DeviceSelectionPanel from '../panels/DeviceSelectionPanel';

export default function MainWindow() {
  const { setDevices } = useMonitoringStore();
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    // 加载设备列表
    const loadDevices = async () => {
      try {
        const devices = await api.getDevices();
        setDevices(devices);
        setLoadError(null);
      } catch (error) {
        console.error('Failed to load devices:', error);
        setLoadError('无法加载设备列表，请检查后端服务是否正常运行');
      }
    };

    loadDevices();
  }, [setDevices]);

  return (
    <div className="min-h-screen bg-dark-bg text-text-primary">
      <MenuBar />
      <div className="container mx-auto px-4 py-6 pb-12">
        {/* 错误提示 */}
        {loadError && (
          <div className="mb-4 p-4 bg-red-900/30 border border-red-700 rounded-lg">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-red-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span className="text-red-300">{loadError}</span>
            </div>
          </div>
        )}

        {/* 主内容区域 */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-1">
            <DeviceSelectionPanel />
          </div>
          <div className="lg:col-span-3">
            {/* MonitorPanel will be added in next task */}
          </div>
        </div>
      </div>
      <StatusBar />
    </div>
  );
}
