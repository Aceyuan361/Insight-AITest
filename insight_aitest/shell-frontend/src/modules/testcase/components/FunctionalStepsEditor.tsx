import { ArrowUp, ArrowDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';

/** 功能用例步骤结构化编辑器（可增删改排序）。 */
export interface FunctionalStep {
  no: number;
  action: string;
  data: string;
}

export interface FunctionalContent {
  steps: FunctionalStep[];
  expected: string;
}

export function FunctionalStepsEditor({ content, onChange }: {
  content: FunctionalContent;
  onChange: (c: FunctionalContent) => void;
}) {
  const { t } = useTranslation();
  const steps = content.steps || [];
  const update = (patch: Partial<FunctionalContent>) => onChange({ ...content, ...patch });
  const updateStep = (i: number, patch: Partial<FunctionalStep>) =>
    update({ steps: steps.map((s, idx) => (idx === i ? { ...s, ...patch } : s)) });
  const addStep = () => update({
    steps: [...steps, { no: steps.length + 1, action: '', data: '' }] });
  const delStep = (i: number) => update({ steps: steps.filter((_, idx) => idx !== i) });
  const moveStep = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= steps.length) return;
    const arr = [...steps];
    [arr[i], arr[j]] = [arr[j], arr[i]];
    update({ steps: arr.map((s, idx) => ({ ...s, no: idx + 1 })) });
  };

  return (
    <div>
      <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 8 }}>{t('testcase.steps')}</div>
      {steps.map((s, i) => (
        <div key={i} style={{ display: 'flex', gap: 6, marginBottom: 6, alignItems: 'center' }}>
          <span style={{ color: "var(--accent)", width: 20, fontSize: 13 }}>{i + 1}</span>
          <input style={inputStyle} placeholder={t('testcase.actionPlaceholder')} value={s.action}
            onChange={(e) => updateStep(i, { action: e.target.value })} />
          <input style={{ ...inputStyle, width: 140 }} placeholder={t('testcase.testDataPlaceholder')} value={s.data}
            onChange={(e) => updateStep(i, { data: e.target.value })} />
          <button onClick={() => moveStep(i, -1)} style={{ ...miniBtn, display: 'inline-flex', alignItems: 'center' }}>
            <ArrowUp size={12} strokeWidth={1.5} />
          </button>
          <button onClick={() => moveStep(i, 1)} style={{ ...miniBtn, display: 'inline-flex', alignItems: 'center' }}>
            <ArrowDown size={12} strokeWidth={1.5} />
          </button>
          <button onClick={() => delStep(i)} style={{ ...miniBtn, color: "var(--error)" }}>×</button>
        </div>
      ))}
      <button onClick={addStep} style={{ ...miniBtn, border: '1px dashed var(--bg-elevated)', padding: '4px 10px' }}>
        + {t('testcase.addStep')}
      </button>
      <div style={{ fontSize: 12, color: "var(--text-secondary)", margin: '16px 0 8px' }}>{t('testcase.expected')}</div>
      <textarea style={{ ...inputStyle, width: '100%', minHeight: 60, resize: 'vertical' }}
        placeholder={t('testcase.expectedPlaceholder')} value={content.expected || ''}
        onChange={(e) => update({ expected: e.target.value })} />
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', borderRadius: 4,
  color: "var(--text-primary)", padding: '6px 8px', fontFamily: 'inherit', fontSize: 13, flex: 1,
};
const miniBtn: React.CSSProperties = {
  background: 'none', border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)",
  padding: '2px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 12,
};
