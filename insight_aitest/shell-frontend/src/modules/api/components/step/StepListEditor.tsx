import { ChevronUp, ChevronDown } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { StepEditor, type StepData } from './StepEditor'

export function StepListEditor({ steps, onChange }: {
  steps: StepData[]; onChange: (s: StepData[]) => void
}) {
  const { t } = useTranslation()
  const set = (i: number, s: StepData) => {
    const next = steps.map((x, idx) => idx === i ? s : x)
    onChange(next)
  }
  const add = () => onChange([...steps, { method: 'GET', path: '/', headers: {}, body: {}, assertions: [], extract: {} }])
  const remove = (i: number) => onChange(steps.filter((_, idx) => idx !== i))
  const move = (i: number, dir: -1 | 1) => {
    const j = i + dir
    if (j < 0 || j >= steps.length) return
    const next = [...steps]
    ;[next[i], next[j]] = [next[j], next[i]]
    onChange(next)
  }

  return (
    <div>
      {steps.map((s, i) => (
        <div key={i} style={{ position: 'relative', paddingLeft: 28 }}>
          <div style={{ position: 'absolute', left: 0, top: 10, display: 'flex', flexDirection: 'column' }}>
            <button onClick={() => move(i, -1)} disabled={i === 0} style={{ ...moveBtn, display: 'inline-flex', alignItems: 'center' }}>
              <ChevronUp size={10} strokeWidth={1.5} />
            </button>
            <button onClick={() => move(i, 1)} disabled={i === steps.length - 1} style={{ ...moveBtn, display: 'inline-flex', alignItems: 'center' }}>
              <ChevronDown size={10} strokeWidth={1.5} />
            </button>
          </div>
          <StepEditor step={s} onChange={(ns) => set(i, ns)} onRemove={() => remove(i)} />
        </div>
      ))}
      <button onClick={add} style={addBtnStyle}>{t('api.addStep')}</button>
    </div>
  )
}

const moveBtn: React.CSSProperties = {
  background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', color: "var(--text-muted)",
  borderRadius: 3, cursor: 'pointer', fontSize: 10, padding: '1px 5px', marginBottom: 2,
}
const addBtnStyle: React.CSSProperties = {
  background: "var(--bg-card)", border: '1px dashed var(--bg-elevated)', color: "var(--text-secondary)",
  borderRadius: 4, cursor: 'pointer', fontSize: 12, padding: '4px 12px',
}
