import { create } from 'zustand'

export interface Schedule {
  id: number; name: string; suite_id: number
  cron_expression: string; environment_id: number | null
  enabled: boolean
  last_run_at: string | null; last_status: string | null
  last_suite_run_id: number | null
  created_at: string; updated_at: string
}

interface SchedState {
  schedules: Schedule[]
  loading: boolean
  unavailable: boolean  // 后端未加载 scheduler 模块（404）
  loadSchedules: () => Promise<void>
  createSchedule: (data: { name: string; suite_id: number; cron_expression: string; environment_id?: number | null; enabled?: boolean }) => Promise<void>
  updateSchedule: (id: number, data: Partial<Schedule>) => Promise<void>
  deleteSchedule: (id: number) => Promise<void>
  triggerSchedule: (id: number) => Promise<void>
}

const BASE = '/api/modules/api/schedules'

export const useSchedStore = create<SchedState>((set, get) => ({
  schedules: [], loading: false, unavailable: false,
  loadSchedules: async () => {
    set({ loading: true, unavailable: false })
    try {
      const r = await fetch(BASE)
      if (r.status === 404) {
        // 后端尚未加载定时调度模块（需重启后端）
        set({ schedules: [], unavailable: true })
        return
      }
      if (!r.ok) throw new Error(`API ${r.status}: ${await r.text().catch(() => '')}`)
      set({ schedules: await r.json(), unavailable: false })
    } catch (e) {
      console.error('loadSchedules failed:', e)
      set({ unavailable: true })
    } finally {
      set({ loading: false })
    }
  },
  createSchedule: async (data) => {
    const r = await fetch(BASE, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) })
    if (!r.ok) throw new Error(`创建失败: ${r.status}`)
    await get().loadSchedules()
  },
  updateSchedule: async (id, data) => {
    const r = await fetch(`${BASE}/${id}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) })
    if (!r.ok) throw new Error(`更新失败: ${r.status}`)
    await get().loadSchedules()
  },
  deleteSchedule: async (id) => {
    const r = await fetch(`${BASE}/${id}`, { method: 'DELETE' })
    if (!r.ok) throw new Error(`删除失败: ${r.status}`)
    await get().loadSchedules()
  },
  triggerSchedule: async (id) => {
    const r = await fetch(`${BASE}/${id}/run`, { method: 'POST' })
    if (!r.ok) throw new Error(`触发失败: ${r.status}`)
  },
}))
