import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronRight } from 'lucide-react';
import type { TraceEntry } from '../../store/taskStore';
import { glassPanelStrong, text, RADIUS, SPRING } from '../agentStyles';
import { IterationCard } from './IterationCard';
import { DecisionBadge } from './DecisionBadge';

/** 单个 step 的 ReAct trace：可折叠，头部展示末次迭代摘要 + 决策徽章。 */
export function StepTrace({ stepIndex, entries }: { stepIndex: number; entries: TraceEntry[] }) {
  const [open, setOpen] = useState(false);
  const sorted = [...entries].sort((a, b) => a.iteration - b.iteration);
  const last = sorted[sorted.length - 1];
  const { t } = useTranslation();

  if (!last) return null;

  return (
    <div
      style={{
        ...glassPanelStrong,
        borderRadius: RADIUS.md,
        overflow: 'hidden',
        marginBottom: 8,
      }}
    >
      {/* 折叠头部 */}
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '10px 14px',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          color: text.primary,
          textAlign: 'left',
          transition: `background 0.15s ${SPRING}`,
        }}
      >
        <ChevronRight
          size={14}
          strokeWidth={2}
          style={{
            flexShrink: 0,
            transition: `transform 0.2s ${SPRING}`,
            transform: open ? 'rotate(90deg)' : 'none',
            color: text.muted,
          }}
        />
        <span style={{ fontSize: 11, color: text.muted, fontWeight: 600, letterSpacing: '0.04em', flexShrink: 0 }}>
          STEP {stepIndex}
        </span>
        <span
          style={{
            fontSize: 13,
            color: text.primary,
            flex: 1,
            minWidth: 0,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {last.action?.desc || last.action?.skill || t('ai.iterationFallback', { n: last.iteration })}
        </span>
        <span style={{ fontSize: 10, color: text.muted, flexShrink: 0 }}>
          {t('ai.iterationCount', { count: sorted.length })}
        </span>
        <DecisionBadge decision={last.decision} confidence={last.reflection?.confidence} />
      </button>

      {/* 展开内容：迭代卡片列表 */}
      {open && (
        <div
          style={{
            padding: '4px 14px 14px',
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
            borderTop: '1px solid var(--border)',
          }}
        >
          {sorted.map((e, i) => (
            <IterationCard key={`${e.iteration}-${i}`} entry={e} />
          ))}
        </div>
      )}
    </div>
  );
}
