/**
 * 主题 store —— 暗黑 / 浅色双主题切换。
 *
 * 通过在 <html data-theme="dark|light"> 上设置属性来驱动 tokens.css 的双主题。
 * 持久化到 localStorage('theme')，默认 'dark'（保持原有深色观感）。
 *
 * 注意：main.tsx 渲染前会同步读取 localStorage 并写入 data-theme，避免 FOUC；
 *      这里在 store 创建时做同样的同步，确保逻辑一致。
 */
import { create } from 'zustand';

export type Theme = 'dark' | 'light';

const STORAGE_KEY = 'theme';

/** 将主题应用到 <html data-theme>。幂等。 */
function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
}

/** 读取已保存的主题，默认 dark。 */
function readStoredTheme(): Theme {
  const saved = localStorage.getItem(STORAGE_KEY);
  return saved === 'light' ? 'light' : 'dark';
}

// 初始化时立即应用，保证与首次渲染一致
const initialTheme = readStoredTheme();
applyTheme(initialTheme);

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: initialTheme,

  setTheme: (theme) => {
    localStorage.setItem(STORAGE_KEY, theme);
    applyTheme(theme);
    set({ theme });
  },

  toggleTheme: () => {
    get().setTheme(get().theme === 'dark' ? 'light' : 'dark');
  },
}));
