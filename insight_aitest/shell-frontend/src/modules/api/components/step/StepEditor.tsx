import { useState } from 'react'
import { X, ChevronDown, ChevronUp } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { KeyValueEditor, toPairs, fromPairs, type KVPair } from './KeyValueEditor'

export interface StepData {
  method: string
  path: string
  headers: Record<string, string>
  body: any
  assertions: { type: string; path?: string; expected: any }[]
  extract: Record<string, string>
}

export function StepEditor({ step, onChange, onRemove }: {
  step: StepData; onChange: (s: StepData) => void; onRemove: () => void
}) {
  const [showBody, setShowBody] = useState(false)
  const { t } = useTranslation()
  const set = (patch: Partial<StepData>) => onChange({ ...step, ...patch })

  const setAssertion = (i: number, patch: Partial<StepData['assertions'][0]>) => {
    const next = step.assertions.map((a, idx) => idx === i ? { ...a, ...patch } : a)
    set({ assertions: next })
  }
  const addAssertion = () => set({ assertions: [...step.assertions, { type: 'status_code', expected: 200 }] })
  const removeAssertion = (i: number) => set({ assertions: step.assertions.filter((_, idx) => idx !== i) })

  const extractPairs: KVPair[] = toPairs(step.extract as any)
  const setExtract = (pairs: KVPair[]) => {
    const out: Record<string, string> = {}
    for (const p of pairs) if (p.key.trim()) out[p.key.trim()] = p.value
    set({ extract: out })
  }

  return (
    <div style={{ border: '1px solid var(--bg-elevated)', borderRadius: 6, padding: 10, marginBottom: 8, background: 'var(--bg-base)' }}>
      <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
        <select style={methodStyle} value={step.method}
          onChange={(e) => set({ method: e.target.value })}>
          {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((m) => <option key={m}>{m}</option>)}
        </select>
        <input style={{ ...inputStyle, flex: 1 }} placeholder="/path" value={step.path}
          onChange={(e) => set({ path: e.target.value })} />
        <button onClick={onRemove} style={{ ...btnStyle, display: 'inline-flex', alignItems: 'center' }}>
          <X size={12} strokeWidth={1.5} />
        </button>
      </div>

      <div style={{ marginBottom: 8 }}>
        <div style={labelStyle}>Headers</div>
        <KeyValueEditor pairs={toPairs(step.headers)} onChange={(p) => set({ headers: fromPairs(p) })} />
      </div>

      {step.method !== 'GET' && (
        <div style={{ marginBottom: 8 }}>
          <button onClick={() => setShowBody(!showBody)} style={{ ...btnStyle, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            Body {showBody ? <ChevronUp size={11} strokeWidth={1.5} /> : <ChevronDown size={11} strokeWidth={1.5} />}
          </button>
          {showBody && (
            <textarea style={{ ...inputStyle, width: '100%', minHeight: 60, marginTop: 4 }}
              value={typeof step.body === 'string' ? step.body : JSON.stringify(step.body, null, 2)}
              onChange={(e) => {
                try { set({ body: JSON.parse(e.target.value) }) }
                catch { set({ body: e.target.value }) }
              }} />
          )}
        </div>
      )}

      <div style={{ marginBottom: 8 }}>
        <div style={labelStyle}>{t('api.assertionLabel')}</div>
        {step.assertions.map((a, i) => (
          <div key={i} style={{ display: 'flex', gap: 6, marginBottom: 4 }}>
            <select style={{ ...methodStyle, width: 130 }} value={a.type}
              onChange={(e) => setAssertion(i, { type: e.target.value })}>
              <option value="status_code">status_code</option>
              <option value="header">header</option>
              <option value="jsonpath">jsonpath</option>
              <option value="response_time">response_time</option>
              <option value="json_schema">json_schema</option>
              <option value="contains">contains</option>
            </select>
            {(a.type === 'header' || a.type === 'jsonpath' || a.type === 'contains') && (
              <input style={inputStyle} placeholder="path" value={a.path || ''}
                onChange={(e) => setAssertion(i, { path: e.target.value })} />
            )}
            <input style={inputStyle} placeholder="expected" value={String(a.expected ?? '')}
              onChange={(e) => setAssertion(i, { expected: e.target.value })} />
            <button onClick={() => removeAssertion(i)} style={{ ...btnStyle, display: 'inline-flex', alignItems: 'center' }}>
              <X size={12} strokeWidth={1.5} />
            </button>
          </div>
        ))}
        <button onClick={addAssertion} style={addBtnStyle}>{t('api.addAssertionBtn')}</button>
      </div>

      <div>
        <div style={labelStyle}>{t('api.extractVars')}</div>
        <KeyValueEditor pairs={extractPairs} onChange={setExtract} />
      </div>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', borderRadius: 4,
  color: "var(--text-primary)", padding: '4px 8px', fontFamily: 'inherit', fontSize: 12,
}
const methodStyle: React.CSSProperties = { ...inputStyle, width: 80 }
const btnStyle: React.CSSProperties = {
  background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)",
  borderRadius: 4, cursor: 'pointer', fontSize: 12, padding: '4px 8px',
}
const addBtnStyle: React.CSSProperties = { ...btnStyle, borderStyle: 'dashed' }
const labelStyle: React.CSSProperties = { fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }
