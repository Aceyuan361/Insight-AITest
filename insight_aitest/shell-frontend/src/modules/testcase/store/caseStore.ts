import { create } from 'zustand';
import { useProjectStore } from '../../../shared/store/projectStore';

export interface TestCase {
  id: number;
  title: string;
  type: string;            // functional|api|performance|ui
  description: string;
  priority: string;        // p0|p1|p2|p3
  status: string;          // draft|reviewed|ready|deprecated
  test_design: string;     // positive|negative|boundary|edge
  preconditions: string;
  content: Record<string, unknown>;
  tags: string[];
  source: string;
  project_id: number | null;
  version_id: number | null;
  last_run_at: string | null;
  last_result: string | null;
  created_at: string;
  updated_at: string;
}

export interface TestPoint {
  id: string;
  summary: string;
  suggested_type: string;
  suggested_design: string;
  rationale: string;
}

interface CaseState {
  cases: TestCase[];
  activeId: number | null;
  loading: boolean;
  // 生成向导临时态
  analyzeLoading: boolean;
  analyzePoints: TestPoint[];
  generateProgress: { done: number; total: number } | null;
  imageGenerating: boolean;

  loadCases: (type?: string, status?: string) => Promise<void>;
  selectCase: (id: number) => void;
  createCase: (data: Partial<TestCase>) => Promise<number>;
  updateCase: (id: number, data: Partial<TestCase>) => Promise<void>;
  updateStatus: (id: number, status: string) => Promise<void>;
  deleteCase: (id: number) => Promise<void>;
  analyze: (query: string, documentIds?: number[] | null) => Promise<void>;
  generateFromPoint: (point: TestPoint, documentIds?: number[] | null,
                      type?: string, design?: string) => Promise<void>;
  generateFromImage: (images: { data: string; mime: string }[], baseUrl: string,
                      pointSummary?: string) => Promise<TestCase | null>;

  // P2: 统一通过 AI /tasks/quick 创建预置任务（analyze_generate | image_generate）
  createQuickTask: (mode: 'analyze_generate' | 'image_generate', payload: Record<string, unknown>) => Promise<{ task_id: number; source_mode: string }>;
  // P2: 迁移用例归属（项目 / 版本）
  assignCase: (caseId: number, projectId?: number, versionId?: number) => Promise<TestCase>;
}

const BASE = '/api/modules/testcase';

export const useCaseStore = create<CaseState>((set) => ({
  cases: [],
  activeId: null,
  loading: false,
  analyzeLoading: false,
  analyzePoints: [],
  generateProgress: null,
  imageGenerating: false,

  loadCases: async (type?: string, status?: string) => {
    set({ loading: true });
    try {
      const { currentProjectId, currentVersionId } = useProjectStore.getState();
      const params = new URLSearchParams();
      if (type) params.set('type', type);
      if (status) params.set('status', status);
      if (currentProjectId !== null) params.set('project_id', String(currentProjectId));
      if (currentVersionId !== null) params.set('version_id', String(currentVersionId));
      const q = params.toString() ? `?${params}` : '';
      const r = await fetch(`${BASE}/testcases${q}`);
      const cases = await r.json();
      set({ cases });
    } finally {
      set({ loading: false });
    }
  },

  selectCase: (id: number) => set({ activeId: id }),

  createCase: async (data) => {
    const { currentProjectId, currentVersionId } = useProjectStore.getState();
    const r = await fetch(`${BASE}/testcases`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...data,
        project_id: data.project_id ?? currentProjectId,
        version_id: data.version_id ?? currentVersionId,
      }),
    });
    const c = await r.json();
    set((s) => ({ cases: [c, ...s.cases], activeId: c.id }));
    return c.id;
  },

  updateCase: async (id, data) => {
    const r = await fetch(`${BASE}/testcases/${id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const updated = await r.json();
    set((s) => ({ cases: s.cases.map((c) => (c.id === id ? updated : c)) }));
  },

  updateStatus: async (id, status) => {
    const r = await fetch(`${BASE}/testcases/${id}/status`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    const updated = await r.json();
    set((s) => ({ cases: s.cases.map((c) => (c.id === id ? updated : c)) }));
  },

  deleteCase: async (id) => {
    await fetch(`${BASE}/testcases/${id}`, { method: 'DELETE' });
    set((s) => ({
      cases: s.cases.filter((c) => c.id !== id),
      activeId: s.activeId === id ? null : s.activeId,
    }));
  },

  analyze: async (query, documentIds) => {
    set({ analyzeLoading: true, analyzePoints: [] });
    try {
      const r = await fetch(`${BASE}/testcases/analyze`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, document_ids: documentIds ?? null }),
      });
      const points = await r.json();
      set({ analyzePoints: points });
    } finally {
      set({ analyzeLoading: false });
    }
  },

  generateFromPoint: async (point, documentIds, type, design) => {
    const { currentProjectId, currentVersionId } = useProjectStore.getState();
    const r = await fetch(`${BASE}/testcases/generate`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        point, document_ids: documentIds ?? null,
        type: type ?? null, test_design: design ?? null,
        project_id: currentProjectId, version_id: currentVersionId,
      }),
    });
    if (r.ok) {
      const c: TestCase = await r.json();
      set((s) => ({ cases: [c, ...s.cases.filter((x) => x.id !== c.id)] }));
    }
  },

  generateFromImage: async (images, baseUrl, pointSummary) => {
    set({ imageGenerating: true });
    try {
      const r = await fetch(`${BASE}/testcases/generate-from-image`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          images: images.map((img) => ({ data: img.data, mime: img.mime })),
          base_url: baseUrl,
          point_summary: pointSummary ?? '',
          project_id: useProjectStore.getState().currentProjectId,
          version_id: useProjectStore.getState().currentVersionId,
        }),
      });
      if (!r.ok) {
        const msg = await r.text();
        throw new Error(`生成失败: ${msg}`);
      }
      const c: TestCase = await r.json();
      set((s) => ({
        cases: [c, ...s.cases.filter((x) => x.id !== c.id)],
        activeId: c.id,
      }));
      return c;
    } finally {
      set({ imageGenerating: false });
    }
  },

  createQuickTask: async (mode, payload) => {
    const resp = await fetch('/api/modules/ai/tasks/quick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, ...payload }),
    });
    if (!resp.ok) throw new Error(await resp.text());
    return resp.json();
  },

  assignCase: async (caseId, projectId, versionId) => {
    const resp = await fetch(`/api/modules/testcase/testcases/${caseId}/assignment`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId, version_id: versionId }),
    });
    if (!resp.ok) throw new Error(await resp.text());
    const updated: TestCase = await resp.json();
    set((s) => ({ cases: s.cases.map((c) => (c.id === caseId ? updated : c)) }));
    return updated;
  },
}));
