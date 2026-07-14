import { useState } from 'react';
import { Check, X, AlertTriangle, ArrowLeft, ChevronDown, ChevronUp } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { StepResult } from '../store/runStore';

export function StepResultCard({ step }: { step: StepResult }) {
  const [showReq, setShowReq] = useState(false);
  const [showResp, setShowResp] = useState(false);
  const { t } = useTranslation();
  const ok = step.passed;
  const statusColor = step.error ? 'var(--chart-3)' : ok ? "var(--success)" : "var(--error)";

  return (
    <div style={{ marginBottom: 10, borderRadius: 6, border: `1px solid ${statusColor}33`,
      background: 'var(--bg-base)', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
        borderBottom: '1px solid var(--bg-card)' }}>
        <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>Step {step.step_index + 1}</span>
        <span style={{ color: "var(--text-primary)", fontSize: 13, flex: 1, fontFamily: 'monospace' }}>
          {step.request.method} {step.request.url}
        </span>
        <span style={{ color: statusColor, fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          {step.error
            ? <><AlertTriangle size={12} strokeWidth={1.5} /> {t('api.abnormal')}</>
            : ok
              ? <Check size={12} strokeWidth={1.5} />
              : <X size={12} strokeWidth={1.5} />} {step.status_code ?? '—'} {step.elapsed_ms}ms
        </span>
      </div>

      {step.error && (
        <div style={{ padding: '8px 12px', color: 'var(--chart-3)', fontSize: 12 }}>
          {step.error}
        </div>
      )}

      {step.assertions.length > 0 && (
        <div style={{ padding: '6px 12px', fontSize: 12 }}>
          <div style={{ color: "var(--text-muted)", marginBottom: 4 }}>{t('api.assertionLabel')}</div>
          {step.assertions.map((a, i) => (
            <div key={i} style={{ color: a.passed ? 'var(--chart-4)' : "var(--error)", lineHeight: 1.6, display: 'flex', alignItems: 'center', gap: 4 }}>
              {a.passed ? <Check size={12} strokeWidth={1.5} /> : <X size={12} strokeWidth={1.5} />} <span>{a.target} == {String(a.expected)}</span>
              {!a.passed && <span style={{ color: "var(--text-secondary)" }}>{t('api.actual', { actual: String(a.actual) })}</span>}
            </div>
          ))}
        </div>
      )}

      {Object.keys(step.extracts).length > 0 && (
        <div style={{ padding: '6px 12px', fontSize: 12 }}>
          <div style={{ color: "var(--text-muted)", marginBottom: 4 }}>{t('api.extract')}</div>
          {Object.entries(step.extracts).map(([k, v]) => (
            <div key={k} style={{ color: 'var(--chart-2)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span>{k}</span> <ArrowLeft size={11} strokeWidth={1.5} /> <span>{String(v)}</span>
            </div>
          ))}
        </div>
      )}

      <div style={{ padding: '4px 12px 8px' }}>
        <button onClick={() => setShowReq(!showReq)} style={{ ...toggleBtn, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          {t('api.request')} {showReq ? <ChevronUp size={11} strokeWidth={1.5} /> : <ChevronDown size={11} strokeWidth={1.5} />}
        </button>
        <button onClick={() => setShowResp(!showResp)} style={{ ...toggleBtn, marginLeft: 8, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          {t('api.response')} {showResp ? <ChevronUp size={11} strokeWidth={1.5} /> : <ChevronDown size={11} strokeWidth={1.5} />}
        </button>
        {showReq && (
          <pre style={preStyle}>{JSON.stringify({ headers: step.request.headers, body: step.request.body }, null, 2)}</pre>
        )}
        {showResp && (
          <pre style={preStyle}>{typeof step.response_body === 'string'
            ? step.response_body : JSON.stringify(step.response_body, null, 2)}</pre>
        )}
      </div>
    </div>
  );
}

const toggleBtn: React.CSSProperties = {
  background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)",
  padding: '2px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 11,
};
const preStyle: React.CSSProperties = {
  background: 'var(--bg-base)',
  padding: 8,
  borderRadius: 4,
  fontSize: 11,
  color: 'var(--text-secondary)',
  overflow: 'auto',
  maxWidth: '100%',
  maxHeight: 240,
  marginTop: 6,
};
