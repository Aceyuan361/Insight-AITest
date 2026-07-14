import { create } from 'zustand';

interface UIConfig {
  base_url: string;
  api_key_set: boolean;
  model: string;
  global_base_url: string;
  global_model: string;
}

interface ConfigState {
  config: UIConfig | null;
  loading: boolean;
  saving: boolean;

  load: () => Promise<void>;
  save: (data: { base_url?: string; api_key?: string; model?: string }) => Promise<void>;
  test: (base_url: string, api_key: string, model: string) => Promise<{ ok: boolean; message: string }>;
}

const BASE = '/api/modules/ui/config';

export const useConfigStore = create<ConfigState>((set) => ({
  config: null,
  loading: false,
  saving: false,

  load: async () => {
    set({ loading: true });
    try {
      const r = await fetch(BASE);
      if (r.ok) set({ config: await r.json() });
    } finally {
      set({ loading: false });
    }
  },

  save: async (data) => {
    set({ saving: true });
    try {
      const r = await fetch(BASE, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!r.ok) throw new Error(await r.text());
      set({ config: await r.json() });
    } finally {
      set({ saving: false });
    }
  },

  test: async (base_url, api_key, model) => {
    const r = await fetch(`${BASE}/test`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ base_url, api_key, model }),
    });
    return r.json();
  },
}));
