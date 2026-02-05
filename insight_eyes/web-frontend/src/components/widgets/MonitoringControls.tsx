import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMonitoringStore } from '@/store/monitoringStore';

export default function MonitoringControls() {
  const { t } = useTranslation();
  const {
    selectedDevice,
    isMonitoring,
    startMonitoring,
    stopMonitoring,
    samplingInterval,
  } = useMonitoringStore();

  const [appPackage, setAppPackage] = useState('com.example.app');
  const [loading, setLoading] = useState(false);

  const handleStart = async () => {
    if (!selectedDevice) {
      alert(t('device.selectDeviceFirst'));
      return;
    }

    setLoading(true);
    try {
      await startMonitoring(selectedDevice, appPackage, 'android', samplingInterval);
    } catch (error) {
      alert(t('device.startMonitorFailed') + ': ' + error);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await stopMonitoring();
    } catch (error) {
      alert(t('device.stopMonitorFailed') + ': ' + error);
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
          placeholder={t('device.appPackagePlaceholder')}
          disabled={isMonitoring}
          className="w-full px-4 py-2 border rounded-lg focus:outline-none disabled:opacity-50 transition-colors"
          style={{
            backgroundColor: '#121824',
            color: '#e0e6ed',
            border: '1px solid #1a1f2e',
          }}
          onFocus={(e) => e.currentTarget.style.borderColor = '#00d4ff'}
          onBlur={(e) => e.currentTarget.style.borderColor = '#1a1f2e'}
        />
      </div>

      <div className="flex items-center space-x-4 ml-4">
        {!isMonitoring ? (
          <button
            onClick={handleStart}
            disabled={!selectedDevice || loading}
            className="px-6 py-2 font-bold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              backgroundColor: '#00d4ff',
              color: '#0a0e17',
            }}
          >
            {loading ? t('device.starting') : t('device.startMonitor')}
          </button>
        ) : (
          <button
            onClick={handleStop}
            disabled={loading}
            className="px-6 py-2 bg-red-500 text-white font-bold rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50"
          >
            {loading ? t('device.stopping') : t('device.stopMonitor')}
          </button>
        )}
      </div>
    </div>
  );
}
