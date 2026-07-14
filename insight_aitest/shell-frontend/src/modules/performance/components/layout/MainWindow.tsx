import { useState, useEffect } from 'react';
import { useMonitoringStore } from '@/modules/performance/store/monitoringStore';
import { useIsMobile } from '@/shared/hooks/useIsMobile';
import MenuBar from './MenuBar';
import DeviceSelectionPanel from '../panels/DeviceSelectionPanel';
import MonitorPanel from '../panels/MonitorPanel';
import ConfigPanel from '../panels/ConfigPanel';
import ReportPanel from '../panels/ReportPanel';

export default function MainWindow() {
  const { setDevices, activeTab } = useMonitoringStore();
  const isMobile = useIsMobile();
  const [loadError] = useState<string | null>(null);

  useEffect(() => {
    // 暂时注释掉设备加载，使用模拟数据进行UI对比
    // const loadDevices = async () => {
    //   try {
    //     const devices = await api.getDevices();
    //     setDevices(devices);
    //     setLoadError(null);
    //   } catch (error) {
    //     console.error('Failed to load devices:', error);
    //     setLoadError('无法加载设备列表，请检查后端服务是否正常运行');
    //   }
    // };

    // loadDevices();
  }, [setDevices]);

  return (
    <div className="bg-dark-bg text-text-primary" style={{ height: isMobile ? 'auto' : '100vh', backgroundColor: "var(--bg-base)", display: 'flex', flexDirection: 'column' }}>
      <MenuBar />
      <div className="flex-1 overflow-hidden" style={{ paddingTop: '4px', paddingBottom: '4px' }}>
        {/* 错误提示 */}
        {loadError && (
          <div className="mb-2 p-2 bg-red-900/30 border border-red-700 rounded-lg">
            <div className="flex items-center">
              <svg className="w-4 h-4 text-red-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span className="text-red-300 text-xs">{loadError}</span>
            </div>
          </div>
        )}

        {/* 主内容区域 - 直接显示监控面板或报告面板 */}
        {activeTab === 'report' ? (
          <ReportPanel />
        ) : (
          <div className="flex gap-3" style={{ gap: '12px', overflowX: isMobile ? 'auto' : 'visible' }}>
            {/* 左侧：设备选择面板 - 20% */}
            <div style={{ flex: '0 0 20%', minWidth: '280px', maxWidth: '400px' }}>
              <DeviceSelectionPanel />
            </div>

            {/* 中间：监控面板 - 60% */}
            <div style={{ flex: '1 1 60%', minWidth: '0' }}>
              <MonitorPanel />
            </div>

            {/* 右侧：配置面板 - 20% */}
            <div style={{ flex: '0 0 20%', minWidth: '280px', maxWidth: '400px' }}>
              <ConfigPanel />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
