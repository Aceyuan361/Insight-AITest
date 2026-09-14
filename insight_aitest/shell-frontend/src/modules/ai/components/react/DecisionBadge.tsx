import type { CSSProperties } from 'react';
import type { Decision } from '../../store/taskStore';
import { RADIUS } from '../agentStyles';

/** ReAct Agent 决策徽章：按 continue/retry/fix/abort 着色（token 派生，双主题自适应）。 */
const DECISION_STYLES: Record<Decision, { color: string; bg: string; border: string; label: string }> = {
  continue: {
    color: 'var(--success)',
    bg: 'color-mix(in srgb, var(--success) 12%, transparent)',
    border: 'color-mix(in srgb, var(--success) 30%, transparent)',
    label: 'CONTINUE',
  },
  retry: {
    color: 'var(--warning)',
    bg: 'color-mix(in srgb, var(--warning) 12%, transparent)',
    border: 'color-mix(in srgb, var(--warning) 30%, transparent)',
    label: 'RETRY',
  },
  fix: {
    color: 'var(--risk)',
    bg: 'color-mix(in srgb, var(--risk) 12%, transparent)',
    border: 'color-mix(in srgb, var(--risk) 30%, transparent)',
    label: 'FIX',
  },
  abort: {
    color: 'var(--error)',
    bg: 'color-mix(in srgb, var(--error) 12%, transparent)',
    border: 'color-mix(in srgb, var(--error) 30%, transparent)',
    label: 'ABORT',
  },
};

export function DecisionBadge({ decision, confidence }: { decision: Decision; confidence?: number }) {
  const s = DECISION_STYLES[decision] ?? DECISION_STYLES.continue;
  const style: CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: '0.05em',
    color: s.color,
    background: s.bg,
    border: `1px solid ${s.border}`,
    padding: '2px 8px',
    borderRadius: RADIUS.sm,
    lineHeight: 1.4,
    whiteSpace: 'nowrap',
  };
  return (
    <span style={style}>
      {s.label}
      {typeof confidence === 'number' && Number.isFinite(confidence) && (
        <span style={{ opacity: 0.7, fontWeight: 600 }}>
          {(confidence * 100).toFixed(0)}%
        </span>
      )}
    </span>
  );
}
