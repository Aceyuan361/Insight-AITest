import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useIsMobile } from '../../../shared/hooks/useIsMobile';

export type StepKind = 'action' | 'assert' | 'extract';

export interface UIStepData {
  kind: StepKind;
  action?: string;    // kind=action 时用
  assert?: string;    // kind=assert 时用
  extract?: Record<string, string>;  // kind=extract 时用 {varName: 自然语言描述}
}

const kindLabelKey: Record<StepKind, string> = {
  action: 'ui.kindAction', assert: 'ui.kindAssert', extract: 'ui.kindExtract',
};

export function StepEditor({ step, onChange, onRemove }: {
  step: UIStepData; onChange: (s: UIStepData) => void; onRemove: () => void;
}) {
  const { t } = useTranslation();
  const setKind = (kind: StepKind) => {
    const next: UIStepData = { kind };
    if (kind === 'action') next.action = step.action || '';
    if (kind === 'assert') next.assert = step.assert || '';
    if (kind === 'extract') next.extract = step.extract || {};
    onChange(next);
  };

  return (
    <div style={{ background: 'var(--bg-card)', borderRadius: 4, padding: 10, marginBottom: 8 }}>
      <div style={{ display: 'flex', gap: 6, marginBottom: 8, alignItems: 'center' }}>
        <select value={step.kind} onChange={(e) => setKind(e.target.value as StepKind)} style={{
          background: "var(--bg-base)", color: "var(--text-primary)", border: '1px solid var(--border-strong)',
          borderRadius: 3, padding: '2px 6px', fontSize: 12,
        }}>
          {(Object.keys(kindLabelKey) as StepKind[]).map((k) => (
            <option key={k} value={k}>{t(kindLabelKey[k])}</option>
          ))}
        </select>
        <button onClick={onRemove} style={{
          marginLeft: 'auto', background: 'transparent', border: 'none',
          color: "var(--text-muted)", cursor: 'pointer', fontSize: 14,
          display: 'inline-flex', alignItems: 'center',
        }}><X size={14} strokeWidth={1.5} /></button>
      </div>
      {step.kind === 'action' && (
        <input value={step.action || ''} onChange={(e) => onChange({ ...step, action: e.target.value })}
          placeholder={t('ui.actionPlaceholder')}
          style={inputStyle} />
      )}
      {step.kind === 'assert' && (
        <input value={step.assert || ''} onChange={(e) => onChange({ ...step, assert: e.target.value })}
          placeholder={t('ui.assertPlaceholder')}
          style={inputStyle} />
      )}
      {step.kind === 'extract' && (
        <ExtractEditor extract={step.extract || {}} onChange={(ex) => onChange({ ...step, extract: ex })} />
      )}
    </div>
  );
}

function ExtractEditor({ extract, onChange }: {
  extract: Record<string, string>; onChange: (e: Record<string, string>) => void;
}) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const entries = Object.entries(extract);
  const setKey = (oldKey: string, newKey: string) => {
    const next = { ...extract };
    const v = next[oldKey]; delete next[oldKey]; next[newKey] = v;
    onChange(next);
  };
  const setVal = (key: string, val: string) => onChange({ ...extract, [key]: val });
  const add = () => onChange({ ...extract, [`var${entries.length + 1}`]: '' });
  const remove = (key: string) => {
    const next = { ...extract }; delete next[key]; onChange(next);
  };
  return (
    <div>
      {entries.map(([k, v]) => (
        <div key={k} style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', gap: 6, marginBottom: 6 }}>
          <input value={k} onChange={(e) => setKey(k, e.target.value)} placeholder={t('ui.varName')} style={{ ...inputStyle, width: isMobile ? '100%' : 100 }} />
          <input value={v} onChange={(e) => setVal(k, e.target.value)} placeholder={t('ui.extractPlaceholder')} style={inputStyle} />
          <button onClick={() => remove(k)} style={{ background: 'transparent', border: 'none', color: "var(--text-muted)", cursor: 'pointer', display: 'inline-flex', alignItems: 'center' }}>
            <X size={12} strokeWidth={1.5} />
          </button>
        </div>
      ))}
      <button onClick={add} style={addBtnStyle}>{t('ui.addVariable')}</button>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%', background: "var(--bg-base)", color: "var(--text-primary)", border: '1px solid var(--bg-elevated)',
  borderRadius: 3, padding: '6px 8px', fontSize: 12,
};
const addBtnStyle: React.CSSProperties = {
  background: 'transparent', border: '1px dashed var(--border-strong)', color: "var(--text-muted)",
  padding: '4px 10px', borderRadius: 3, fontSize: 11, cursor: 'pointer',
};
