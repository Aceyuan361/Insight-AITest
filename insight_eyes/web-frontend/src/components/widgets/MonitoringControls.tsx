import { useState } from 'react';
import { useMonitoringStore } from '@/store/monitoringStore';

export default function MonitoringControls() {
  const {
    selectedDevice,
    isMonitoring,
    startMonitoring,
    stopMonitoring,
  } = useMonitoringStore();

  const [appPackage, setAppPackage] = useState('com.example.app');
  const [loading, setLoading] = useState(false);

  const handleStart = async () => {
    if (!selectedDevice) {
      alert('请先选择设备');
      return;
    }

    setLoading(true);
    try {
      await startMonitoring(selectedDevice, appPackage);
    } catch (error) {
      alert('启动监控失败: ' + error);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await stopMonitoring();
    } catch (error) {
      alert('停止监控失败: ' + error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-between mb-6">
      <div className="flex-1">
        <input
          type="text"
          value={appPackage}
          onChange={(e) => setAppPackage(e.target.value)}
          placeholder="应用包名 (如: com.example.app)"
          disabled={isMonitoring}
          className="w-full px-4 py-2 bg-gray-900 border border-gray-800 rounded-lg focus:border-neon-cpu focus:outline-none disabled:opacity-50"
        />
      </div>

      <div className="flex items-center space-x-4 ml-4">
        {!isMonitoring ? (
          <button
            onClick={handleStart}
            disabled={!selectedDevice || loading}
            className="px-6 py-2 bg-neon-cpu text-black font-bold rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? '启动中...' : '开始监控'}
          </button>
        ) : (
          <button
            onClick={handleStop}
            disabled={loading}
            className="px-6 py-2 bg-red-500 text-white font-bold rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50"
          >
            {loading ? '停止中...' : '停止监控'}
          </button>
        )}
      </div>
    </div>
  );
}
