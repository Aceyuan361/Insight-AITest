/**
 * 右侧统计面板组件
 * 显示性能统计数据和告警记录
 * 完全复刻桌面版 StatsPanelWidget 样式
 */
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowUp, ArrowDown } from 'lucide-react';
import { api } from '@/shared/api/api';
import type { Statistics, AlertInfo } from '@/shared/api/api';

interface StatsPanelProps {
  sessionId: number | null;
}

// 统计卡片样式
const statCardStyle: React.CSSProperties = {
  backgroundColor: "var(--bg-card)",
  borderRadius: '6px',
  padding: '8px',
  marginBottom: '8px',
};

const titleStyle: React.CSSProperties = {
  color: "var(--text-secondary)",
  fontSize: '9pt',
  marginBottom: '2px',
};

const avgStyle: React.CSSProperties = {
  color: "var(--text-primary)",
  fontSize: '13pt',
  fontWeight: 'bold',
  marginBottom: '2px',
};

const rangeStyle: React.CSSProperties = {
  color: "var(--text-muted)",
  fontSize: '8pt',
};

const alertsContainerStyle: React.CSSProperties = {
  backgroundColor: "var(--bg-card)",
  borderRadius: '8px',
  padding: '12px',
  marginTop: '12px',
};

export default function StatsPanel({ sessionId }: StatsPanelProps) {
  const { t } = useTranslation();
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [alerts, setAlerts] = useState<AlertInfo[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!sessionId) {
      setStatistics(null);
      setAlerts([]);
      return;
    }

    const loadData = async () => {
      setLoading(true);
      try {
        const [statsData, alertsData] = await Promise.all([
          api.getSessionStatistics(sessionId),
          api.getSessionAlerts(sessionId),
        ]);
        setStatistics(statsData);
        setAlerts(alertsData);
      } catch (error) {
        console.error('Failed to load statistics:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [sessionId]);

  if (!sessionId) {
    return (
      <div className="flex items-center justify-center h-full" style={{ backgroundColor: "var(--bg-base)" }}>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>{t('stats.selectSession')}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full" style={{ backgroundColor: "var(--bg-base)" }}>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>{t('stats.loading')}</p>
      </div>
    );
  }

  return (
    <div
      className="flex flex-col h-full"
      style={{
        backgroundColor: "var(--bg-base)",
        borderLeft: '1px solid var(--bg-card)',
        minWidth: '280px',
      }}
    >
      {/* 标题 */}
      <div className="px-3 pt-3 pb-2">
        <h3
          className="text-base font-bold"
          style={{ color: "var(--accent)", fontSize: '14pt' }}
        >
          {t('stats.title')}
        </h3>
      </div>

      {/* 可滚动内容区域 */}
      <div className="flex-1 overflow-y-auto px-3 pb-3">
        {/* FPS 统计卡片 */}
        {statistics?.fps && (
          <div style={statCardStyle}>
            <div style={titleStyle}>FPS</div>
            <div style={avgStyle}>
              {t('stats.avg')}: {statistics.fps.avg.toFixed(1)}fps
            </div>
            <div style={rangeStyle}>
              {t('stats.max')}: {statistics.fps.max}fps  {t('stats.min')}: {statistics.fps.min}fps
            </div>
          </div>
        )}

        {/* CPU 统计卡片 */}
        {statistics?.cpu_app && (
          <div style={statCardStyle}>
            <div style={titleStyle}>CPU</div>
            <div style={avgStyle}>
              {t('stats.avg')}: {statistics.cpu_app.avg.toFixed(2)}%
            </div>
            <div style={rangeStyle}>
              {t('stats.max')}: {statistics.cpu_app.max}%  {t('stats.min')}: {statistics.cpu_app.min}%
            </div>
          </div>
        )}

        {/* 内存统计卡片 */}
        {statistics?.memory_pss && (
          <div style={statCardStyle}>
            <div style={titleStyle}>{t('config.metrics.memory')}</div>
            <div style={avgStyle}>
              {t('stats.avg')}: {statistics.memory_pss.avg.toFixed(1)}MB
            </div>
            <div style={rangeStyle}>
              {t('stats.max')}: {statistics.memory_pss.max}MB  {t('stats.min')}: {statistics.memory_pss.min}MB
            </div>
          </div>
        )}

        {/* 网络统计卡片（合并显示） */}
        {(statistics?.network_up || statistics?.network_down) && (
          <div style={statCardStyle}>
            <div style={titleStyle}>{t('stats.network')}</div>
            {statistics.network_up && (
              <div style={{ color: "var(--chart-4)", fontSize: '9pt', marginBottom: '2px', display: 'flex', alignItems: 'center', gap: 3 }}>
                <ArrowUp size={10} strokeWidth={1.5} style={{ flexShrink: 0 }} />
                <span>{t('stats.avg')}: {statistics.network_up.avg.toFixed(2)}KB/s  {t('stats.max')}: {statistics.network_up.max.toFixed(2)}KB/s</span>
              </div>
            )}
            {statistics.network_down && (
              <div style={{ color: "var(--chart-5)", fontSize: '9pt', display: 'flex', alignItems: 'center', gap: 3 }}>
                <ArrowDown size={10} strokeWidth={1.5} style={{ flexShrink: 0 }} />
                <span>{t('stats.avg')}: {statistics.network_down.avg.toFixed(2)}KB/s  {t('stats.max')}: {statistics.network_down.max.toFixed(2)}KB/s</span>
              </div>
            )}
          </div>
        )}

        {/* 告警区域 */}
        {alerts.length > 0 && (
          <div style={alertsContainerStyle}>
            <div
              className="text-sm font-bold mb-2"
              style={{ color: "var(--error)", fontSize: '10pt' }}
            >
              {t('stats.alerts')} ({alerts.length})
            </div>
            <div className="space-y-2">
              {alerts.slice(0, 20).map((alert) => (
                <div
                  key={alert.id}
                  className="text-xs"
                  style={{ color: "var(--text-primary)", fontSize: '9pt' }}
                >
                  {alert.timestamp}  {alert.description}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 无告警提示 */}
        {alerts.length === 0 && !loading && (
          <div className="text-center py-4" style={{ color: "var(--text-muted)", fontSize: '9pt' }}>
            {t('stats.noAlerts')}
          </div>
        )}
      </div>
    </div>
  );
}
