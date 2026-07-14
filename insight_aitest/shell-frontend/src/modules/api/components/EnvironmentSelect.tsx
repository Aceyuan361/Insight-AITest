import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useEnvStore } from '../store/envStore'

export function EnvironmentSelect({ value, onChange }: {
  value: number | null; onChange: (id: number | null) => void
}) {
  const { envs, loadEnvs } = useEnvStore()
  const { t } = useTranslation()
  useEffect(() => { loadEnvs() }, [loadEnvs])
  return (
    <select style={selectStyle} value={value ?? ''} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}>
      <option value="">{t('api.noEnv')}</option>
      {envs.map((e) => <option key={e.id} value={e.id}>{e.name}{e.is_default ? t('api.defaultEnv') : ''}</option>)}
    </select>
  )
}

const selectStyle: React.CSSProperties = {
  background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', borderRadius: 4,
  color: "var(--text-primary)", padding: '4px 8px', fontSize: 12,
}
