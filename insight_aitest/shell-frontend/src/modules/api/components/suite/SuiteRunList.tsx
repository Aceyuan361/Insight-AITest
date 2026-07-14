import { useTranslation } from 'react-i18next'
import type { SuiteRunSummary } from '../../store/suiteStore'
import { Check, X, Pause, Clock } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export function SuiteRunList({ runs, selectedRunId, onSelect }: {
  runs: SuiteRunSummary[]; selectedRunId: number | null; onSelect: (id: number) => void
}) {
  const { t } = useTranslation()
  if (runs.length === 0) return <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: 12 }}>{t('api.noSuiteRuns')}</div>
  const color = (s: string) => s === 'completed' ? "var(--success)" : s === 'failed' ? "var(--error)" : s === 'interrupted' ? 'var(--chart-3)' : "var(--accent)"
  const icon = (s: string): LucideIcon => s === 'completed' ? Check : s === 'failed' ? X : s === 'interrupted' ? Pause : Clock
  return (
    <div style={{ overflow: 'auto' }}>
      {runs.map((r) => {
        const Icon = icon(r.status)
        return (
          <div key={r.id} onClick={() => onSelect(r.id)} style={{
            padding: '8px 16px', cursor: 'pointer', borderBottom: '1px solid var(--bg-card)',
            background: selectedRunId === r.id ? 'rgba(91,140,123,0.06)' : 'transparent',
          }}>
            <span style={{ color: color(r.status), fontSize: 13, marginRight: 8, display: 'inline-flex', alignItems: 'center' }}>
              <Icon size={12} strokeWidth={1.5} />
            </span>
            <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>{r.done}/{r.total}</span>
            <span style={{ color: 'var(--text-muted)', fontSize: 11, marginLeft: 8 }}>{r.environment_name ?? t('api.noEnv')}</span>
            <span style={{ color: 'var(--text-muted)', fontSize: 11, marginLeft: 8 }}>{new Date(r.started_at).toLocaleString()}</span>
          </div>
        )
      })}
    </div>
  )
}
