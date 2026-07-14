/**
 * Agent 组件共享样式（Stage 2 token 化重定向版）。
 *
 * 历史：原本是 Apple Liquid Glass 磨玻璃 + 第 4 套独立色板（cyan #00e5ff / #f0f0f5…）。
 * 现状：色彩统一重定向到 tokens.css 的 CSS variables（emerald 高饱和 + 深底强对比）。
 *   - Stage 4 已去玻璃（backdrop-filter），改实色 token 化底材。
 *   - text 对象保留（65 处调用），但 7 个色值全部 var(--*)，不再硬编码。
 *
 * 单一真相源：@/shared/theme/tokens.css
 */

/** 面板：卡片、消息气泡、输入栏的通用底材（Stage 4 去玻璃，实色 token 化） */
export const glassPanel: React.CSSProperties = {
  background: "var(--bg-card)",
  border: "1px solid var(--border)",
  boxShadow: "var(--shadow-card)",
};

/** 强调面板：策略卡、结果卡等需要更多层级感的面板 */
export const glassPanelStrong: React.CSSProperties = {
  ...glassPanel,
  background: "var(--bg-elevated)",
  border: "1px solid var(--border-strong)",
  boxShadow: "var(--shadow-elevated)",
};

/** 浮动输入栏 */
export const glassInputBar: React.CSSProperties = {
  background: "var(--bg-elevated)",
  border: "1px solid var(--border-strong)",
  boxShadow: "var(--shadow-elevated)",
  borderRadius: 16,
};

/** 输入框内嵌 */
export const glassTextarea: React.CSSProperties = {
  background: "transparent",
  border: "none",
  color: "var(--text-primary)",
  padding: "8px 12px",
  fontFamily: "inherit",
  fontSize: 14,
  resize: "none",
  outline: "none",
  width: "100%",
  minHeight: 36,
  maxHeight: 120,
};

/** 主按钮（emerald 填充 + 玻璃高光） */
export const primaryButton: React.CSSProperties = {
  background: "linear-gradient(180deg, var(--accent-hover), var(--accent))",
  color: "var(--bg-base)",
  border: "none",
  borderRadius: 10,
  padding: "8px 20px",
  cursor: "pointer",
  fontSize: 13,
  fontWeight: 600,
  boxShadow:
    "0 2px 8px color-mix(in srgb, var(--accent) 30%, transparent), inset 0 1px 0 rgba(255,255,255,0.25)",
  transition: "all 0.2s cubic-bezier(0.16,1,0.3,1)",
};

/** 次级按钮（描边） */
export const ghostButton: React.CSSProperties = {
  background: "transparent",
  border: "1px solid var(--border-strong)",
  color: "var(--text-secondary)",
  borderRadius: 10,
  padding: "8px 16px",
  cursor: "pointer",
  fontSize: 13,
  transition: "all 0.2s cubic-bezier(0.16,1,0.3,1)",
};

/** 统一圆角体系 */
export const RADIUS = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  pill: 999,
};

/** 统一缓动 */
export const SPRING = "cubic-bezier(0.16,1,0.3,1)";

/**
 * 文字层级 —— 保留对象结构（65 处调用），色值重定向到 tokens.css。
 * 取代原 var(--text-primary)/#a8a8b8/var(--text-muted)/var(--accent)/var(--success)/var(--error) 硬编码。
 */
export const text = {
  primary: "var(--text-primary)",
  secondary: "var(--text-secondary)",
  muted: "var(--text-muted)",
  accent: "var(--accent)",
  success: "var(--success)",
  danger: "var(--error)",
};
