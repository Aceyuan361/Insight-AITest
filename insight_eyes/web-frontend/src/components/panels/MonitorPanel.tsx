import { useMonitoringStore } from '@/store/monitoringStore';
import { ALL_METRIC_CARDS } from '@/config/metricCards';
import NeonChartCard from '@/components/charts/NeonChartCard';
import MonitoringControls from '@/components/widgets/MonitoringControls';

export default function MonitorPanel() {
  const { metricsData, timestamps, isMonitoring, currentSession } = useMonitoringStore();

  // 获取应用名称用于标题显示
  const appName = currentSession?.app_name || '';

  // 获取启用的卡片（最多5个）
  const enabledCards = ALL_METRIC_CARDS
    .filter(card => card.enabled)
    .sort((a, b) => a.priority - b.priority)
    .slice(0, 5);

  return (
    <div className="space-y-6">
      {/* 控制栏 */}
      <MonitoringControls />

      {/* 主标题栏 - 始终显示，与桌面版一致 */}
      <div
        className="text-center mb-6"
        style={{
          fontFamily: '"Microsoft YaHei UI", "Segoe UI", Arial, sans-serif',
          fontSize: '16px',
          fontWeight: '600',
          color: '#ffffff',
          textTransform: 'uppercase',
        }}
      >
        {isMonitoring && appName ? `MONITORING: ${appName}` : 'REAL-TIME SYSTEM MONITOR'}
      </div>

      {/* 图表网格 - 始终显示5个卡片，未监控时显示空状态 */}
      <div>
        {/* 第一行：2个卡片 (CPU, Memory) */}
        <div className="grid grid-cols-2" style={{ columnGap: '15px', marginBottom: '12px' }}>
          {enabledCards.slice(0, 2).map((card) => (
            <NeonChartCard
              key={card.metricId}
              config={card}
              data={metricsData[card.metricId] || []}
              timestamps={timestamps}
            />
          ))}
        </div>

        {/* 第二行：2个卡片 (FPS, Network Upload) */}
        <div className="grid grid-cols-2" style={{ columnGap: '15px', marginBottom: '12px' }}>
          {enabledCards.slice(2, 4).map((card) => (
            <NeonChartCard
              key={card.metricId}
              config={card}
              data={metricsData[card.metricId] || []}
              timestamps={timestamps}
            />
          ))}
        </div>

        {/* 第三行：第5个卡片 (Network Download) */}
        {enabledCards.length >= 5 && (
          <div className="grid grid-cols-2" style={{ columnGap: '15px' }}>
            {enabledCards.slice(4, 5).map((card) => (
              <NeonChartCard
                key={card.metricId}
                config={card}
                data={metricsData[card.metricId] || []}
                timestamps={timestamps}
              />
            ))}
          </div>
        )}
      </div>

      {/* 未监控时的提示 - 移到图表下方 */}
      {!isMonitoring && (
        <div className="text-center py-4 text-text-secondary">
          <p className="text-sm" style={{ color: '#64748b' }}>
            选择设备并点击"开始监控"开始性能监控
          </p>
        </div>
      )}
    </div>
  );
}
