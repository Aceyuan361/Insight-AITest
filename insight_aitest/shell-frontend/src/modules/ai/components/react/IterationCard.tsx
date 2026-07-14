import { useTranslation } from 'react-i18next';
import type { TraceEntry } from '../../store/taskStore';
import { glassPanel, text, RADIUS, SPRING } from '../agentStyles';
import { DecisionBadge } from './DecisionBadge';

/** 单次 ReAct 循环卡片：action / observation / reflection / decision。 */
export function IterationCard({ entry }: { entry: TraceEntry }) {
  const obsStr = truncateJson(entry.observation);
  const paramsStr = entry.action.params && Object.keys(entry.action.params).length > 0
    ? truncateJson(entry.action.params)
    : null;
  const reflection = entry.reflection;
  const { t } = useTranslation();

  return (
    <div
      style={{
        ...glassPanel,
        padding: 12,
        borderRadius: RADIUS.md,
        background: 'var(--bg-card)',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      {/* 迭代号 + 决策徽章 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <span style={{ fontSize: 10, color: text.muted, fontWeight: 600, letterSpacing: '0.04em' }}>
          {t('ai.iterationN', { n: entry.iteration })}
        </span>
        <DecisionBadge
          decision={entry.decision}
          confidence={reflection?.confidence}
        />
      </div>

      {/* Action */}
      <Field label="Action">
        <span style={{ fontSize: 13, color: text.primary, fontWeight: 500 }}>
          {entry.action.skill}
        </span>
        {entry.action.desc && (
          <span style={{ fontSize: 12, color: text.secondary, marginLeft: 6 }}>
            {entry.action.desc}
          </span>
        )}
        {paramsStr && (
          <pre style={preStyle}>{paramsStr}</pre>
        )}
      </Field>

      {/* Observation */}
      <Field label="Observation">
        <pre style={preStyle}>{obsStr}</pre>
      </Field>

      {/* Reflection */}
      {reflection && (
        <Field label="Reflection">
          {reflection.thought && (
            <div style={{ fontSize: 12, color: text.primary, lineHeight: 1.5, marginBottom: 4 }}>
              {reflection.thought}
            </div>
          )}
          {reflection.reasoning && (
            <div style={{ fontSize: 11, color: text.muted, lineHeight: 1.5 }}>
              {reflection.reasoning}
            </div>
          )}
        </Field>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <div style={{ fontSize: 10, color: text.accent, fontWeight: 600, letterSpacing: '0.04em' }}>
        {label}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>{children}</div>
    </div>
  );
}

const preStyle: React.CSSProperties = {
  margin: 0,
  padding: '6px 8px',
  background: 'var(--bg-base)',
  border: '1px solid var(--hairline-soft)',
  borderRadius: RADIUS.sm,
  fontSize: 11,
  lineHeight: 1.5,
  color: text.secondary,
  fontFamily: 'var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace)',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
  maxHeight: 120,
  overflow: 'auto',
  transition: `border-color 0.15s ${SPRING}`,
};

function truncateJson(obj: unknown, max = 400): string {
  let str: string;
  try {
    str = JSON.stringify(obj, null, 2) ?? String(obj);
  } catch {
    str = String(obj);
  }
  return str.length > max ? str.slice(0, max) + '\n…' : str;
}
