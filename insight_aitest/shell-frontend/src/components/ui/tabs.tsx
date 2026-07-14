export interface TabItem {
  key: string;
  label: string;
}

/**
 * 受控标签栏。外观取自 ApiApp/UIApp 既有的 underline 风格。
 * 与路由解耦：value/onChange 由父组件给（路由桥接在 Phase C）。
 */
export function Tabs({ tabs, value, onChange }: {
  tabs: TabItem[];
  value: string;
  onChange: (key: string) => void;
}) {
  return (
    <div style={{ display: 'flex', flexWrap: 'nowrap', overflowX: 'auto', WebkitOverflowScrolling: 'touch', borderBottom: '1px solid var(--bg-card)' }}>
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          style={{
            background: value === t.key ? 'rgba(16,185,129,0.08)' : 'transparent',
            border: 'none',
            borderBottom: value === t.key ? '2px solid var(--accent)' : '2px solid transparent',
            color: value === t.key ? 'var(--accent)' : 'var(--text-muted)',
            padding: '10px 20px',
            cursor: 'pointer',
            fontSize: 13,
          }}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
