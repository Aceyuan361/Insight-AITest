export const neonTheme = {
  colors: {
    // 背景色
    background: '#0a0a0a',
    cardBg: '#141414',

    // 文字色
    textPrimary: '#ffffff',
    textSecondary: '#aaaaaa',

    // 霓虹指标色（与桌面版完全一致）
    cpu: '#00f2ff',      // 青色
    memory: '#7000ff',   // 紫色
    fps: '#ffb400',      // 橙色
    networkUp: '#00ff87', // 绿色
    networkDown: '#0062ff', // 蓝色

    // 状态色
    success: '#22c55e',
    warning: '#f59e0b',
    error: '#ef4444',
  },

  fonts: {
    primary: '"Microsoft YaHei UI", "Segoe UI", Arial, sans-serif',
    mono: '"Consolas", "Monaco", monospace',
  },

  spacing: {
    cardPadding: 15,
    chartGridTop: 35,
    chartGridLeft: 55,
    chartGridRight: 20,
    chartGridBottom: 30,
  },

  sizes: {
    windowMinWidth: 1000,
    windowMinHeight: 600,
    cardMinHeight: 180,
  },
};
