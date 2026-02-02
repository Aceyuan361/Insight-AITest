import { useEffect, useState } from 'react';
import { api } from '@/services/api';
import { exportHtmlReport } from '@/services/htmlExporter';
import type { Session, Device, MetricsData } from '@/types';

interface SessionListProps {
  onSelectSession?: (sessionId: number | null) => void;
  selectedSessionId?: number | null;
}

interface ExportingState {
  [sessionId: number]: boolean;
}

export default function SessionList({ onSelectSession, selectedSessionId }: SessionListProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [devices, setDevices] = useState<Record<string, Device>>({});
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState<ExportingState>({});
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [deletingIds, setDeletingIds] = useState<Set<number>>(new Set());

  const loadSessions = async () => {
    setLoading(true);
    try {
      const data = await api.getSessions(50);
      setSessions(data);

      // 加载设备信息
      const deviceIds = [...new Set(data.map(s => s.device_id))];
      const deviceMap: Record<string, Device> = {};
      await Promise.all(
        deviceIds.map(async (deviceId) => {
          try {
            const device = await api.getDevice(deviceId);
            deviceMap[deviceId] = device;
          } catch {
            // 设备可能已断开连接，忽略错误
          }
        })
      );
      setDevices(deviceMap);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadSessions(); }, []);

  const formatDate = (dateString: string) => new Date(dateString).toLocaleString('zh-CN');

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'text-green-400';
      case 'stopped': return 'text-gray-400';
      case 'error': return 'text-red-400';
      default: return 'text-yellow-400';
    }
  };

  // 导出 HTML 报告
  const handleExportHtml = async (session: Session) => {
    setExporting({ ...exporting, [session.id]: true });
    try {
      const [metrics, alerts] = await Promise.all([
        api.getSessionMetrics(session.id, 10000),
        api.getSessionAlerts(session.id),
      ]);

      const device = devices[session.device_id] || null;
      await exportHtmlReport(session, metrics, device, alerts);
    } catch (error) {
      console.error('Failed to export HTML report:', error);
      alert('导出报告失败: ' + (error as Error).message);
    } finally {
      setExporting({ ...exporting, [session.id]: false });
    }
  };

  // 删除单个会话
  const handleDeleteSession = async (sessionId: number) => {
    if (!confirm(`确定要删除会话 ${sessionId} 吗？\n\n此操作不可撤销，将删除该会话的所有数据和告警记录。`)) {
      return;
    }

    setDeletingIds(new Set([...deletingIds, sessionId]));
    try {
      await api.deleteSession(sessionId);

      // 如果删除的是当前选中的会话，清空选中状态
      if (selectedSessionId === sessionId) {
        onSelectSession?.(null);
      }

      // 从选中列表中移除
      const newSelectedIds = new Set(selectedIds);
      newSelectedIds.delete(sessionId);
      setSelectedIds(newSelectedIds);

      // 刷新会话列表
      await loadSessions();
    } catch (error) {
      console.error('Failed to delete session:', error);
      alert('删除会话失败: ' + (error as Error).message);
    } finally {
      setDeletingIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(sessionId);
        return newSet;
      });
    }
  };

  // 批量删除
  const handleBatchDelete = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) {
      alert('请先选择要删除的会话');
      return;
    }

    if (!confirm(`确定要删除选中的 ${ids.length} 个会话吗？\n\n此操作不可撤销，将删除这些会话的所有数据和告警记录。`)) {
      return;
    }

    try {
      const result = await api.batchDeleteSessions(ids);

      const { success, failed, failed_ids } = result;

      // 如果当前选中的会话被删除了，清空选中状态
      if (selectedSessionId && selectedIds.has(selectedSessionId)) {
        onSelectSession?.(null);
      }

      // 清空选中状态
      setSelectedIds(new Set());

      // 刷新会话列表
      await loadSessions();

      // 显示结果
      if (failed === 0) {
        alert(`成功删除 ${success} 个会话`);
      } else {
        alert(`批量删除完成\n成功: ${success} 个\n失败: ${failed} 个\n\n失败的会话ID: ${failed_ids.join(', ')}`);
      }
    } catch (error) {
      console.error('Failed to batch delete sessions:', error);
      alert('批量删除会话失败: ' + (error as Error).message);
    }
  };

  // 切换选中状态
  const toggleSelectSession = (sessionId: number) => {
    const newSelectedIds = new Set(selectedIds);
    if (newSelectedIds.has(sessionId)) {
      newSelectedIds.delete(sessionId);
    } else {
      newSelectedIds.add(sessionId);
    }
    setSelectedIds(newSelectedIds);
  };

  return (
    <div className="bg-dark-card rounded-lg border border-gray-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-neon-cpu">会话历史</h2>
        <div className="flex gap-2">
          {selectedIds.size > 0 && (
            <button
              onClick={handleBatchDelete}
              className="px-3 py-1 text-xs bg-red-500/20 hover:bg-red-500/40 text-red-400 rounded border border-red-500/50"
            >
              批量删除 ({selectedIds.size})
            </button>
          )}
          <button onClick={loadSessions} disabled={loading} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg">
            {loading ? '加载中...' : '刷新'}
          </button>
        </div>
      </div>
      <div className="space-y-2 max-h-[600px] overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="text-center text-text-secondary py-8">暂无会话记录</div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                selectedSessionId === session.id
                  ? 'bg-neon-cpu/10 border-neon-cpu'
                  : selectedIds.has(session.id)
                  ? 'bg-gray-800 border-gray-700'
                  : 'bg-gray-900 border-gray-800 hover:border-gray-700'
              }`}
              onClick={() => onSelectSession?.(session.id)}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(session.id)}
                    onChange={(e) => {
                      e.stopPropagation();
                      toggleSelectSession(session.id);
                    }}
                    onClick={(e) => e.stopPropagation()}
                    className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-neon-cpu focus:ring-neon-cpu focus:ring-offset-gray-900"
                  />
                  <span className="font-bold">Session #{session.id}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-sm ${getStatusColor(session.status)}`}>
                    {session.status.toUpperCase()}
                  </span>
                  {session.status === 'stopped' && (
                    <>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleExportHtml(session);
                        }}
                        disabled={exporting[session.id] || deletingIds.has(session.id)}
                        className="px-2 py-1 text-xs bg-neon-cpu/20 hover:bg-neon-cpu/40 text-neon-cpu rounded border border-neon-cpu/50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {exporting[session.id] ? '导出中...' : '导出'}
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteSession(session.id);
                        }}
                        disabled={deletingIds.has(session.id)}
                        className="px-2 py-1 text-xs bg-red-500/20 hover:bg-red-500/40 text-red-400 rounded border border-red-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {deletingIds.has(session.id) ? '删除中...' : '删除'}
                      </button>
                    </>
                  )}
                </div>
              </div>
              <div className="text-sm text-text-secondary space-y-1">
                <p>设备: {devices[session.device_id]?.name || session.device_id}</p>
                <p>应用: {session.app_package}</p>
                <p>开始: {formatDate(session.start_time)}</p>
                {session.end_time && <p>结束: {formatDate(session.end_time)}</p>}
                {session.duration && (
                  <p>时长: {Math.floor(session.duration / 60)}分{session.duration % 60}秒</p>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
