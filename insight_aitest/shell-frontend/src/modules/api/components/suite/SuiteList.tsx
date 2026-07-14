import { useTranslation } from 'react-i18next'
import type { Suite } from '../../store/suiteStore'

export function SuiteList({ suites, selectedId, onSelect, onNew }: {
  suites: Suite[]; selectedId: number | null; onSelect: (id: number) => void; onNew: () => void
}) {
  const { t } = useTranslation()
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--bg-card)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{t('api.suite')}</span>
        <button onClick={onNew} style={primaryBtn}>{t('api.newBtn')}</button>
      </div>
      <div style={{ flex: 1, overflow: 'auto' }}>
        {suites.length === 0 && <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: 12 }}>{t('api.noSuites')}</div>}
        {suites.map((s) => (
          <div key={s.id} onClick={() => onSelect(s.id)} style={{
            padding: '10px 16px', cursor: 'pointer', borderBottom: '1px solid var(--bg-card)',
            background: selectedId === s.id ? 'rgba(91,140,123,0.06)' : 'transparent',
          }}>
            <div style={{ color: "var(--text-primary)", fontSize: 13 }}>{s.name}</div>
            <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>{t('api.caseCount', { count: s.case_count })}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

const primaryBtn: React.CSSProperties = { background: "var(--accent)", color: "var(--bg-base)", border: 'none', borderRadius: 4, padding: '3px 10px', cursor: 'pointer', fontSize: 12, fontWeight: 600 }
