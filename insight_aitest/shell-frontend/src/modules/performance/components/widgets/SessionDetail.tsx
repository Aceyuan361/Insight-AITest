/**
 * 会话详情组件 - 重构版
 * 完全复刻桌面版 SessionReportWidget 布局
 *
 * 布局结构:
 * - 顶部: 紧凑会话信息栏
 * - 中间: SplitPane (70:30)
 *   - 左侧: 图表区域 (2×3网格)
 *   - 右侧: 统计面板 (滚动)
 * - 底部: 操作按钮
 */
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { api } from '@/shared/api/api';
import { useConfirmStore } from '@/shared/store/confirmStore';
import { exportHtmlReport } from '@/shared/api/htmlExporter';
import SessionInfoBar from './SessionInfoBar';
import SessionCharts from '../charts/SessionCharts';
import StatsPanel from './StatsPanel';
import SplitPane from '../layout/SplitPane';

interface SessionDetailProps {
  sessionId: number | null;
  onClose?: () => void;
  onDeleted?: () => void;
}

export default function SessionDetail({ sessionId, onClose, onDeleted }: SessionDetailProps) {
  const { t } = useTranslation();
  const { confirm } = useConfirmStore();
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // 导出 HTML
  const handleExportHtml = async () => {
    if (!sessionId) return;

    setExporting(true);
    try {
      const session = await api.getSession(sessionId);
      const metrics = await api.getSessionMetrics(sessionId, 10000);
      const device = await api.getDevice(session.device_id).catch(() => null);
      const alerts = await api.getSessionAlerts(sessionId);

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
    if (!sessionId) return;

    confirm({
      title: t('dialogs.confirmDelete'),
      message: t('report.confirmDeleteMessage', { sessionId }),
      confirmText: t('dialogs.confirmDelete'),
      cancelText: t('dialogs.cancel'),
      variant: 'danger',
      onConfirm: async () => {
        setDeleting(true);
        try {
          await api.deleteSession(sessionId);
          onDeleted?.();
          onClose?.();
        } catch (error) {
          console.error('Failed to delete session:', error);
          toast.error(`${t('report.deleteFailed')}: ${(error as Error).message}`);
        } finally {
          setDeleting(false);
        }
      },
    });
  };

  // 空状态
  if (!sessionId) {
    return (
      <div className="flex items-center justify-center h-full bg-dark-card rounded-lg border border-gray-800">
        <p className="text-text-secondary">{t('report.selectSessionPrompt')}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-dark-card rounded-lg border border-gray-800 overflow-hidden">
      {/* 紧凑会话信息栏 */}
      <SessionInfoBar sessionId={sessionId} />

      {/* 主内容区域: SplitPane (70:30) */}
      <div className="flex-1 overflow-hidden">
        <SplitPane
          direction="horizontal"
          defaultSize={700}
          minSize={400}
          maxSize={1200}
          storageKey="report-split-position"
          className="h-full"
        >
          {/* 左侧: 图表区域 */}
          <div className="h-full overflow-hidden">
            <SessionCharts sessionId={sessionId} />
          </div>

          {/* 右侧: 统计面板 */}
          <div className="h-full overflow-hidden">
            <StatsPanel sessionId={sessionId} />
          </div>
        </SplitPane>
      </div>

      {/* 底部操作按钮 */}
      <div
        className="flex items-center justify-between px-4 py-3 gap-4"
        style={{
          backgroundColor: "var(--bg-base)",
          borderTop: '1px solid var(--bg-card)',
        }}
      >
        <button
          onClick={handleExportHtml}
          disabled={exporting}
          className="px-4 py-2 rounded font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            backgroundColor: "var(--bg-card)",
            color: "var(--accent)",
            border: '1px solid var(--accent)',
            borderRadius: '6px',
            padding: '8px 16px',
          }}
          onMouseEnter={(e) => {
            if (!exporting) {
              e.currentTarget.style.backgroundColor = "var(--accent)";
              e.currentTarget.style.color = "var(--bg-base)";
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "var(--bg-card)";
            e.currentTarget.style.color = "var(--accent)";
          }}
        >
          {exporting ? t('report.exporting') : t('report.exportHtml')}
        </button>

        <button
          onClick={handleDelete}
          disabled={deleting}
          className="px-4 py-2 rounded font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            backgroundColor: "var(--bg-card)",
            color: "var(--error)",
            border: '1px solid var(--error)',
            borderRadius: '6px',
            padding: '8px 16px',
          }}
          onMouseEnter={(e) => {
            if (!deleting) {
              e.currentTarget.style.backgroundColor = "var(--error)";
              e.currentTarget.style.color = "var(--bg-base)";
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "var(--bg-card)";
            e.currentTarget.style.color = "var(--error)";
          }}
        >
          {deleting ? t('report.deleting') : t('report.deleteSession')}
        </button>
      </div>
    </div>
  );
}
