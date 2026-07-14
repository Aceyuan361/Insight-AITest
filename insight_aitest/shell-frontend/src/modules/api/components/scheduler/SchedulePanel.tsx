import { useEffect, useState } from 'react'
import { Play, Trash2, Power } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useSchedStore } from '../../store/schedStore'
import { useSuiteStore } from '../../store/suiteStore'
import { useEnvStore } from '../../store/envStore'
import { EnvironmentSelect } from '../EnvironmentSelect'

export function SchedulePanel() {
  const { schedules, loading, unavailable, loadSchedules, createSchedule, updateSchedule, deleteSchedule, triggerSchedule } = useSchedStore()
  const { suites, loadSuites } = useSuiteStore()
  const { loadEnvs } = useEnvStore()
  const { t } = useTranslation()
  const [editing, setEditing] = useState<{ id: number | null; name: string; suite_id: number | null; cron: string; envId: number | null; enabled: boolean } | null>(null)

  useEffect(() => { loadSchedules(); loadSuites(); loadEnvs() }, [loadSchedules, loadSuites, loadEnvs])

  const suiteName = (id: number) => suites.find(s => s.id === id)?.name ?? `#${id}`

  const cronToHuman = (cron: string) => {
    const parts = cron.trim().split(/\s+/)
    if (parts.length !== 5) return cron
    const [m, h, d, mon, dow] = parts
    if (m === '0' && h !== '*' && d === '*' && mon === '*' && dow === '*') return t('api.everydayAt', { h })
    if (m === '0' && h !== '*' && d === '*' && mon === '*' && dow === '1-5') return t('api.workdayAt', { h })
    if (m.startsWith('*/')) return t('api.everyMinutes', { n: m.slice(2) })
    return cron
  }

  const save = async () => {
    if (!editing || !editing.suite_id) return
    if (editing.id) {
      await updateSchedule(editing.id, {
        name: editing.name, suite_id: editing.suite_id,
        cron_expression: editing.cron, environment_id: editing.envId, enabled: editing.enabled,
      })
    } else {
      await createSchedule({
        name: editing.name, suite_id: editing.suite_id,
        cron_expression: editing.cron, environment_id: editing.envId, enabled: editing.enabled,
      })
    }
    setEditing(null)
  }

  if (editing) {
    return (
      <div style={{ flex: 1, height: '100%', overflow: 'auto', padding: 16, color: "var(--text-primary)" }}>
        <h3 style={{ fontSize: 15, marginTop: 0 }}>{editing.id ? t('api.editSchedule') : t('api.newSchedule')}</h3>
        <div style={{ marginBottom: 8 }}>
          <div style={labelStyle}>{t('api.taskName')}</div>
          <input style={inputStyle} value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} placeholder={t('api.taskNamePlaceholder')} />
        </div>
        <div style={{ marginBottom: 8 }}>
          <div style={labelStyle}>{t('api.suite')}</div>
          <select style={inputStyle} value={editing.suite_id ?? ''} onChange={(e) => setEditing({ ...editing, suite_id: Number(e.target.value) })}>
            <option value="">{t('api.selectSuite')}</option>
            {suites.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
        <div style={{ marginBottom: 8 }}>
          <div style={labelStyle}>{t('api.cronHint')}</div>
          <input style={{ ...inputStyle, fontFamily: 'monospace' }} value={editing.cron} onChange={(e) => setEditing({ ...editing, cron: e.target.value })} placeholder="0 8 * * *" />
        </div>
        <div style={{ marginBottom: 8 }}>
          <div style={labelStyle}>{t('api.envOptional')}</div>
          <EnvironmentSelect value={editing.envId} onChange={(envId) => setEditing({ ...editing, envId })} />
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12, fontSize: 12, color: "var(--text-secondary)" }}>
          <input type="checkbox" checked={editing.enabled} onChange={(e) => setEditing({ ...editing, enabled: e.target.checked })} />
          {t('api.enable')}
        </label>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={save} style={primaryBtn}>{t('api.save')}</button>
          <button onClick={() => setEditing(null)} style={secondaryBtn}>{t('api.cancel')}</button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ flex: 1, height: '100%', overflow: 'auto', padding: 16, color: "var(--text-primary)" }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h3 style={{ fontSize: 15, margin: 0 }}>{t('api.scheduleExecution')}</h3>
        <button onClick={() => setEditing({ id: null, name: '', suite_id: null, cron: '0 8 * * *', envId: null, enabled: true })} style={primaryBtn}>{t('api.newBtn')}</button>
      </div>
      {loading && <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{t('api.loading')}</div>}
      {unavailable && (
        <div style={{ padding: 12, marginBottom: 12, border: '1px solid var(--chart-3)', borderRadius: 6, background: 'color-mix(in srgb, var(--chart-3) 10%, transparent)', color: 'var(--chart-3)', fontSize: 12, lineHeight: 1.6 }}>
          {t('api.schedulerUnavailable')}<br />
          {t('api.schedulerUnavailableHint')}<code style={{ fontSize: 11 }}>python -m insight_aitest</code>
        </div>
      )}
      {schedules.map((s) => (
        <div key={s.id} style={{ padding: 10, marginBottom: 8, border: '1px solid var(--bg-card)', borderRadius: 6, background: 'var(--bg-base)', opacity: s.enabled ? 1 : 0.6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 13, color: "var(--text-primary)", flex: 1 }}>{s.name}</span>
            <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 3, color: s.enabled ? 'var(--success)' : 'var(--text-muted)', border: `1px solid ${s.enabled ? 'var(--success)' : 'var(--text-muted)'}` }}>
              {s.enabled ? t('api.enable') : t('api.disabled')}
            </span>
            <button onClick={() => setEditing({ id: s.id, name: s.name, suite_id: s.suite_id, cron: s.cron_expression, envId: s.environment_id, enabled: s.enabled })} style={btnStyle}>{t('api.edit')}</button>
            <button onClick={() => triggerSchedule(s.id).then(() => alert(t('api.triggered')))} style={{ ...btnStyle, display: 'inline-flex', alignItems: 'center', gap: 3 }}>
              <Play size={11} strokeWidth={1.5} /> {t('api.trigger')}
            </button>
            <button onClick={() => updateSchedule(s.id, { enabled: !s.enabled })} style={{ ...btnStyle, display: 'inline-flex', alignItems: 'center' }}>
              <Power size={11} strokeWidth={1.5} />
            </button>
            <button onClick={() => deleteSchedule(s.id)} style={{ ...btnStyle, display: 'inline-flex', alignItems: 'center' }}>
              <Trash2 size={11} strokeWidth={1.5} />
            </button>
          </div>
          <div style={{ color: "var(--text-secondary)", fontSize: 12, marginTop: 4 }}>
            {suiteName(s.suite_id)} · <code style={{ fontSize: 11 }}>{s.cron_expression}</code>
            <span style={{ color: 'var(--text-muted)', marginLeft: 6 }}>({cronToHuman(s.cron_expression)})</span>
          </div>
          {s.last_run_at && (
            <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 2 }}>
              {t('api.lastRun')}: {new Date(s.last_run_at).toLocaleString('zh-CN')} · {s.last_status}
            </div>
          )}
        </div>
      ))}
      {!loading && schedules.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{t('api.noSchedules')}</div>}
    </div>
  )
}

const inputStyle: React.CSSProperties = { width: '100%', background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', borderRadius: 4, color: "var(--text-primary)", padding: '6px 8px', fontSize: 13 }
const labelStyle: React.CSSProperties = { fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }
const primaryBtn: React.CSSProperties = { background: "var(--accent)", color: "var(--bg-base)", border: 'none', borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: 12, fontWeight: 600 }
const secondaryBtn: React.CSSProperties = { background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)", borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: 12 }
const btnStyle: React.CSSProperties = { background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)", borderRadius: 4, padding: '3px 8px', cursor: 'pointer', fontSize: 11 }
