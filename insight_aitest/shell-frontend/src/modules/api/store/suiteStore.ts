import { create } from 'zustand'
import type { StepData } from '../components/step/StepEditor'

export interface Suite {
  id: number; name: string; description: string
  case_ids: number[]; setup: StepData[]; teardown: StepData[]
  case_count: number
}

export interface SuiteRunSummary {
  id: number; suite_id: number; suite_name: string
  status: 'running' | 'completed' | 'failed' | 'interrupted'
  total: number; done: number; setup_status: string | null
  started_at: string; finished_at: string | null
  environment_name: string | null
}

export interface SuiteRunDetail extends SuiteRunSummary {
  case_run_ids: number[]; error: string | null
}

async function _jsonOrThrow(r: Response) {
  if (!r.ok) {
    const msg = await r.text().catch(() => r.statusText)
    throw new Error(`API ${r.status}: ${msg}`)
  }
  return r.json()
}

interface SuiteState {
  suites: Suite[]
  selectedSuiteId: number | null
  runs: SuiteRunSummary[]
  selectedRun: SuiteRunDetail | null
  executing: boolean
  loadSuites: () => Promise<void>
  selectSuite: (id: number) => void
  createSuite: (data: any) => Promise<void>
  updateSuite: (id: number, data: any) => Promise<void>
  deleteSuite: (id: number) => Promise<void>
  loadRuns: (suiteId: number) => Promise<void>
  executeSuite: (suiteId: number, envId: number | null) => Promise<number>
  loadRunDetail: (runId: number) => Promise<void>
}

const BASE = '/api/modules/api/suites'

export const useSuiteStore = create<SuiteState>((set, get) => ({
  suites: [], selectedSuiteId: null, runs: [], selectedRun: null, executing: false,
  loadSuites: async () => {
    const r = await fetch(BASE)
    set({ suites: await _jsonOrThrow(r) })
  },
  selectSuite: (id) => { set({ selectedSuiteId: id, selectedRun: null }); get().loadRuns(id) },
  createSuite: async (data) => {
    const r = await fetch(BASE, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data) })
    await _jsonOrThrow(r)
    await get().loadSuites()
  },
  updateSuite: async (id, data) => {
    const r = await fetch(`${BASE}/${id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data) })
    await _jsonOrThrow(r)
    await get().loadSuites()
  },
  deleteSuite: async (id) => {
    const r = await fetch(`${BASE}/${id}`, { method: 'DELETE' })
    if (!r.ok) throw new Error(`删除套件失败: ${r.status}`)
    await get().loadSuites()
  },
  loadRuns: async (suiteId) => {
    const r = await fetch(`${BASE}/runs?suite_id=${suiteId}`)
    set({ runs: await _jsonOrThrow(r) })
  },
  executeSuite: async (suiteId, envId) => {
    set({ executing: true })
    try {
      const url = envId ? `${BASE}/${suiteId}/execute?environment_id=${envId}` : `${BASE}/${suiteId}/execute`
      const r = await fetch(url, { method: 'POST' })
      const body = await _jsonOrThrow(r)
      await get().loadRuns(suiteId)
      return body.suite_run_id
    } finally { set({ executing: false }) }
  },
  loadRunDetail: async (runId) => {
    const r = await fetch(`${BASE}/runs/${runId}`)
    if (r.ok) set({ selectedRun: await r.json() })
  },
}))
