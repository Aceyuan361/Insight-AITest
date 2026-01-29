import SessionList from '../widgets/SessionList';

export default function ReportPanel() {
  return (
    <div className="space-y-6">
      <div className="bg-dark-card rounded-lg border border-gray-800 p-6">
        <h2 className="text-2xl font-bold text-neon-cpu mb-4">性能报告</h2>
        <p className="text-text-secondary">查看历史监控会话和性能数据报告</p>
      </div>
      <SessionList />
    </div>
  );
}
