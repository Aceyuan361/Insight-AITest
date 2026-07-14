import { create } from 'zustand';

export interface UISchedule {
  id: number;
  name: string;
  cron_expression: string;
  case_ids: number[];
  base_url: string | null;
  browser_config: any;
  enabled: boolean;
  last_run_at: string | null;
  last_status: string | null;
  last_batch_run_id: number | null;
  created_at: string;
  updated_at: string;
}

interface SchedState {
  schedules: UISchedule[];
  loading: boolean;
  unavailable: boolean;

  load: () => Promise<void>;
  create: (data: { name: string; cron_expression: string; case_ids: number[]; base_url?: string | null }) => Promise<void>;
  update: (id: number, data: Partial<UISchedule>) => Promise<void>;
  remove: (id: number) => Promise<void>;
  trigger: (id: number) => Promise<void>;
}

const BASE = '/api/modules/ui/schedules';

export const useSchedStore = create<SchedState>((set, get) => ({
  schedules: [],
  loading: false,
  unavailable: false,

  load: async () => {
    set({ loading: true, unavailable: false });
    try {
      const r = await fetch(BASE);
      if (r.status === 404) {
        set({ schedules: [], unavailable: true });
        return;
      }
      if (!r.ok) throw new Error(await r.text());
      set({ schedules: await r.json() });
    } catch {
      set({ unavailable: true });
    } finally {
      set({ loading: false });
    }
  },

  create: async (data) => {
    const r = await fetch(BASE, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!r.ok) throw new Error(await r.text());
    await get().load();
  },

  update: async (id, data) => {
    const r = await fetch(`${BASE}/${id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!r.ok) throw new Error(await r.text());
    await get().load();
  },

  remove: async (id) => {
    const r = await fetch(`${BASE}/${id}`, { method: 'DELETE' });
    if (!r.ok) throw new Error(await r.text());
    await get().load();
  },

  trigger: async (id) => {
    const r = await fetch(`${BASE}/${id}/run`, { method: 'POST' });
    if (!r.ok) throw new Error(await r.text());
  },
}));
