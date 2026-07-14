import { create } from 'zustand';

export interface Project {
  id: number;
  name: string;
  description: string;
  color: string;
  version_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectVersion {
  id: number;
  project_id: number;
  name: string;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface ProjectState {
  projects: Project[];
  versions: ProjectVersion[];          // 当前选中项目的版本列表
  currentProjectId: number | null;     // null = 全部
  currentVersionId: number | null;     // null = 项目下全部
  loadProjects: () => Promise<void>;
  loadVersions: (projectId: number) => Promise<void>;
  setProject: (projectId: number | null) => void;
  setVersion: (versionId: number | null) => void;
}

const BASE = '/api/platform';

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  versions: [],
  currentProjectId: null,
  currentVersionId: null,

  loadProjects: async () => {
    try {
      const r = await fetch(`${BASE}/projects`);
      if (!r.ok) return;
      const data = await r.json();
      set({ projects: Array.isArray(data) ? data : [] });
    } catch {
      /* 静默（后端未启动时不阻塞前端渲染） */
    }
  },

  loadVersions: async (projectId: number) => {
    try {
      const r = await fetch(`${BASE}/projects/${projectId}/versions`);
      if (!r.ok) return;
      const data = await r.json();
      set({ versions: Array.isArray(data) ? data : [] });
    } catch {
      set({ versions: [] });
    }
  },

  setProject: (projectId: number | null) => {
    set({ currentProjectId: projectId, currentVersionId: null, versions: [] });
    if (projectId !== null) {
      get().loadVersions(projectId);
    }
  },

  setVersion: (versionId: number | null) => {
    set({ currentVersionId: versionId });
  },
}));
