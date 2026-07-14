import { useState } from 'react'
import { ChevronUp, ChevronDown } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { StepListEditor } from '../step/StepListEditor'
import type { StepData } from '../step/StepEditor'
import type { ApiCase } from '../../store/runStore'

export function SuiteEditor({ initial, cases, onSave, onCancel }: {
  initial: { name: string; description: string; case_ids: number[]; setup: StepData[]; teardown: StepData[] } | null
  cases: ApiCase[]
  onSave: (data: any) => void
  onCancel: () => void
}) {
  const [name, setName] = useState(initial?.name ?? '')
  const [desc, setDesc] = useState(initial?.description ?? '')
  const [selected, setSelected] = useState<number[]>(initial?.case_ids ?? [])
  const [setup, setSetup] = useState<StepData[]>(initial?.setup ?? [])
  const [teardown, setTeardown] = useState<StepData[]>(initial?.teardown ?? [])
  const { t } = useTranslation()

  const toggle = (id: number) => setSelected((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id])
  const move = (i: number, dir: -1 | 1) => {
    const j = i + dir; if (j < 0 || j >= selected.length) return
    const next = [...selected]; [next[i], next[j]] = [next[j], next[i]]; setSelected(next)
  }

  return (
    <div style={{ flex: 1, height: '100%', overflow: 'auto', padding: 16, color: "var(--text-primary)" }}>
      <h3 style={{ fontSize: 15, marginTop: 0 }}>{initial ? t('api.editSuite') : t('api.newSuite')}</h3>
      <div style={{ marginBottom: 8 }}>
        <div style={labelStyle}>{t('api.name')}</div>
        <input style={inputStyle} value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div style={{ marginBottom: 8 }}>
        <div style={labelStyle}>{t('api.description')}</div>
        <input style={inputStyle} value={desc} onChange={(e) => setDesc(e.target.value)} />
      </div>
      <div style={{ marginBottom: 12 }}>
        <div style={{ ...labelStyle, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          {t('api.selectCasesHintStart')}
          <ChevronUp size={10} strokeWidth={1.5} /><ChevronDown size={10} strokeWidth={1.5} />
          {t('api.selectCasesHintEnd')}
        </div>
        <div style={{ display: 'flex', gap: 16 }}>
          <div style={{ flex: 1 }}>
            {cases.map((c) => (
              <label key={c.id} style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', padding: '2px 0' }}>
                <input type="checkbox" checked={selected.includes(c.id)} onChange={() => toggle(c.id)} style={{ marginRight: 6 }} />
                {c.title}
              </label>
            ))}
            {cases.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>{t('api.noApiCases')}</div>}
          </div>
          <div style={{ width: 220 }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>{t('api.selectedCount', { count: selected.length })}</div>
            {selected.map((id, i) => {
              const c = cases.find((x) => x.id === id)
              return (
                <div key={id} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: "var(--text-secondary)", padding: '2px 0' }}>
                  <button onClick={() => move(i, -1)} disabled={i === 0} style={{ ...moveBtn, display: 'inline-flex', alignItems: 'center' }}>
                    <ChevronUp size={10} strokeWidth={1.5} />
                  </button>
                  <button onClick={() => move(i, 1)} disabled={i === selected.length - 1} style={{ ...moveBtn, display: 'inline-flex', alignItems: 'center' }}>
                    <ChevronDown size={10} strokeWidth={1.5} />
                  </button>
                  <span style={{ flex: 1 }}>{c?.title ?? `#${id}`}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
      <div style={{ marginBottom: 12 }}>
        <div style={labelStyle}>{t('api.setupHint')}</div>
        <StepListEditor steps={setup} onChange={setSetup} />
      </div>
      <div style={{ marginBottom: 12 }}>
        <div style={labelStyle}>{t('api.teardownHint')}</div>
        <StepListEditor steps={teardown} onChange={setTeardown} />
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button onClick={() => onSave({ name, description: desc, case_ids: selected, setup, teardown })} style={primaryBtn}>{t('api.save')}</button>
        <button onClick={onCancel} style={secondaryBtn}>{t('api.cancel')}</button>
      </div>
    </div>
  )
}

const inputStyle: React.CSSProperties = { width: '100%', background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', borderRadius: 4, color: "var(--text-primary)", padding: '6px 8px', fontSize: 13 }
const labelStyle: React.CSSProperties = { fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }
const primaryBtn: React.CSSProperties = { background: "var(--accent)", color: "var(--bg-base)", border: 'none', borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: 12, fontWeight: 600 }
const secondaryBtn: React.CSSProperties = { background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)", borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: 12 }
const moveBtn: React.CSSProperties = { background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', color: "var(--text-muted)", borderRadius: 3, cursor: 'pointer', fontSize: 10, padding: '1px 5px' }
