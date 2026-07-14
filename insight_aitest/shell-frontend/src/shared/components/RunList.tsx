import { Check, X, AlertTriangle } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export interface PickableRun {
  id: number;
  status: 'passed' | 'failed' | 'error';
  total_steps: number;
  passed_steps: number;
  started_at: string;
  duration_ms: number;
}

/**
 * 执行记录列表。泛型约束最小字段集（api/ui RunSummary 均满足）。
 * 单行紧凑布局（cockpit density），emptyLabel 区分文案。
 */
export function RunList<T extends PickableRun>({
  runs,
  selectedRunId,
  onSelect,
  emptyLabel = '暂无执行记录',
}: {
  runs: T[];
  selectedRunId: number | null;
  onSelect: (id: number) => void;
  emptyLabel?: string;
}) {
  if (runs.length === 0) {
    return <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: 12 }}>{emptyLabel}</div>;
  }
  return (
    <div style={{ overflow: 'auto' }}>
      {runs.map((r) => {
        const color =
          r.status === 'passed' ? 'var(--success)'
          : r.status === 'failed' ? 'var(--error)'
          : 'var(--chart-3)';
        const Icon: LucideIcon = r.status === 'passed' ? Check : r.status === 'failed' ? X : AlertTriangle;
        return (
          <div
            key={r.id}
            onClick={() => onSelect(r.id)}
            style={{
              padding: '8px 16px',
              cursor: 'pointer',
              borderBottom: '1px solid var(--bg-card)',
              background: selectedRunId === r.id ? 'rgba(91,140,123,0.06)' : 'transparent',
            }}
          >
            <span style={{ color, fontSize: 13, marginRight: 8, display: 'inline-flex', alignItems: 'center' }}>
              <Icon size={12} strokeWidth={1.5} />
            </span>
            <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
              {r.passed_steps}/{r.total_steps} 步 · {r.duration_ms}ms
            </span>
            <span style={{ color: 'var(--text-muted)', fontSize: 11, marginLeft: 8 }}>
              {new Date(r.started_at).toLocaleString()}
            </span>
          </div>
        );
      })}
    </div>
  );
}
