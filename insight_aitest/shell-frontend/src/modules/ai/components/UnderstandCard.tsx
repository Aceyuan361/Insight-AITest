import { useTranslation } from 'react-i18next';
import { useTaskStore } from '../store/taskStore';
import { glassPanel, text, RADIUS } from './agentStyles';

export function UnderstandCard({ summary }: { summary: string }) {
  const { currentTask } = useTaskStore();
  const scope = currentTask?.context?.scope || [];
  const { t } = useTranslation();

  return (
    <div
      style={{
        ...glassPanel,
        padding: 16,
        borderRadius: RADIUS.lg,
        borderLeft: '3px solid rgba(52,211,153,0.5)',
      }}
    >
      <div style={{ fontSize: 11, color: text.success, fontWeight: 600, marginBottom: 10, letterSpacing: '0.04em' }}>
        {t('ai.requirementUnderstanding')}
      </div>
      <div style={{ fontSize: 14, color: text.primary, lineHeight: 1.7 }}>
        {summary}
      </div>
      {scope.length > 0 && (
        <div style={{ marginTop: 12, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {scope.map((s, i) => (
            <span
              key={i}
              style={{
                fontSize: 11,
                color: text.secondary,
                background: 'var(--bg-elevated)',
                border: '1px solid var(--hairline-soft)',
                padding: '3px 10px',
                borderRadius: RADIUS.sm,
              }}
            >
              {s}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
