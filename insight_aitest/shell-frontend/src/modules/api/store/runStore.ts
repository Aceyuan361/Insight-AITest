import { create } from 'zustand';
import { useProjectStore } from '../../../shared/store/projectStore';

/** D 的 API 用例（只读引用）。 */
export interface ApiCase {
  id: number;
  title: string;
  status: string;
  content: { base_url?: string; steps: any[] };
  last_result: string | null;
}

export interface StepResult {
  step_index: number;
  request: { method: string; url: string; headers: Record<string, string>; body: any };
  status_code: number | null;
  response_body: any;
  response_headers: Record<string, string>;
  elapsed_ms: number;
  assertions: { type: string; target: string; expected: any; actual: any; passed: boolean }[];
  extracts: Record<string, any>;
  error: string | null;
  passed: boolean;
}

export interface RunSummary {
  id: number;
  case_id: number;
  case_title: string;
  status: 'passed' | 'failed' | 'error';
  total_steps: number;
  passed_steps: number;
  started_at: string;
  duration_ms: number;
}

export interface RunDetail extends RunSummary {
  steps: StepResult[];
}

interface RunState {
  cases: ApiCase[];
  selectedCaseId: number | null;
  runs: RunSummary[];
  selectedRun: RunDetail | null;
  executing: boolean;
  loadingCases: boolean;

  loadCases: () => Promise<void>;
  selectCase: (id: number) => void;
  loadRuns: (caseId: number) => Promise<void>;
  execute: (caseId: number, environmentId?: number | null) => Promise<void>;
  loadRunDetail: (runId: number) => Promise<void>;
}

const API_BASE = '/api/modules/api';
const TC_BASE = '/api/modules/testcase/testcases';

export const useRunStore = create<RunState>((set, get) => ({
  cases: [],
  selectedCaseId: null,
  runs: [],
  selectedRun: null,
  executing: false,
  loadingCases: false,

  loadCases: async () => {
    set({ loadingCases: true });
    try {
      const { currentProjectId, currentVersionId } = useProjectStore.getState();
      const params = new URLSearchParams({ type: 'api' });
      if (currentProjectId !== null) params.set('project_id', String(currentProjectId));
      if (currentVersionId !== null) params.set('version_id', String(currentVersionId));
      const r = await fetch(`${TC_BASE}?${params}`);
      const cases = await r.json();
      set({ cases });
    } finally {
      set({ loadingCases: false });
    }
  },

  selectCase: (id) => {
    set({ selectedCaseId: id, runs: [], selectedRun: null });
    get().loadRuns(id);
  },

  loadRuns: async (caseId) => {
    const r = await fetch(`${API_BASE}/runs?case_id=${caseId}`);
    const runs = await r.json();
    set({ runs });
  },

  execute: async (caseId, environmentId = null) => {
    set({ executing: true });
    try {
      const url = environmentId
        ? `${API_BASE}/runs/execute?environment_id=${environmentId}`
        : `${API_BASE}/runs/execute`;
      const r = await fetch(url, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_id: caseId }),
      });
      if (!r.ok) throw new Error((await r.text()) || '执行失败');
      const run: RunDetail = await r.json();
      // 刷新历史 + 自动选中最新
      await get().loadRuns(caseId);
      set({ selectedRun: run });
    } finally {
      set({ executing: false });
    }
  },

  loadRunDetail: async (runId) => {
    const r = await fetch(`${API_BASE}/runs/${runId}`);
    if (r.ok) {
      const run = await r.json();
      set({ selectedRun: run });
    }
  },
}));
