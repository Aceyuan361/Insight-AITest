import { useEffect, useState } from 'react';
import { api } from '@/services/api';
import { exportHtmlReport } from '@/services/htmlExporter';
import type { Session, Device, MetricsData, AlertInfo } from '@/types';
import { MetricStats } from '@/services/htmlExporter';

interface SessionDetailProps {
  sessionId: number | null;
  onClose?: () => void;
  onDeleted?: () => void;
}

export default function SessionDetail({ sessionId, onClose, onDeleted }: SessionDetailProps) {
  const [session, setSession] = useState<Session | null>(null);
  const [device, setDevice] = useState<Device | null>(null);
  const [statistics, setStatistics] = useState<Record<string, MetricStats> | null>(null);
  const [alerts, setAlerts] = useState<AlertInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (sessionId) {
      loadSessionDetail(sessionId);
    }
  }, [sessionId]);

  const loadSessionDetail = async (id: number) => {
    setLoading(true);
    try {
      const [sessionData, statsData, alertsData] = await Promise.all([
        api.getSession(id),
        api.getSessionStatistics(id),
        api.getSessionAlerts(id),
      ]);

      setSession(sessionData);

      // 获取设备信息
      try {
        const deviceData = await api.getDevice(sessionData.device_id);
        setDevice(deviceData);
      } catch {
        setDevice(null);
      }

      setStatistics(statsData);
      setAlerts(alertsData);
    } catch (error) {
      console.error('Failed to load session detail:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExportHtml = async () => {
    if (!session) return;

    setExporting(true);
    try {
      const metrics = await api.getSessionMetrics(session.id, 10000);
      await exportHtmlReport(session, metrics, device, alerts);
    } catch (error) {
      console.error('Failed to export HTML report:', error);
      alert('导出报告失败: ' + (error as Error).message);
    } finally {
      setExporting(false);
    }
  };

  const handleDelete = async () => {
    if (!session) return;

    if (!confirm(`确定要删除会话 ${session.id} 吗？\n\n此操作不可撤销，将删除该会话的所有数据和告警记录。`)) {
      return;
    }

    setDeleting(true);
    try {
      await api.deleteSession(session.id);
      onDeleted?.();
      onClose?.();
    } catch (error) {
      console.error('Failed to delete session:', error);
      alert('删除会话失败: ' + (error as Error).message);
    } finally {
      setDeleting(false);
    }
  };

  const formatDate = (dateString: string) => new Date(dateString).toLocaleString('zh-CN');

  if (!sessionId) {
    return (
      <div className="bg-dark-card rounded-lg border border-gray-800 p-8 text-center">
        <p className="text-text-secondary">请选择一个会话查看详情</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="bg-dark-card rounded-lg border border-gray-800 p-8 text-center">
        <p className="text-text-secondary">加载中...</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="bg-dark-card rounded-lg border border-gray-800 p-8 text-center">
        <p className="text-red-400">加载会话详情失败</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 会话信息 */}
      <div className="bg-dark-card rounded-lg border border-gray-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-neon-cpu">会话 #{session.id}</h2>
          <div className="flex gap-2">
            <button
              onClick={handleExportHtml}
              disabled={exporting || session.status !== 'stopped'}
              className="px-4 py-2 bg-neon-cpu/20 hover:bg-neon-cpu/40 text-neon-cpu rounded border border-neon-cpu/50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {exporting ? '导出中...' : '导出HTML'}
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="px-4 py-2 bg-red-500/20 hover:bg-red-500/40 text-red-400 rounded border border-red-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {deleting ? '删除中...' : '删除'}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-text-secondary">设备：</span>
            <span className="text-text-primary">{device?.name || session.device_id}</span>
          </div>
          <div>
            <span className="text-text-secondary">应用：</span>
            <span className="text-text-primary">{session.app_package}</span>
          </div>
          <div>
            <span className="text-text-secondary">状态：</span>
            <span className={`${
              session.status === 'running' ? 'text-green-400' :
              session.status === 'stopped' ? 'text-gray-400' :
              'text-red-400'
            }`}>
              {session.status.toUpperCase()}
            </span>
          </div>
          <div>
            <span className="text-text-secondary">平台：</span>
            <span className="text-text-primary">{session.platform}</span>
          </div>
          <div>
            <span className="text-text-secondary">开始时间：</span>
            <span className="text-text-primary">{formatDate(session.start_time)}</span>
          </div>
          {session.end_time && (
            <div>
              <span className="text-text-secondary">结束时间：</span>
              <span className="text-text-primary">{formatDate(session.end_time)}</span>
            </div>
          )}
        </div>
      </div>

      {/* 统计数据 */}
      {statistics && Object.keys(statistics).length > 0 && (
        <div className="bg-dark-card rounded-lg border border-gray-800 p-6">
          <h3 className="text-lg font-bold text-neon-cpu mb-4">性能统计</h3>
          <div className="grid grid-cols-5 gap-4">
            {statistics.fps && (
              <div className="bg-gray-900 rounded p-4 border border-gray-800">
                <div className="text-xs text-text-secondary mb-1">FPS</div>
                <div className="text-xl font-bold text-yellow-400">{statistics.fps.avg.toFixed(1)}</div>
                <div className="text-xs text-text-secondary mt-2">
                  Max: {statistics.fps.max} | Min: {statistics.fps.min}
                </div>
              </div>
            )}
            {statistics.cpu_app && (
              <div className="bg-gray-900 rounded p-4 border border-gray-800">
                <div className="text-xs text-text-secondary mb-1">CPU</div>
                <div className="text-xl font-bold text-cyan-400">{statistics.cpu_app.avg.toFixed(2)}%</div>
                <div className="text-xs text-text-secondary mt-2">
                  Max: {statistics.cpu_app.max}% | Min: {statistics.cpu_app.min}%
                </div>
              </div>
            )}
            {statistics.memory_pss && (
              <div className="bg-gray-900 rounded p-4 border border-gray-800">
                <div className="text-xs text-text-secondary mb-1">内存</div>
                <div className="text-xl font-bold text-purple-400">{statistics.memory_pss.avg.toFixed(1)} MB</div>
                <div className="text-xs text-text-secondary mt-2">
                  Max: {statistics.memory_pss.max} MB | Min: {statistics.memory_pss.min} MB
                </div>
              </div>
            )}
            {statistics.network_up && (
              <div className="bg-gray-900 rounded p-4 border border-gray-800">
                <div className="text-xs text-text-secondary mb-1">网络上行</div>
                <div className="text-xl font-bold text-green-400">{statistics.network_up.avg.toFixed(2)} KB/s</div>
                <div className="text-xs text-text-secondary mt-2">
                  Max: {statistics.network_up.max} KB/s
                </div>
              </div>
            )}
            {statistics.network_down && (
              <div className="bg-gray-900 rounded p-4 border border-gray-800">
                <div className="text-xs text-text-secondary mb-1">网络下行</div>
                <div className="text-xl font-bold text-blue-400">{statistics.network_down.avg.toFixed(2)} KB/s</div>
                <div className="text-xs text-text-secondary mt-2">
                  Max: {statistics.network_down.max} KB/s
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 告警记录 */}
      {alerts.length > 0 && (
        <div className="bg-dark-card rounded-lg border border-gray-800 p-6">
          <h3 className="text-lg font-bold text-red-400 mb-4">告警记录 ({alerts.length})</h3>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {alerts.map((alert) => (
              <div key={alert.id} className="bg-gray-900 rounded p-3 border border-red-500/30">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-text-secondary">{formatDate(alert.timestamp)}</div>
                    <div className="text-sm text-text-primary">{alert.description}</div>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded ${
                    alert.severity === 'critical' ? 'bg-red-500/20 text-red-400' :
                    alert.severity === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-blue-500/20 text-blue-400'
                  }`}>
                    {alert.severity}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 无告警提示 */}
      {alerts.length === 0 && (
        <div className="bg-dark-card rounded-lg border border-gray-800 p-6 text-center">
          <p className="text-text-secondary">无告警记录</p>
        </div>
      )}
    </div>
  );
}
