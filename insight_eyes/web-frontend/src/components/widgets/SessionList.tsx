import { useEffect, useState } from 'react';
import { api } from '@/services/api';
import type { Session } from '@/types';

export default function SessionList() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);

  const loadSessions = async () => {
    setLoading(true);
    try {
      const data = await api.getSessions(50);
      setSessions(data);
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

  return (
    <div className="bg-dark-card rounded-lg border border-gray-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-neon-cpu">会话历史</h2>
        <button onClick={loadSessions} disabled={loading} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg">
          {loading ? '加载中...' : '刷新'}
        </button>
      </div>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="text-center text-text-secondary py-8">暂无会话记录</div>
        ) : (
          sessions.map((session) => (
            <div key={session.id} className="p-4 bg-gray-900 rounded-lg border border-gray-800">
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold">Session #{session.id}</span>
                <span className={`text-sm ${getStatusColor(session.status)}`}>
                  {session.status.toUpperCase()}
                </span>
              </div>
              <div className="text-sm text-text-secondary space-y-1">
                <p>设备: {session.device_id}</p>
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
