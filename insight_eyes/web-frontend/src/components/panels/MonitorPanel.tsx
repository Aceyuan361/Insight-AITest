import { useMonitoringStore } from '@/store/monitoringStore';
import { useTranslation } from 'react-i18next';
import { ALL_METRIC_CARDS } from '@/config/metricCards';
import NeonChartCard from '@/components/charts/NeonChartCard';

export default function MonitorPanel() {
  const { t } = useTranslation();
  const { metricsData, timestamps, isMonitoring, currentSession, enabledMetricIds } = useMonitoringStore();

  // 获取应用名称用于标题显示
  const appName = currentSession?.app_name || '';

  // 关键修改：根据store中的enabledMetricIds过滤卡片（动态显示）
  const enabledCards = ALL_METRIC_CARDS
    .filter(card => enabledMetricIds.includes(card.metricId))
    .sort((a, b) => a.priority - b.priority);

  return (
    <div>
      {/* 图表网格 - 直接置顶 */}
      <div>
        {/* 第一行：2个卡片 (CPU, Memory) */}
        <div className="grid grid-cols-2" style={{ columnGap: '8px', marginBottom: '4px' }}>
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
        <div className="grid grid-cols-2" style={{ columnGap: '8px', marginBottom: '4px' }}>
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
          <div className="grid grid-cols-2" style={{ columnGap: '8px' }}>
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

      {/* 未监控时的提示 */}
      {!isMonitoring && (
        <div className="text-center text-text-secondary" style={{ paddingTop: '4px' }}>
          <p className="text-xs" style={{ color: '#64748b', fontSize: '10px', margin: 0 }}>
            {t('device.startMonitorHint')}
          </p>
        </div>
      )}
    </div>
  );
}
