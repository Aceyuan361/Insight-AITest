/**
 * 告警记录列表组件
 * 显示格式：[时间] [严重程度] 内容
 */
import { useTranslation } from 'react-i18next';
import { useMonitoringStore } from '@/store/monitoringStore';

export default function AlarmRecords() {
  const { t } = useTranslation();
  const { alarms } = useMonitoringStore();

  // 获取告警严重程度的翻译
  const getSeverityLabel = (level: string): string => {
    const severityMap: Record<string, string> = {
      '严重': t('alerts.severityCritical'),
      '警告': t('alerts.severityWarning'),
      '信息': t('alerts.severityInfo'),
    };
    return severityMap[level] || level;
  };

  return (
    <div>
      <div style={{
        fontSize: '14px',
        fontWeight: '600',
        color: '#7dd3fc',
        marginBottom: '12px',
      }}>
        {t('alerts.title')}
      </div>
      <div style={{
        backgroundColor: '#121824',
        border: '1px solid #1a1f2e',
        borderRadius: '6px',
        maxHeight: '200px',
        overflowY: 'auto',
        padding: '8px',
      }}>
        {!alarms || alarms.length === 0 ? (
          <div style={{
            fontSize: '11px',
            color: '#64748b',
            textAlign: 'center',
            padding: '12px',
          }}>
            {t('alerts.noAlerts')}
          </div>
        ) : (
          alarms.map((alarm) => (
            <div
              key={alarm.id}
              style={{
                fontSize: '12px',
                color: '#cccccc',
                padding: '6px 8px',
                borderBottom: '1px solid rgba(255,255,255,0.05)',
                fontFamily: "'Consolas', 'Monaco', monospace",
              }}
            >
              <span style={{ color: '#94a3b8' }}>[{alarm.time}]</span>
              <span style={{
                color: alarm.level === '严重' ? '#ef4444' : '#f59e0b',
                marginLeft: '8px',
              }}>
                [{getSeverityLabel(alarm.level)}]
              </span>
              <span style={{ marginLeft: '8px' }}>{alarm.content}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
