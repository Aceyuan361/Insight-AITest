import { create } from 'zustand';
import { useProjectStore } from '../../../shared/store/projectStore';

/** D 的 UI 用例（只读引用）。 */
export interface UiCase {
  id: number;
  title: string;
  status: string;
  content: { base_url?: string; steps: any[] };
  last_result: string | null;
}

export interface UIStepResult {
  step_index: number;
  kind: 'action' | 'assert' | 'extract';
  prompt: string;
  screenshot: string | null;
  action_log: string | null;
  assert_passed: boolean | null;
  extracts: Record<string, any>;
  elapsed_ms: number;
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
  base_url_used: string;
}

export interface RunDetail extends RunSummary {
  steps: UIStepResult[];
}

interface BrowserConfig {
  headless?: boolean;
  viewport_width?: number;
  viewport_height?: number;
  timeout?: number;
  retry?: number;
  screenshot_on_failure?: boolean;
}

interface RunState {
  cases: UiCase[];
  selectedCaseId: number | null;
  runs: RunSummary[];
  selectedRun: RunDetail | null;
  executing: boolean;
  loadingCases: boolean;
  execError: string | null;

  loadCases: () => Promise<void>;
  selectCase: (id: number) => void;
  loadRuns: (caseId: number) => Promise<void>;
  execute: (caseId: number, baseUrl?: string, browserConfig?: BrowserConfig) => Promise<void>;
  loadRunDetail: (runId: number) => Promise<void>;
}

const API_BASE = '/api/modules/ui';
const TC_BASE = '/api/modules/testcase/testcases';

export const useRunStore = create<RunState>((set, get) => ({
  cases: [],
  selectedCaseId: null,
  runs: [],
  selectedRun: null,
  executing: false,
  loadingCases: false,
  execError: null,

  loadCases: async () => {
    set({ loadingCases: true });
    try {
      const { currentProjectId, currentVersionId } = useProjectStore.getState();
      const params = new URLSearchParams({ type: 'ui' });
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

  execute: async (caseId, baseUrl, browserConfig) => {
    set({ executing: true, execError: null });
    try {
      const r = await fetch(`${API_BASE}/runs/execute?base_url=${encodeURIComponent(baseUrl || '')}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_id: caseId, browser_config: browserConfig || null }),
      });
      if (!r.ok) {
        const errText = await r.text();
        let msg = errText || '执行失败';
        try { const j = JSON.parse(errText); if (j.detail) msg = j.detail; } catch {}
        set({ execError: msg });
        return;
      }
      const run: RunDetail = await r.json();
      await get().loadRuns(caseId);
      set({ selectedRun: run });
    } catch (e) {
      set({ execError: String(e) });
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
