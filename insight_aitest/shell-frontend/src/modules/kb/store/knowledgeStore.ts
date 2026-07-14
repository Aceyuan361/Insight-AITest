import { create } from 'zustand';
import { useProjectStore } from '../../../shared/store/projectStore';

export interface Document {
  id: number;
  filename: string;
  status: string;  // pending|parsing|chunking|embedding|ready|*_failed|embed_partial
  char_count: number;
  chunk_count: number;
  error_message: string | null;
  project_id: number | null;
  version_id: number | null;
  tags: string[];
  doc_type: string;
  description: string;
  created_at: string;
}

export interface DocVersion {
  id: number;
  document_id: number;
  version_no: number;
  char_count: number;
  chunk_count: number;
  note: string;
  is_current: number;
  created_at: string;
}

export interface TagCount {
  tag: string;
  count: number;
}

interface KnowledgeState {
  documents: Document[];
  uploading: boolean;
  saving: boolean;
  pollTimer: number | null;
  tags: TagCount[];
  loadDocuments: () => Promise<void>;
  uploadDocument: (file: File) => Promise<void>;
  deleteDocument: (id: number) => void;
  startPolling: () => void;
  stopPolling: () => void;
  // KB 升级新增
  fetchContent: (id: number) => Promise<{ text: string; filename: string; mime_type: string | null }>;
  saveContent: (id: number, text: string, note?: string) => Promise<void>;
  saveBinaryFile: (id: number, blob: Blob, filename: string, note?: string) => Promise<void>;
  updateMeta: (id: number, meta: { tags?: string[]; doc_type?: string; description?: string }) => Promise<void>;
  loadTags: () => Promise<void>;
  listVersions: (id: number) => Promise<DocVersion[]>;
  getVersionContent: (id: number, versionNo: number) => Promise<string>;
  rollbackVersion: (id: number, versionNo: number) => Promise<void>;
  rawUrl: (id: number) => string;
  exportZipUrl: () => string;
}

const BASE = '/api/modules/kb/documents';

const NON_TERMINAL = ['pending', 'parsing', 'chunking', 'embedding'];

function projectQs(): string {
  const { currentProjectId, currentVersionId } = useProjectStore.getState();
  const params = new URLSearchParams();
  if (currentProjectId !== null) params.set('project_id', String(currentProjectId));
  if (currentVersionId !== null) params.set('version_id', String(currentVersionId));
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

export const useKnowledgeStore = create<KnowledgeState>((set, get) => ({
  documents: [],
  uploading: false,
  saving: false,
  pollTimer: null,
  tags: [],

  loadDocuments: async () => {
    try {
      const qs = projectQs();
      const r = await fetch(`${BASE}${qs}`);
      const docs = await r.json();
      set({ documents: docs });
      // 有非终态文档则启动轮询
      if (docs.some((d: Document) => NON_TERMINAL.includes(d.status))) {
        get().startPolling();
      } else {
        get().stopPolling();
      }
    } catch {
      /* 静默 */
    }
  },

  uploadDocument: async (file: File) => {
    set({ uploading: true });
    try {
      const qs = projectQs();
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(`${BASE}${qs}`, { method: 'POST', body: fd });
      if (!r.ok) {
        const msg = await r.text();
        throw new Error(msg);
      }
      await get().loadDocuments();
    } finally {
      set({ uploading: false });
    }
  },

  deleteDocument: async (id: number) => {
    await fetch(`${BASE}/${id}`, { method: 'DELETE' });
    await get().loadDocuments();
  },

  startPolling: () => {
    if (get().pollTimer) return;
    const t = window.setInterval(() => get().loadDocuments(), 2000);
    set({ pollTimer: t });
  },

  stopPolling: () => {
    const t = get().pollTimer;
    if (t) {
      window.clearInterval(t);
      set({ pollTimer: null });
    }
  },

  // ===== KB 升级新增 =====

  fetchContent: async (id: number) => {
    const r = await fetch(`${BASE}/${id}/content`);
    if (!r.ok) throw new Error('加载内容失败');
    return r.json();
  },

  saveContent: async (id: number, text: string, note = '') => {
    set({ saving: true });
    try {
      const r = await fetch(`${BASE}/${id}/content`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, note }),
      });
      if (!r.ok) throw new Error('保存失败');
      await get().loadDocuments();
    } finally {
      set({ saving: false });
    }
  },

  saveBinaryFile: async (id: number, blob: Blob, filename: string, note = '在线编辑保存') => {
    set({ saving: true });
    try {
      const fd = new FormData();
      fd.append('file', blob, filename);
      fd.append('note', note);
      const r = await fetch(`${BASE}/${id}/file`, { method: 'PUT', body: fd });
      if (!r.ok) throw new Error('保存失败');
      await get().loadDocuments();
    } finally {
      set({ saving: false });
    }
  },

  updateMeta: async (id: number, meta) => {
    const r = await fetch(`${BASE}/${id}/meta`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(meta),
    });
    if (!r.ok) throw new Error('更新元数据失败');
    await get().loadDocuments();
    await get().loadTags();
  },

  loadTags: async () => {
    try {
      const qs = projectQs();
      const r = await fetch(`${BASE}/tags/all${qs}`);
      if (r.ok) set({ tags: await r.json() });
    } catch {
      /* 静默 */
    }
  },

  listVersions: async (id: number) => {
    const r = await fetch(`${BASE}/${id}/versions`);
    if (!r.ok) throw new Error('加载版本失败');
    return r.json();
  },

  getVersionContent: async (id: number, versionNo: number) => {
    const r = await fetch(`${BASE}/${id}/versions/${versionNo}/content`);
    if (!r.ok) throw new Error('加载版本内容失败');
    const data = await r.json();
    return data.text || '';
  },

  rollbackVersion: async (id: number, versionNo: number) => {
    const r = await fetch(`${BASE}/${id}/rollback/${versionNo}`, { method: 'POST' });
    if (!r.ok) throw new Error('回滚失败');
    await get().loadDocuments();
  },

  rawUrl: (id: number) => `${BASE}/${id}/raw`,

  exportZipUrl: () => `${BASE}/export/zip${projectQs()}`,
}));
