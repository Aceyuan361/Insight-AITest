import { useState, useEffect } from 'react';
import { useMonitoringStore } from '@/store/monitoringStore';
import MenuBar from './MenuBar';
import StatusBar from './StatusBar';
import DeviceSelectionPanel from '../panels/DeviceSelectionPanel';
import MonitorPanel from '../panels/MonitorPanel';
import ConfigPanel from '../panels/ConfigPanel';
import ReportPanel from '../panels/ReportPanel';

type TabType = 'monitor' | 'report';

export default function MainWindow() {
  const { setDevices } = useMonitoringStore();
  const [loadError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('monitor');

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
    <div className="min-h-screen bg-dark-bg text-text-primary" style={{ backgroundColor: '#0a0a0a' }}>
      <MenuBar />
      <div className="px-4 py-6 pb-12" style={{ paddingTop: '16px', paddingBottom: '48px' }}>
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

        {/* 标签页切换 */}
        <div className="mb-6">
          <div className="flex space-x-2" style={{ borderBottom: '1px solid #1a1f2e' }}>
            <button
              onClick={() => setActiveTab('monitor')}
              className="px-6 py-3 font-medium transition-colors"
              style={{
                borderBottom: activeTab === 'monitor' ? '2px solid #00d4ff' : 'none',
                color: activeTab === 'monitor' ? '#00d4ff' : '#94a3b8',
              }}
            >
              实时监控
            </button>
            <button
              onClick={() => setActiveTab('report')}
              className="px-6 py-3 font-medium transition-colors"
              style={{
                borderBottom: activeTab === 'report' ? '2px solid #00d4ff' : 'none',
                color: activeTab === 'report' ? '#00d4ff' : '#94a3b8',
              }}
            >
              性能报告
            </button>
          </div>
        </div>

        {/* 主内容区域 - 三栏布局 20:60:20 */}
        {activeTab === 'monitor' ? (
          <div className="flex gap-3" style={{ gap: '12px' }}>
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
        ) : (
          <ReportPanel />
        )}
      </div>
      <StatusBar />
    </div>
  );
}
