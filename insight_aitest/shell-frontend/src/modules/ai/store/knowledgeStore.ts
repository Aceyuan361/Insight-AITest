import { create } from 'zustand';

export interface Document {
  id: number;
  filename: string;
  status: string;  // pending|parsing|chunking|embedding|ready|*_failed|embed_partial
  char_count: number;
  chunk_count: number;
  error_message: string | null;
  created_at: string;
}

interface KnowledgeState {
  documents: Document[];
  uploading: boolean;
  pollTimer: number | null;
  loadDocuments: () => Promise<void>;
  uploadDocument: (file: File) => Promise<void>;
  deleteDocument: (id: number) => Promise<void>;
  startPolling: () => void;
  stopPolling: () => void;
}

const BASE = '/api/modules/ai';

const NON_TERMINAL = ['pending', 'parsing', 'chunking', 'embedding'];

export const useKnowledgeStore = create<KnowledgeState>((set, get) => ({
  documents: [],
  uploading: false,
  pollTimer: null,

  loadDocuments: async () => {
    try {
      const r = await fetch(`${BASE}/documents`);
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
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(`${BASE}/documents`, { method: 'POST', body: fd });
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
    await fetch(`${BASE}/documents/${id}`, { method: 'DELETE' });
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
}));
