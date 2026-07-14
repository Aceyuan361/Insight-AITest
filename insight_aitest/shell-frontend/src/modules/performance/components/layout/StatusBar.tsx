import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useMonitoringStore } from '@/modules/performance/store/monitoringStore';

export default function StatusBar() {
  const { t } = useTranslation();
  const { isMonitoring, currentSession } = useMonitoringStore();
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    // 每秒更新时间
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  return (
    <footer className="fixed bottom-0 left-0 right-0 bg-dark-card border-t border-gray-800">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-8">
          {/* 监控状态 */}
          <div className="flex items-center text-sm">
            {isMonitoring ? (
              <>
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                <span className="ml-2 text-text-secondary">
                  {t('menu.monitoring')} - Session #{currentSession?.id}
                </span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 bg-gray-500 rounded-full"></span>
                <span className="ml-2 text-text-secondary">{t('menu.notMonitoring')}</span>
              </>
            )}
          </div>

          {/* 设备信息 */}
          <div className="text-sm text-text-secondary">
            {currentSession ? (
              <>
                <span>{currentSession.device_id}</span>
                <span className="mx-2">|</span>
                <span>{currentSession.app_package}</span>
              </>
            ) : (
              <span>{t('statusBar.noDevice')}</span>
            )}
          </div>

          {/* 时间 */}
          <div className="text-sm text-text-secondary font-mono">
            {currentTime.toLocaleTimeString()}
          </div>
        </div>
      </div>
    </footer>
  );
}
