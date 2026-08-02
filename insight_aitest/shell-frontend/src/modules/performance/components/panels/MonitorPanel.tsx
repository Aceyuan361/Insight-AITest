import { useMonitoringStore } from '@/modules/performance/store/monitoringStore';
import { useTranslation } from 'react-i18next';
import { ALL_METRIC_CARDS } from '@/shared/config/metricCards';
import NeonChartCard from '@/modules/performance/components/charts/NeonChartCard';

export default function MonitorPanel() {
  const { t } = useTranslation();
  const { metricsData, timestamps, isMonitoring, enabledMetricIds, devices, selectedDevice } = useMonitoringStore();

  // 检测当前设备类型
  const currentDeviceType = devices.find(d => d.device_id === selectedDevice)?.type || 'android';

  // 关键修改：根据store中的enabledMetricIds过滤卡片（动态显示）
  // iOS 设备：强制移除 GPU 卡片（即使已启用）
  // Android 设备：正常显示所有启用的卡片
  const isIOS = currentDeviceType === 'ios';
  const filteredMetricIds = isIOS
    ? enabledMetricIds.filter(id => id !== 'gpu')
    : enabledMetricIds;

  const enabledCards = ALL_METRIC_CARDS
    .filter(card => filteredMetricIds.includes(card.metricId))
    .sort((a, b) => a.priority - b.priority);

  return (
    <div>
      {/* 图表网格 - 直接置顶 */}
      <div>
        {/* 动态布局：每行2个卡片，支持任意数量的卡片 */}
        {Array.from({ length: Math.ceil(enabledCards.length / 2) }, (_, rowIndex) => (
          <div key={rowIndex} className="grid grid-cols-2" style={{ columnGap: '8px', marginBottom: '4px' }}>
            {enabledCards.slice(rowIndex * 2, rowIndex * 2 + 2).map((card) => (
              <NeonChartCard
                key={card.metricId}
                config={card}
                data={metricsData[card.metricId] || []}
                timestamps={timestamps}
                note={undefined}
              />
            ))}
          </div>
        ))}
      </div>

      {/* 未监控时的提示 */}
      {!isMonitoring && (
        <div className="text-center text-text-secondary" style={{ paddingTop: '4px' }}>
          <p className="text-xs" style={{ color: "var(--text-muted)", fontSize: '10px', margin: 0 }}>
            {t('device.startMonitorHint')}
          </p>
        </div>
      )}
    </div>
  );
}
