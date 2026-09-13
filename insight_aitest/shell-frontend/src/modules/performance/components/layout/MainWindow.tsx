import { useMonitoringStore } from '@/modules/performance/store/monitoringStore';
import { useIsMobile } from '@/shared/hooks/useIsMobile';
import MenuBar from './MenuBar';
import DeviceSelectionPanel from '../panels/DeviceSelectionPanel';
import MonitorPanel from '../panels/MonitorPanel';
import ConfigPanel from '../panels/ConfigPanel';
import ReportPanel from '../panels/ReportPanel';

export default function MainWindow() {
  const { activeTab } = useMonitoringStore();
  const isMobile = useIsMobile();

  return (
    <div className="text-text-primary" style={{ height: isMobile ? 'auto' : '100vh', backgroundColor: "var(--bg-base)", display: 'flex', flexDirection: 'column' }}>
      <MenuBar />
      <div className="flex-1 overflow-hidden" style={{ paddingTop: '4px', paddingBottom: '4px' }}>
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
