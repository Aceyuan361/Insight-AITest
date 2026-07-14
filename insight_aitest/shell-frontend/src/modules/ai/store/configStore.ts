import { create } from 'zustand';

/** 后端 GET /config 返回的脱敏配置（spec §6.6）。 */
export interface AIConfig {
  llm_base_url: string;
  chat_model: string;
  vision_model: string;
  embed_model: string;
  embed_dim: number;
  api_key_set: boolean;
  chunk_size: number;
  chunk_overlap: number;
  top_k: number;
  min_score: number;
  rerank_enabled: boolean;
  rerank_fetch_k: number;
  history_turns: number;
  ocr_enabled: boolean;
  vector_enabled: boolean;
  embed_base_url: string;
  embed_api_key_set: boolean;
  // 多 Provider
  providers: ProviderOut[];
  active_provider_id: string;
}

/** PUT /config 的可写字段（全部可选）。embed_dim 不在此列（不可热更新）。 */
export interface AIConfigUpdate {
  llm_base_url?: string;
  llm_api_key?: string;
  chat_model?: string;
  vision_model?: string;
  embed_model?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  top_k?: number;
  min_score?: number;
  rerank_enabled?: boolean;
  rerank_fetch_k?: number;
  history_turns?: number;
  ocr_enabled?: boolean;
  vector_enabled?: boolean;
  embed_base_url?: string;
  embed_api_key?: string;
}

/** 后端返回的 Provider（api_key 脱敏为 api_key_set）。 */
export interface ProviderOut {
  id: string;
  name: string;
  base_url: string;
  chat_model: string;
  vision_model: string;
  api_key_set: boolean;
}

/** 新增/更新 Provider 的请求体。 */
export interface ProviderUpsert {
  id?: string;
  name: string;
  base_url: string;
  api_key?: string;
  chat_model?: string;
  vision_model?: string;
}

/** 内置 Provider 预设（从 GET /config/presets 拉取）。 */
export interface ProviderPreset {
  name: string;
  base_url: string;
  models: string[];
}

interface ConfigState {
  config: AIConfig | null;
  loading: boolean;
  saving: boolean;
  presets: ProviderPreset[];

  loadConfig: () => Promise<void>;
  updateConfig: (patch: AIConfigUpdate) => Promise<void>;
  loadPresets: () => Promise<void>;
  upsertProvider: (providerId: string, body: ProviderUpsert) => Promise<void>;
  deleteProvider: (providerId: string) => Promise<void>;
  activateProvider: (providerId: string) => Promise<void>;
  testConnection: (baseUrl: string, apiKey: string, model: string) => Promise<{ ok: boolean; message: string }>;
}

const BASE = '/api/modules/ai';

export const useConfigStore = create<ConfigState>((set) => ({
  config: null,
  loading: false,
  saving: false,
  presets: [],

  loadConfig: async () => {
    set({ loading: true });
    try {
      const r = await fetch(`${BASE}/config`);
      const config = await r.json();
      set({ config });
    } finally {
      set({ loading: false });
    }
  },

  updateConfig: async (patch: AIConfigUpdate) => {
    set({ saving: true });
    try {
      const r = await fetch(`${BASE}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      });
      if (!r.ok) {
        const msg = await r.text();
        throw new Error(msg || `保存失败（${r.status}）`);
      }
      const config = await r.json();
      set({ config });
    } finally {
      set({ saving: false });
    }
  },

  loadPresets: async () => {
    try {
      const r = await fetch(`${BASE}/config/presets`);
      const data = await r.json();
      set({ presets: data.presets || [] });
    } catch {
      // 预设加载失败不阻塞
    }
  },

  upsertProvider: async (providerId: string, body: ProviderUpsert) => {
    set({ saving: true });
    try {
      const r = await fetch(`${BASE}/config/providers/${providerId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const msg = await r.text();
        throw new Error(msg || `保存失败（${r.status}）`);
      }
      const config = await r.json();
      set({ config });
    } finally {
      set({ saving: false });
    }
  },

  deleteProvider: async (providerId: string) => {
    set({ saving: true });
    try {
      const r = await fetch(`${BASE}/config/providers/${providerId}`, {
        method: 'DELETE',
      });
      if (!r.ok) {
        const msg = await r.text();
        throw new Error(msg || `删除失败（${r.status}）`);
      }
      const config = await r.json();
      set({ config });
    } finally {
      set({ saving: false });
    }
  },

  activateProvider: async (providerId: string) => {
    set({ saving: true });
    try {
      const r = await fetch(`${BASE}/config/activate/${providerId}`, {
        method: 'PUT',
      });
      if (!r.ok) {
        const msg = await r.text();
        throw new Error(msg || `切换失败（${r.status}）`);
      }
      const config = await r.json();
      set({ config });
    } finally {
      set({ saving: false });
    }
  },

  testConnection: async (baseUrl: string, apiKey: string, model: string) => {
    const r = await fetch(`${BASE}/config/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ base_url: baseUrl, api_key: apiKey, model }),
    });
    const data = await r.json();
    return { ok: !!data.ok, message: data.message || '' };
  },
}));

/** 兼容旧引用（现改为从后端 loadPresets() 拉取，此常量保留空数组避免破坏旧 import）。 */
export const LLM_PRESETS: { label: string; base_url: string }[] = [];
