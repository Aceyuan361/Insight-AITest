/**
 * 报告面板组件 - 完全复刻桌面版布局
 *
 * 桌面版布局结构:
 * - 顶部控制栏 (40px): 标题 | 筛选下拉 | 搜索框 | 刷新按钮
 * - 主内容区 (3列): 会话列表(25%) | 图表区(50%) | 统计面板(25%)
 */
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { api } from '@/shared/api/api';
import { exportHtmlReport } from '@/shared/api/htmlExporter';
import { useMonitoringStore } from '@/modules/performance/store/monitoringStore';
import { useConfirmStore } from '@/shared/store/confirmStore';
import { useIsMobile } from '@/shared/hooks/useIsMobile';
import SessionList from '../widgets/SessionList';
import SessionCharts from '../charts/SessionCharts';
import StatsPanel from '../widgets/StatsPanel';
import SessionInfoBar from '../widgets/SessionInfoBar';

export default function ReportPanel() {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const { confirm } = useConfirmStore();
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // 从store获取最近停止的会话ID
  const { lastStoppedSessionId, clearLastStoppedSessionId } = useMonitoringStore();

  // 当有最近停止的会话时，自动选中它
  useEffect(() => {
    if (lastStoppedSessionId && !selectedSessionId) {
      setSelectedSessionId(lastStoppedSessionId);
      clearLastStoppedSessionId();  // 清除标记，避免重复选中
    }
  }, [lastStoppedSessionId, selectedSessionId, clearLastStoppedSessionId]);

  // 筛选状态
  const [platformFilter, setPlatformFilter] = useState<'all' | 'android' | 'ios'>('all');
  const [searchText, setSearchText] = useState('');

  const handleSessionDeleted = () => {
    setSelectedSessionId(null);
    setRefreshKey(prev => prev + 1);
  };

  // 导出 HTML
  const handleExportHtml = async () => {
    if (!selectedSessionId) return;

    setExporting(true);
    try {
      const session = await api.getSession(selectedSessionId);
      const metrics = await api.getSessionMetrics(selectedSessionId, 10000);
      const device = await api.getDevice(session.device_id).catch(() => null);
      const alerts = await api.getSessionAlerts(selectedSessionId);

      await exportHtmlReport(session, metrics, device, alerts);
    } catch (error) {
      console.error('Failed to export HTML report:', error);
      toast.error(`${t('report.exportFailed')}: ${(error as Error).message}`);
    } finally {
      setExporting(false);
    }
  };

  // 删除会话
  const handleDelete = () => {
    if (!selectedSessionId) return;

    confirm({
      title: t('dialogs.confirmDelete'),
      message: t('report.confirmDeleteMessage', { sessionId: selectedSessionId }),
      confirmText: t('dialogs.confirmDelete'),
      cancelText: t('dialogs.cancel'),
      variant: 'danger',
      onConfirm: async () => {
        setDeleting(true);
        try {
          await api.deleteSession(selectedSessionId);
          handleSessionDeleted();
        } catch (error) {
          console.error('Failed to delete session:', error);
          toast.error(`${t('report.deleteFailed')}: ${(error as Error).message}`);
        } finally {
          setDeleting(false);
        }
      },
    });
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: "var(--bg-base)",
    }}>
      {/* 顶部控制栏 - 完全复刻桌面版 */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        padding: '0 20px',
        height: '40px',
        backgroundColor: 'var(--bg-card)',
        borderBottom: '1px solid var(--border-strong)',
      }}>
        {/* 标题 */}
        <h2 style={{
          fontSize: '16px',
          fontWeight: '600',
          color: "var(--accent)",
          margin: 0,
          whiteSpace: 'nowrap',
        }}>
          {t('report.title')}
        </h2>

        {/* 平台筛选下拉框 */}
        <select
          value={platformFilter}
          onChange={(e) => setPlatformFilter(e.target.value as 'all' | 'android' | 'ios')}
          style={{
            backgroundColor: "var(--bg-card)",
            color: "var(--text-primary)",
            border: '1px solid var(--bg-card)',
            borderRadius: '4px',
            padding: '4px 8px',
            fontSize: '12px',
            cursor: 'pointer',
          }}
        >
          <option value="all">{t('report.allDevices')}</option>
          <option value="android">Android</option>
          <option value="ios">iOS</option>
        </select>

        {/* 搜索输入框 */}
        <input
          type="text"
          placeholder={t('report.searchPlaceholder')}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          style={{
            backgroundColor: "var(--bg-card)",
            color: "var(--text-primary)",
            border: '1px solid var(--bg-card)',
            borderRadius: '4px',
            padding: '4px 8px',
            fontSize: '12px',
            width: '180px',
          }}
        />
      </div>

      {/* 主内容区域 - 3列布局，完全复刻桌面版 */}
      <div style={{
        display: 'flex',
        flex: 1,
        overflowX: isMobile ? 'auto' : 'hidden',
        overflowY: 'hidden',
        gap: '20px',
        padding: '20px',
      }}>
        {/* 左侧：会话列表 (25%) */}
        <div style={{
          flex: '0 0 25%',
          minWidth: '250px',
          maxWidth: '350px',
          overflow: 'hidden',
        }}>
          <SessionList
            key={refreshKey}
            onSelectSession={setSelectedSessionId}
            selectedSessionId={selectedSessionId}
            platformFilter={platformFilter}
            searchText={searchText}
          />
        </div>

        {/* 中间：图表展示区 (50%) */}
        <div style={{
          flex: '1 1 50%',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}>
          {selectedSessionId ? (
            <>
              {/* 会话信息栏 */}
              <SessionInfoBar sessionId={selectedSessionId} />

              {/* 图表区域 */}
              <div style={{
                flex: 1,
                overflow: 'auto',
                padding: '10px',
                backgroundColor: 'var(--bg-card)',
              }}>
                <SessionCharts sessionId={selectedSessionId} />
              </div>

              {/* 底部操作按钮 */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 20px',
                backgroundColor: "var(--bg-card)",
                borderTop: '1px solid var(--border-strong)',
              }}>
                <button
                  onClick={handleExportHtml}
                  disabled={exporting}
                  style={{
                    backgroundColor: "var(--accent)",
                    color: "var(--bg-base)",
                    border: 'none',
                    borderRadius: '4px',
                    padding: '6px 16px',
                    fontSize: '13px',
                    fontWeight: '500',
                    cursor: exporting ? 'not-allowed' : 'pointer',
                    opacity: exporting ? 0.5 : 1,
                  }}
                  onMouseEnter={(e) => {
                    if (!exporting) e.currentTarget.style.backgroundColor = 'var(--accent-hover)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = "var(--accent)";
                  }}
                >
                  {exporting ? t('report.exporting') : t('report.exportHtml')}
                </button>

                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  style={{
                    backgroundColor: "var(--error)",
                    color: "var(--text-primary)",
                    border: 'none',
                    borderRadius: '4px',
                    padding: '6px 16px',
                    fontSize: '13px',
                    fontWeight: '500',
                    cursor: deleting ? 'not-allowed' : 'pointer',
                    opacity: deleting ? 0.5 : 1,
                  }}
                  onMouseEnter={(e) => {
                    if (!deleting) e.currentTarget.style.backgroundColor = 'var(--error)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = "var(--error)";
                  }}
                >
                  {deleting ? t('report.deleting') : t('report.deleteSession')}
                </button>
              </div>
            </>
          ) : (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              backgroundColor: 'var(--bg-card)',
            }}>
              <span style={{ color: "var(--text-muted)", fontSize: '14px' }}>{t('report.selectSessionPrompt')}</span>
            </div>
          )}
        </div>

        {/* 右侧：性能统计面板 (25%) */}
        <div style={{
          flex: '0 0 25%',
          minWidth: '250px',
          maxWidth: '350px',
          overflow: 'hidden',
        }}>
          <StatsPanel sessionId={selectedSessionId} />
        </div>
      </div>
    </div>
  );
}
