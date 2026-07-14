import { useState, useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import { useTranslation } from 'react-i18next'

/** 键值对编辑器（headers + 环境变量复用）。{key,value}[] 与 Record<string,string> 互转 */
export interface KVPair { key: string; value: string }

export function toPairs(obj: Record<string, string> | undefined | null): KVPair[] {
  if (!obj) return []
  return Object.entries(obj).map(([key, value]) => ({ key, value: String(value) }))
}

export function fromPairs(pairs: KVPair[]): Record<string, string> {
  const out: Record<string, string> = {}
  for (const p of pairs) {
    if (p.key.trim()) out[p.key.trim()] = p.value
  }
  return out
}

export function KeyValueEditor({ pairs, onChange }: {
  pairs: KVPair[]; onChange: (pairs: KVPair[]) => void
}) {
  // 内部状态保留空行（正在编辑但 key 还没填的行）。
  // 父组件的 onChange 通常会 fromPairs 过滤掉空 key，如果不维护
  // 本地状态，新添加的空行会在 re-render 后立即消失。
  const [local, setLocal] = useState<KVPair[]>(pairs)
  const { t } = useTranslation()
  const pairsRef = useRef(pairs)
  pairsRef.current = pairs

  // 当父组件推入的数据与本地"已提交"行不一致时（如切换了 step），
  // 才同步本地状态；否则保留正在编辑的空行。
  useEffect(() => {
    const committed = local.filter((p) => p.key.trim())
    if (JSON.stringify(committed) !== JSON.stringify(pairs)) {
      setLocal(pairs)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pairs])

  const commit = (next: KVPair[]) => {
    setLocal(next)
    onChange(next)
  }
  const set = (i: number, field: 'key' | 'value', v: string) => {
    commit(local.map((p, idx) => (idx === i ? { ...p, [field]: v } : p)))
  }
  const add = () => commit([...local, { key: '', value: '' }])
  const remove = (i: number) => commit(local.filter((_, idx) => idx !== i))

  return (
    <div>
      {local.map((p, i) => (
        <div key={i} style={{ display: 'flex', gap: 6, marginBottom: 4 }}>
          <input style={inputStyle} placeholder={t('api.keyPlaceholder')} value={p.key}
            onChange={(e) => set(i, 'key', e.target.value)} />
          <input style={inputStyle} placeholder={t('api.valuePlaceholder')} value={p.value}
            onChange={(e) => set(i, 'value', e.target.value)} />
          <button onClick={() => remove(i)} style={{ ...btnStyle, display: 'inline-flex', alignItems: 'center' }}>
            <X size={12} strokeWidth={1.5} />
          </button>
        </div>
      ))}
      <button onClick={add} style={addBtnStyle}>{t('api.addRow')}</button>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  flex: 1, background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', borderRadius: 4,
  color: "var(--text-primary)", padding: '4px 8px', fontFamily: 'inherit', fontSize: 12,
}
const btnStyle: React.CSSProperties = {
  background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)",
  borderRadius: 4, cursor: 'pointer', fontSize: 12, padding: '4px 8px',
}
const addBtnStyle: React.CSSProperties = {
  ...btnStyle, borderStyle: 'dashed', marginTop: 4,
}
