import { useState } from 'react';
import { Check, X, AlertTriangle, Image } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { UIStepResult } from '../store/runStore';

const API_BASE = '/api/modules/ui';

export function UIStepResultCard({ step, runId }: { step: UIStepResult; runId: number }) {
  const [showShot, setShowShot] = useState(false);
  const { t } = useTranslation();
  const kindColor = step.kind === 'assert' ? 'var(--chart-2)' : step.kind === 'extract' ? "var(--success)" : "var(--info)";
  const statusColor = step.error ? 'var(--chart-3)' : step.passed ? "var(--success)" : "var(--error)";
  return (
    <div style={{
      background: 'var(--bg-card)', borderRadius: 4, padding: 12, marginBottom: 8,
      borderLeft: `3px solid ${statusColor}`,
    }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 6, alignItems: 'center' }}>
        <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>#{step.step_index + 1}</span>
        <span style={{
          color: kindColor, fontSize: 11, background: 'var(--surface-hover)',
          padding: '1px 6px', borderRadius: 3,
        }}>{step.kind}</span>
        <span style={{ color: statusColor, fontSize: 11, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          {step.error
            ? <><AlertTriangle size={12} strokeWidth={1.5} /> error</>
            : step.passed
              ? <Check size={12} strokeWidth={1.5} />
              : <X size={12} strokeWidth={1.5} />}
        </span>
        <span style={{ color: 'var(--text-muted)', fontSize: 11, marginLeft: 'auto' }}>{step.elapsed_ms}ms</span>
      </div>
      <div style={{ color: "var(--text-secondary)", fontSize: 12, marginBottom: 4 }}>{step.prompt}</div>
      {step.action_log && <div style={{ color: "var(--text-muted)", fontSize: 11 }}>log: {step.action_log}</div>}
      {step.assert_passed !== null && (
        <div style={{ color: step.assert_passed ? "var(--success)" : "var(--error)", fontSize: 11 }}>
          {t('ui.assertResult', { result: step.assert_passed ? t('ui.pass') : t('ui.fail') })}
        </div>
      )}
      {step.error && <div style={{ color: 'var(--chart-3)', fontSize: 11, marginTop: 4 }}>{step.error}</div>}
      {step.screenshot && (
        <div style={{ marginTop: 6 }}>
          <button onClick={() => setShowShot(!showShot)} style={{
            background: 'transparent', border: '1px solid var(--border-strong)', color: "var(--text-secondary)",
            padding: '2px 8px', borderRadius: 3, fontSize: 11, cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', gap: 4,
          }}>{showShot ? t('ui.hideScreenshot') : <><Image size={11} strokeWidth={1.5} /> {t('ui.viewScreenshot')}</>}</button>
          {showShot && (
            <img src={`${API_BASE}/runs/${runId}/screenshot/${step.step_index}`}
              style={{ maxWidth: '100%', marginTop: 6, borderRadius: 4, border: '1px solid var(--bg-elevated)' }} />
          )}
        </div>
      )}
    </div>
  );
}
