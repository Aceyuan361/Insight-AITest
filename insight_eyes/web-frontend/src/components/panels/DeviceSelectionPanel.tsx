import React, { useState } from 'react';
import { useMonitoringStore } from '@/store/monitoringStore';
import { api } from '@/services/api';

export default function DeviceSelectionPanel() {
  const { devices, selectedDevice, selectDevice, isMonitoring } = useMonitoringStore();
  const [appPackage, setAppPackage] = useState('com.example.app');
  const [loading, setLoading] = useState(false);

  const handleRefresh = async () => {
    setLoading(true);
    try {
      const updatedDevices = await api.getDevices();
      useMonitoringStore.getState().setDevices(updatedDevices);
    } catch (error) {
      console.error('Failed to refresh devices:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-dark-card rounded-lg border border-gray-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-neon-cpu">设备选择</h2>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
        >
          {loading ? '刷新中...' : '刷新设备'}
        </button>
      </div>

      {/* 设备列表 */}
      <div className="space-y-2 mb-6">
        {devices.length === 0 ? (
          <div className="text-center text-text-secondary py-8">
            未检测到设备，请连接设备后点击刷新
          </div>
        ) : (
          devices.map((device) => (
            <div
              key={device.device_id}
              onClick={() => !isMonitoring && selectDevice(device.device_id)}
              className={`p-4 rounded-lg border transition-all cursor-pointer ${
                selectedDevice === device.device_id
                  ? 'border-neon-cpu bg-gray-800'
                  : 'border-gray-800 hover:border-gray-700'
              } ${isMonitoring ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center">
                    <h3 className="font-bold text-lg">{device.device_name || device.device_id}</h3>
                    <span className={`ml-2 px-2 py-1 text-xs rounded ${
                      device.platform === 'android'
                        ? 'bg-green-900 text-green-300'
                        : 'bg-blue-900 text-blue-300'
                    }`}>
                      {device.platform.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-sm text-text-secondary mt-1">{device.device_id}</p>
                </div>
                <div className={`w-3 h-3 rounded-full ${
                  device.status === 'online' ? 'bg-green-500' : 'bg-gray-500'
                }`} />
              </div>
            </div>
          ))
        )}
      </div>

      {/* 应用包名输入 */}
      <div className="border-t border-gray-800 pt-4">
        <label className="block text-sm font-medium text-text-secondary mb-2">
          应用包名 / Bundle ID
        </label>
        <input
          type="text"
          value={appPackage}
          onChange={(e) => setAppPackage(e.target.value)}
          placeholder="com.example.app"
          disabled={isMonitoring}
          className="w-full px-4 py-2 bg-gray-900 border border-gray-800 rounded-lg focus:border-neon-cpu focus:outline-none disabled:opacity-50"
        />
      </div>
    </div>
  );
}
