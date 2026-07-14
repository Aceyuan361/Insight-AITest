import type { CSSProperties } from 'react';
import type { Decision } from '../../store/taskStore';
import { RADIUS } from '../agentStyles';

/** ReAct Agent 决策徽章：按 continue/retry/fix/abort 着色。 */
const DECISION_STYLES: Record<Decision, { color: string; bg: string; border: string; label: string }> = {
  continue: { color: '#16a34a', bg: '#dcfce7', border: 'rgba(22,163,74,0.3)', label: 'CONTINUE' },
  retry: { color: '#ca8a04', bg: '#fef9c3', border: 'rgba(202,138,4,0.3)', label: 'RETRY' },
  fix: { color: '#ea580c', bg: '#ffedd5', border: 'rgba(234,88,12,0.3)', label: 'FIX' },
  abort: { color: '#dc2626', bg: '#fee2e2', border: 'rgba(220,38,38,0.3)', label: 'ABORT' },
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
