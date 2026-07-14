import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTaskStore } from '../store/taskStore';
import { glassPanelStrong, primaryButton, text, SPRING, RADIUS } from './agentStyles';

export function StrategyCard() {
  const { currentTask, selectStrategy, phase } = useTaskStore();
  const loading = phase === 'executing';
  const [selected, setSelected] = useState<string | null>(null);
  const { t } = useTranslation();
  if (!currentTask || !currentTask.strategies?.length) return null;

  const confirm = () => {
    if (!selected) return;
    selectStrategy(selected);
  };

  return (
    <div
      style={{
        ...glassPanelStrong,
        padding: 16,
        borderRadius: RADIUS.lg,
        borderLeft: '3px solid rgba(91,140,123,0.5)',
      }}
    >
      <div style={{ fontSize: 11, color: text.accent, fontWeight: 600, marginBottom: 6, letterSpacing: '0.04em' }}>
        {t('ai.selectStrategy')}
      </div>
      <p style={{ fontSize: 12, color: text.muted, marginBottom: 14 }}>
        {t('ai.strategyHint')}
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {currentTask.strategies.map((s) => {
          const checked = selected === s.id;
          return (
            <label
              key={s.id}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: 12, padding: 12,
                borderRadius: RADIUS.md,
                border: checked
                  ? '1px solid rgba(91,140,123,0.4)'
                  : '1px solid var(--hairline-soft)',
                background: 'var(--bg-elevated)',
                cursor: 'pointer',
                transition: `all 0.2s ${SPRING}`,
              }}
              onMouseEnter={(e) => { if (!checked) e.currentTarget.style.borderColor = 'var(--border-strong)'; }}
              onMouseLeave={(e) => { if (!checked) e.currentTarget.style.borderColor = 'var(--hairline-soft)'; }}
            >
              <input
                type="radio"
                name={`strategy-${currentTask?.id ?? '0'}`}
                checked={checked}
                onChange={() => setSelected(s.id)}
                style={{ marginTop: 3, accentColor: "var(--accent)" }}
              />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, color: text.primary, fontWeight: 600 }}>
                  {s.id}. {s.label}
                </div>
                <div style={{ fontSize: 12, color: text.secondary, marginTop: 4, lineHeight: 1.5 }}>
                  {s.description}
                </div>
                <div style={{ fontSize: 11, color: text.muted, marginTop: 6 }}>
                  {t('ai.strategyStepCount', { count: s.plan.length })}：{s.plan.map((p) => p.desc).join(' → ')}
                </div>
              </div>
            </label>
          );
        })}
      </div>
      <div style={{ marginTop: 14 }}>
        <button
          onClick={confirm}
          disabled={!selected || loading}
          style={{
            ...primaryButton,
            opacity: !selected || loading ? 0.4 : 1,
            transition: `all 0.15s ${SPRING}`,
          }}
          onMouseDown={(e) => { if (selected && !loading) e.currentTarget.style.transform = 'scale(0.97)'; }}
          onMouseUp={(e) => { e.currentTarget.style.transform = 'scale(1)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)'; }}
        >
          {loading ? t('ai.starting') : t('ai.confirmExec')}
        </button>
      </div>
    </div>
  );
}
