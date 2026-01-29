import { useMonitoringStore } from '@/store/monitoringStore';
import { ALL_METRIC_CARDS } from '@/config/metricCards';
import NeonChartCard from '@/components/charts/NeonChartCard';
import MonitoringControls from '@/components/widgets/MonitoringControls';

export default function MonitorPanel() {
  const { metricsData, timestamps, isMonitoring } = useMonitoringStore();

  return (
    <div className="space-y-6">
      {/* 控制栏 */}
      <MonitoringControls />

      {/* 监控状态 */}
      {!isMonitoring && (
        <div className="text-center py-12 text-text-secondary">
          <p className="text-lg">选择设备并点击"开始监控"开始性能监控</p>
        </div>
      )}

      {/* 图表网格 */}
      {isMonitoring && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {ALL_METRIC_CARDS
            .filter(card => card.enabled)
            .sort((a, b) => a.priority - b.priority)
            .map((card) => (
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
  );
}
