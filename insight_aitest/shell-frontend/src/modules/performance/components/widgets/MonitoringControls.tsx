import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { useMonitoringStore } from '@/modules/performance/store/monitoringStore';
import { useProjectStore } from '@/shared/store/projectStore';

export default function MonitoringControls() {
  const { t } = useTranslation();
  const {
    selectedDevice,
    isMonitoring,
    startMonitoring,
    stopMonitoring,
    samplingInterval,
  } = useMonitoringStore();
  const currentProjectId = useProjectStore((s) => s.currentProjectId);

  const [appPackage, setAppPackage] = useState('com.example.app');
  const [loading, setLoading] = useState(false);

  const handleStart = async () => {
    if (!selectedDevice) {
      toast.warning(t('device.selectDeviceFirst'));
      return;
    }

    setLoading(true);
    try {
      await startMonitoring(selectedDevice, appPackage, 'android', samplingInterval, currentProjectId);
    } catch (error) {
      toast.error(`${t('device.startMonitorFailed')}: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await stopMonitoring();
    } catch (error) {
      toast.error(`${t('device.stopMonitorFailed')}: ${error}`);
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
            backgroundColor: "var(--bg-card)",
            color: "var(--text-primary)",
            border: '1px solid var(--bg-card)',
          }}
          onFocus={(e) => e.currentTarget.style.borderColor = "var(--accent)"}
          onBlur={(e) => e.currentTarget.style.borderColor = "var(--bg-card)"}
        />
      </div>

      <div className="flex items-center space-x-4 ml-4">
        {!isMonitoring ? (
          <button
            onClick={handleStart}
            disabled={!selectedDevice || loading}
            className="px-6 py-2 font-bold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              backgroundColor: "var(--accent)",
              color: "var(--bg-base)",
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
