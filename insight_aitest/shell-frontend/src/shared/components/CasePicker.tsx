export interface PickableCase {
  id: number;
  title: string;
  last_result: string | null;
  content: { steps?: unknown[] };
}

/**
 * 用例选择列表。泛型化：api/ui 两版仅类型 + 空状态文案不同。
 */
export function CasePicker<T extends PickableCase>({
  cases,
  selectedId,
  onSelect,
  loading,
  emptyLabel = '暂无用例',
}: {
  cases: T[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  loading: boolean;
  emptyLabel?: string;
}) {
  if (loading) {
    return <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: 12 }}>加载用例…</div>;
  }
  if (cases.length === 0) {
    return <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: 12 }}>{emptyLabel}</div>;
  }
  return (
    <div style={{ overflow: 'auto' }}>
      {cases.map((c) => {
        const resColor =
          c.last_result === 'passed' ? 'var(--success)'
          : c.last_result === 'failed' ? 'var(--error)'
          : c.last_result === 'error' ? 'var(--chart-3)'
          : 'var(--border-strong)';
        return (
          <div
            key={c.id}
            onClick={() => onSelect(c.id)}
            style={{
              padding: '10px 16px',
              cursor: 'pointer',
              borderBottom: '1px solid var(--bg-card)',
              background: selectedId === c.id ? 'rgba(91,140,123,0.06)' : 'transparent',
            }}
          >
            <div style={{ color: 'var(--text-primary)', fontSize: 13 }}>{c.title}</div>
            <div style={{ display: 'flex', gap: 8, marginTop: 2 }}>
              <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{c.content.steps?.length ?? 0} 步</span>
              <span style={{ color: resColor, fontSize: 11 }}>
                {c.last_result ? `最近: ${c.last_result}` : '未执行'}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
