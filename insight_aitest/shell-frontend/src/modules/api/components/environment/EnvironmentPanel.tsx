import { useEffect, useRef, useState } from 'react'
import { Copy, Download, Upload } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useEnvStore } from '../../store/envStore'
import { KeyValueEditor, toPairs, type KVPair } from '../step/KeyValueEditor'
import { useConfirmStore } from '../../../../shared/store/confirmStore'

const BASE = '/api/modules/api/environments'

export function EnvironmentPanel() {
  const { envs, loading, loadEnvs, createEnv, updateEnv, deleteEnv } = useEnvStore()
  const { confirm } = useConfirmStore()
  const { t } = useTranslation()
  const [editing, setEditing] = useState<{ id: number | null; name: string; base_url: string; vars: KVPair[]; meta: Record<string,string>; is_default: boolean } | null>(null)
  const importRef = useRef<HTMLInputElement>(null)
  useEffect(() => { loadEnvs() }, [loadEnvs])

  const save = async () => {
    if (!editing) return
    const variables: Record<string,string> = {}
    const variables_meta: Record<string,string> = {}
    for (const p of editing.vars) if (p.key.trim()) {
      variables[p.key.trim()] = p.value
      variables_meta[p.key.trim()] = editing.meta[p.key.trim()] || 'text'
    }
    const data = { name: editing.name, base_url: editing.base_url, variables, variables_meta, is_default: editing.is_default }
    if (editing.id) await updateEnv(editing.id, data)
    else await createEnv(data)
    setEditing(null)
  }

  const clone = async (id: number, name: string) => {
    const newName = prompt(t('api.newEnvNamePrompt'), t('api.envCopySuffix', { name }))
    if (!newName) return
    const r = await fetch(`${BASE}/${id}/clone`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ new_name: newName }) })
    if (!r.ok) { alert(t('api.cloneFailed', { msg: await r.text().catch(() => '') })); return }
    await loadEnvs()
  }

  const importEnvs = async (file: File) => {
    try {
      const data = JSON.parse(await file.text())
      const arr = Array.isArray(data) ? data : [data]
      const r = await fetch(`${BASE}/import`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(arr) })
      const result = await r.json()
      alert(t('api.importDone', { imported: result.imported, skipped: result.skipped }))
      await loadEnvs()
    } catch (e) { alert(t('api.importFailed', { msg: e })) }
  }

  if (editing) {
    return (
      <div style={{ padding: 16, color: "var(--text-primary)", maxWidth: 600 }}>
        <h3 style={{ fontSize: 15, marginTop: 0 }}>{editing.id ? t('api.editEnv') : t('api.newEnv')}</h3>
        <div style={{ marginBottom: 8 }}>
          <div style={labelStyle}>{t('api.name')}</div>
          <input style={inputStyle} value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} placeholder="dev" />
        </div>
        <div style={{ marginBottom: 8 }}>
          <div style={labelStyle}>{t('api.baseUrl')}</div>
          <input style={inputStyle} value={editing.base_url} onChange={(e) => setEditing({ ...editing, base_url: e.target.value })} placeholder="https://dev.example.com" />
        </div>
        <div style={{ marginBottom: 8 }}>
          <div style={labelStyle}>{t('api.varTypeHint')}</div>
          <KeyValueEditor pairs={editing.vars} onChange={(vars) => setEditing({ ...editing, vars })} />
          {/* 变量类型标记 */}
          <div style={{ marginTop: 8 }}>
            {editing.vars.filter(p => p.key.trim()).map((p, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', width: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.key}</span>
                <select style={{ ...inputStyle, width: 100, fontSize: 11, padding: '2px 4px' }}
                  value={editing.meta[p.key.trim()] || 'text'}
                  onChange={(e) => setEditing({ ...editing, meta: { ...editing.meta, [p.key.trim()]: e.target.value } })}>
                  <option value="text">text</option>
                  <option value="secret">secret</option>
                  <option value="json">json</option>
                </select>
                {editing.meta[p.key.trim()] === 'secret' && <span style={{ fontSize: 10, color: 'var(--chart-3)' }}>{t('api.secretRuntimeHint')}</span>}
              </div>
            ))}
          </div>
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12, fontSize: 12, color: "var(--text-secondary)" }}>
          <input type="checkbox" checked={editing.is_default} onChange={(e) => setEditing({ ...editing, is_default: e.target.checked })} />
          {t('api.setDefaultHint')}
        </label>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={save} style={primaryBtn}>{t('api.save')}</button>
          <button onClick={() => setEditing(null)} style={secondaryBtn}>{t('api.cancel')}</button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: 16, color: "var(--text-primary)" }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
        <h3 style={{ fontSize: 15, margin: 0 }}>{t('api.envManagement')}</h3>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <a href={`${BASE}/export`} download style={{ ...btnStyle, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <Download size={12} strokeWidth={1.5} /> {t('api.exportBtn')}
          </a>
          <button onClick={() => importRef.current?.click()} style={{ ...btnStyle, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <Upload size={12} strokeWidth={1.5} /> {t('api.importBtn')}
          </button>
          <input ref={importRef} type="file" accept=".json" style={{ display: 'none' }}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) importEnvs(f); e.target.value = '' }} />
          <button onClick={() => setEditing({ id: null, name: '', base_url: '', vars: [], meta: {}, is_default: false })} style={primaryBtn}>{t('api.newBtn')}</button>
        </div>
      </div>
      {loading && <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{t('api.loading')}</div>}
      {envs.map((e) => (
        <div key={e.id} style={{ padding: 10, marginBottom: 8, border: '1px solid var(--bg-card)', borderRadius: 6, background: 'var(--bg-base)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ color: "var(--text-primary)", fontSize: 13, flex: 1 }}>{e.name}</span>
            {e.is_default && <span style={{ fontSize: 10, color: "var(--accent)", border: '1px solid var(--accent)', borderRadius: 3, padding: '1px 6px' }}>{t('api.defaultTag')}</span>}
            <button onClick={() => setEditing({ id: e.id, name: e.name, base_url: e.base_url, vars: toPairs(e.variables), meta: { ...(e.variables_meta || {}) }, is_default: e.is_default })} style={btnStyle}>{t('api.edit')}</button>
            <button onClick={() => clone(e.id, e.name)} style={{ ...btnStyle, display: 'inline-flex', alignItems: 'center', gap: 3 }}>
              <Copy size={11} strokeWidth={1.5} /> {t('api.clone')}
            </button>
            <button onClick={() => confirm({
              title: t('api.confirmDelete'),
              message: t('api.confirmDeleteEnv', { name: e.name }),
              variant: 'danger',
              onConfirm: () => deleteEnv(e.id),
            })} style={btnStyle}>{t('api.delete')}</button>
          </div>
          <div style={{ color: "var(--text-secondary)", fontSize: 12, marginTop: 4 }}>{e.base_url}</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 2 }}>
            {t('api.varCount', { count: Object.keys(e.variables).length })}
            {e.variables_meta && Object.values(e.variables_meta).filter(v => v === 'secret').length > 0 &&
              ` · ${t('api.secretCount', { count: Object.values(e.variables_meta).filter(v => v === 'secret').length })}`}
          </div>
        </div>
      ))}
      {!loading && envs.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{t('api.noEnvs')}</div>}
    </div>
  )
}

const inputStyle: React.CSSProperties = { width: '100%', background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', borderRadius: 4, color: "var(--text-primary)", padding: '6px 8px', fontSize: 13 }
const labelStyle: React.CSSProperties = { fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }
const primaryBtn: React.CSSProperties = { background: "var(--accent)", color: "var(--bg-base)", border: 'none', borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: 12, fontWeight: 600 }
const secondaryBtn: React.CSSProperties = { background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)", borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: 12 }
const btnStyle: React.CSSProperties = { background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)", borderRadius: 4, padding: '3px 10px', cursor: 'pointer', fontSize: 11 }
