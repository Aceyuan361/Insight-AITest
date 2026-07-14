import { create } from 'zustand';
import { useProjectStore } from '../../../shared/store/projectStore';

export interface UiCase {
  id: number;
  title: string;
  status: string;
  content: { base_url?: string; steps: any[] };
}

export interface BatchRunSummary {
  id: number;
  name: string;
  case_ids: number[];
  status: 'running' | 'passed' | 'failed' | 'error';
  total: number;
  passed: number;
  failed: number;
  error: number;
  started_at: string;
  finished_at: string | null;
}

export interface BatchRunDetail extends BatchRunSummary {
  config: { base_url?: string; browser_config?: any };
  case_run_ids: number[];
  child_runs: {
    id: number; case_id: number; case_title: string; status: string;
    total_steps: number; passed_steps: number; duration_ms: number;
  }[];
}

interface BatchState {
  cases: UiCase[];
  loadingCases: boolean;
  runs: BatchRunSummary[];
  selectedRun: BatchRunDetail | null;
  executing: boolean;

  loadCases: () => Promise<void>;
  execute: (caseIds: number[], baseUrl?: string) => Promise<void>;
  loadRuns: () => Promise<void>;
  loadDetail: (id: number) => Promise<void>;
}

const API_BASE = '/api/modules/ui';
const TC_BASE = '/api/modules/testcase/testcases';

export const useBatchStore = create<BatchState>((set, get) => ({
  cases: [],
  loadingCases: false,
  runs: [],
  selectedRun: null,
  executing: false,

  loadCases: async () => {
    set({ loadingCases: true });
    try {
      const { currentProjectId, currentVersionId } = useProjectStore.getState();
      const params = new URLSearchParams({ type: 'ui' });
      if (currentProjectId !== null) params.set('project_id', String(currentProjectId));
      if (currentVersionId !== null) params.set('version_id', String(currentVersionId));
      const r = await fetch(`${TC_BASE}?${params}`);
      set({ cases: await r.json() });
    } finally {
      set({ loadingCases: false });
    }
  },

  execute: async (caseIds, baseUrl) => {
    set({ executing: true });
    try {
      const browserConfigStr = localStorage.getItem('ui_browser_config');
      const browser_config = browserConfigStr ? JSON.parse(browserConfigStr) : null;
      const r = await fetch(`${API_BASE}/batch/execute`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_ids: caseIds, base_url: baseUrl || null, browser_config }),
      });
      if (!r.ok) throw new Error(await r.text());
      // 延迟刷新（批量执行是异步的）
      setTimeout(() => get().loadRuns(), 2000);
    } finally {
      set({ executing: false });
    }
  },

  loadRuns: async () => {
    const r = await fetch(`${API_BASE}/batch/runs`);
    set({ runs: await r.json() });
  },

  loadDetail: async (id) => {
    const r = await fetch(`${API_BASE}/batch/runs/${id}`);
    if (r.ok) set({ selectedRun: await r.json() });
  },
}));
