/**
 * 报告面板组件 - 重构版
 * 完全复刻桌面版 ReportPanel 布局
 *
 * 布局结构:
 * - Header: 标题 + 筛选控件 (平台下拉/搜索/刷新/批量删除)
 * - Main: SplitPane (30:70)
 *   - 左侧: 会话列表表格 (紧凑格式)
 *   - 右侧: 会话详情 (图表+统计)
 */
import { useState } from 'react';
import SessionList from '../widgets/SessionList';
import SessionDetail from '../widgets/SessionDetail';
import SplitPane from '../layout/SplitPane';

export default function ReportPanel() {
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // 筛选状态
  const [platformFilter, setPlatformFilter] = useState<'all' | 'android' | 'ios'>('all');
  const [searchText, setSearchText] = useState('');

  const handleSessionDeleted = () => {
    setSelectedSessionId(null);
    setRefreshKey(prev => prev + 1);
  };

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Header: 标题 + 筛选控件 */}
      <div
        className="px-4 py-3 rounded-lg border flex items-center gap-4"
        style={{
          backgroundColor: '#121824',
          borderColor: '#1a1f2e',
        }}
      >
        {/* 标题 */}
        <h2
          className="text-xl font-bold"
          style={{ fontSize: '18pt', fontWeight: '600', color: '#00d4ff' }}
        >
          测试报告
        </h2>

        <div className="flex-1" />

        {/* 平台筛选下拉框 */}
        <select
          value={platformFilter}
          onChange={(e) => setPlatformFilter(e.target.value as 'all' | 'android' | 'ios')}
          className="px-3 py-2 rounded-lg border bg-gray-900 text-gray-200 focus:outline-none focus:ring-2 focus:ring-neon-cpu"
          style={{
            backgroundColor: '#121824',
            color: '#e0e6ed',
            border: '1px solid #1a1f2e',
            borderRadius: '6px',
            padding: '6px 12px',
            minWidth: '120px',
          }}
        >
          <option value="all">全部设备</option>
          <option value="android">Android</option>
          <option value="ios">iOS</option>
        </select>

        {/* 搜索输入框 */}
        <input
          type="text"
          placeholder="搜索包名或应用名..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          className="px-3 py-2 rounded-lg border bg-gray-900 text-gray-200 focus:outline-none focus:ring-2 focus:ring-neon-cpu"
          style={{
            backgroundColor: '#121824',
            color: '#e0e6ed',
            border: '1px solid #1a1f2e',
            borderRadius: '6px',
            padding: '6px 12px',
            minWidth: '200px',
          }}
        />

        {/* 刷新按钮 */}
        <button
          onClick={handleRefresh}
          className="px-4 py-2 rounded-lg font-medium transition-colors"
          style={{
            backgroundColor: '#1a1f2e',
            color: '#e0e6ed',
            minWidth: '80px',
            padding: '6px 16px',
          }}
        >
          刷新
        </button>

        {/* 批量删除按钮 - 暂时不实现，需要从 SessionList 传递选中状态 */}
      </div>

      {/* 主内容区域: SplitPane (30:70) */}
      <div className="flex-1 overflow-hidden min-h-0">
        <SplitPane
          direction="horizontal"
          defaultSize={300}
          minSize={200}
          maxSize={500}
          storageKey="report-panel-split-position"
          className="h-full"
        >
          {/* 左侧: 会话列表 */}
          <div className="h-full overflow-hidden">
            <SessionList
              key={refreshKey}
              onSelectSession={setSelectedSessionId}
              selectedSessionId={selectedSessionId}
              platformFilter={platformFilter}
              searchText={searchText}
            />
          </div>

          {/* 右侧: 会话详情 */}
          <div className="h-full overflow-hidden">
            <SessionDetail
              sessionId={selectedSessionId}
              onDeleted={handleSessionDeleted}
              onClose={() => setSelectedSessionId(null)}
            />
          </div>
        </SplitPane>
      </div>
    </div>
  );
}
