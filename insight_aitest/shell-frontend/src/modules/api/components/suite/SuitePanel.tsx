import { useEffect, useRef, useState } from 'react'
import { Play } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useSuiteStore } from '../../store/suiteStore'
import { useRunStore } from '../../store/runStore'
import { EnvironmentSelect } from '../EnvironmentSelect'
import { SuiteEditor } from './SuiteEditor'
import { SuiteRunList } from './SuiteRunList'
import { SuiteRunDetail } from './SuiteRunDetail'
import type { RunDetail } from '../../store/runStore'

export function SuitePanel({ suiteId, onNew }: { suiteId: number | null; onNew: () => void }) {
  const { suites, runs, selectedRun, executing, loadSuites,
          createSuite, updateSuite, executeSuite, loadRunDetail } = useSuiteStore()
  const { cases, loadCases } = useRunStore()
  const { t } = useTranslation()
  const [editing, setEditing] = useState(false)
  const [envId, setEnvId] = useState<number | null>(null)
  const [caseRuns, setCaseRuns] = useState<CaseRunSummary[]>([])

  // 轮询 interval ref（防泄漏）
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => { loadCases(); loadSuites() }, [loadCases, loadSuites])

  // 组件卸载或切换套件时清理轮询
  const clearPoll = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }
  useEffect(() => () => clearPoll(), [])

  const suite = suites.find((s) => s.id === suiteId)

  // 选中 run 变化时，并行 fetch 子 run 详情 → caseRuns
  useEffect(() => {
    if (!selectedRun || selectedRun.case_run_ids.length === 0) { setCaseRuns([]); return }
    let cancelled = false
    Promise.all(
      selectedRun.case_run_ids.map((id) =>
        fetch(`/api/modules/api/runs/${id}`).then((r) => (r.ok ? r.json() : null)).catch(() => null)
      )
    ).then((results) => {
      if (cancelled) return
      setCaseRuns(results.filter((r): r is RunDetail => r != null).map((r) => ({
        id: r.id, status: r.status, case_title: r.case_title,
        passed_steps: r.passed_steps, total_steps: r.total_steps,
      })))
    })
    return () => { cancelled = true }
  }, [selectedRun])

  const doExecute = async () => {
    if (!suiteId) return
    clearPoll()
    const srid = await executeSuite(suiteId, envId)
    await loadRunDetail(srid)
    // 轮询（带泄漏防护）
    pollRef.current = setInterval(async () => {
      await loadRunDetail(srid)
      const cur = useSuiteStore.getState().selectedRun
      if (cur && cur.status !== 'running') clearPoll()
    }, 1500)
  }

  if (editing || !suiteId) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <SuiteEditor
          initial={suite ? { name: suite.name, description: suite.description, case_ids: suite.case_ids, setup: suite.setup, teardown: suite.teardown } : null}
          cases={cases}
          onSave={async (data) => {
            if (suiteId) await updateSuite(suiteId, data)
            else await createSuite(data)
            setEditing(false)
            onNew()
          }}
          onCancel={() => setEditing(false)} />
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--bg-card)', display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 13, color: "var(--text-primary)", flex: 1 }}>{suite?.name ?? t('api.suite')}</span>
        <EnvironmentSelect value={envId} onChange={setEnvId} />
        <button onClick={doExecute} disabled={executing} style={{ ...primaryBtn, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          {executing ? t('api.executing') : <><Play size={12} strokeWidth={1.5} /> {t('api.runSuiteBtn')}</>}
        </button>
        <button onClick={() => setEditing(true)} style={secondaryBtn}>{t('api.editBtn')}</button>
      </div>
      <div style={{ height: 200, borderBottom: '1px solid var(--bg-card)' }}>
        <SuiteRunList runs={runs} selectedRunId={selectedRun?.id ?? null} onSelect={loadRunDetail} />
      </div>
      <div style={{ flex: 1, overflow: 'auto' }}>
        <SuiteRunDetail run={selectedRun} caseRuns={caseRuns} />
      </div>
    </div>
  )
}

interface CaseRunSummary {
  id: number; status: string; case_title: string
  passed_steps: number; total_steps: number
}

const primaryBtn: React.CSSProperties = { background: "var(--accent)", color: "var(--bg-base)", border: 'none', borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: 12, fontWeight: 600 }
const secondaryBtn: React.CSSProperties = { background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)", borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: 12 }
