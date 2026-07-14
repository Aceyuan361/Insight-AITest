import type { RunDetail as RunDetailType } from '../store/runStore';
import { Check, X, AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { StepResultCard } from './StepResultCard';
import { exportRunHtmlReport } from '../report/runReportHtml';

export function RunDetail({ run }: { run: RunDetailType | null }) {
  const { t } = useTranslation();
  if (!run) {
    return <div style={{ padding: 24, color: 'var(--text-muted)', fontSize: 13 }}>{t('api.selectRunHint')}</div>;
  }
  const color = run.status === 'passed' ? "var(--success)" : run.status === 'failed' ? "var(--error)" : 'var(--chart-3)';
  return (
    <div style={{ padding: 16, overflow: 'auto' }}>
      <div style={{ marginBottom: 12, fontSize: 13, color, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          {run.status === 'passed'
            ? <><Check size={13} strokeWidth={1.5} /> {t('api.passed')}</>
            : run.status === 'failed'
              ? <><X size={13} strokeWidth={1.5} /> {t('api.failed')}</>
              : <><AlertTriangle size={13} strokeWidth={1.5} /> {t('api.abnormal')}</>}
          {' · '}{t('api.stepsPassed', { passed: run.passed_steps, total: run.total_steps })} · {run.duration_ms}ms
        </span>
        <button
          onClick={() => exportRunHtmlReport(run)}
          style={{ fontSize: 12, padding: '4px 10px', background: "var(--bg-card)", color: "var(--accent)", border: '1px solid color-mix(in srgb, var(--accent) 30%, transparent)', borderRadius: 4, cursor: 'pointer' }}
        >
          {t('api.exportReport')}
        </button>
      </div>
      {run.steps.map((s) => <StepResultCard key={s.step_index} step={s} />)}
    </div>
  );
}
