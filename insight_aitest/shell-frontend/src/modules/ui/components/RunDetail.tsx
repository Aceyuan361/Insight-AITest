import type { RunDetail as RunDetailType } from '../store/runStore';
import { Check, X, AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { UIStepResultCard } from './UIStepResultCard';

export function RunDetail({ run }: { run: RunDetailType | null }) {
  const { t } = useTranslation();
  if (!run) {
    return <div style={{ padding: 24, color: 'var(--text-muted)', fontSize: 13 }}>{t('ui.selectRunDetail')}</div>;
  }
  const color = run.status === 'passed' ? "var(--success)" : run.status === 'failed' ? "var(--error)" : 'var(--chart-3)';
  return (
    <div style={{ padding: 16, overflow: 'auto' }}>
      <div style={{ marginBottom: 12, fontSize: 13, color, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
        {run.status === 'passed'
          ? <><Check size={13} strokeWidth={1.5} /> {t('ui.pass')}</>
          : run.status === 'failed'
            ? <><X size={13} strokeWidth={1.5} /> {t('ui.fail')}</>
            : <><AlertTriangle size={13} strokeWidth={1.5} /> {t('ui.abnormal')}</>}
        {' · '}{t('ui.stepPassSummary', { passed: run.passed_steps, total: run.total_steps, duration: run.duration_ms })}
      </div>
      <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 12 }}>URL: {run.base_url_used}</div>
      {run.steps.map((s) => <UIStepResultCard key={s.step_index} step={s} runId={run.id} />)}
    </div>
  );
}
