import { useState } from 'react';
import SessionList from '../widgets/SessionList';
import SessionDetail from '../widgets/SessionDetail';
import { api } from '@/services/api';
import type { Session } from '@/types';

export default function ReportPanel() {
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSessionDeleted = () => {
    // 会话删除后刷新列表并清空详情
    setSelectedSessionId(null);
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="space-y-6">
      <div className="bg-dark-card rounded-lg border border-gray-800 p-6">
        <h2 className="text-2xl font-bold text-neon-cpu mb-4">性能报告</h2>
        <p className="text-text-secondary">查看历史监控会话和性能数据报告</p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* 左侧：会话列表 */}
        <div className="col-span-1">
          <SessionList
            key={refreshKey}
            onSelectSession={setSelectedSessionId}
            selectedSessionId={selectedSessionId}
          />
        </div>

        {/* 右侧：会话详情 */}
        <div className="col-span-2">
          <SessionDetail
            sessionId={selectedSessionId}
            onDeleted={handleSessionDeleted}
            onClose={() => setSelectedSessionId(null)}
          />
        </div>
      </div>
    </div>
  );
}
