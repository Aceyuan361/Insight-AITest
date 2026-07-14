import { useState } from 'react';
import { Check, X, Save, ChevronUp, ChevronDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { StepEditor, type UIStepData } from './StepEditor';

const TC_BASE = '/api/modules/testcase/testcases';

export function CaseEditor({ caseId, initial }: {
  caseId: number;
  initial: { base_url?: string; steps: UIStepData[] };
}) {
  const [baseUrl, setBaseUrl] = useState(initial.base_url || '');
  const [steps, setSteps] = useState<UIStepData[]>(initial.steps || []);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');
  const [msgOk, setMsgOk] = useState(false);
  const { t } = useTranslation();

  const set = (i: number, s: UIStepData) => setSteps(steps.map((x, idx) => idx === i ? s : x));
  const add = () => setSteps([...steps, { kind: 'action', action: '' }]);
  const remove = (i: number) => setSteps(steps.filter((_, idx) => idx !== i));
  const move = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= steps.length) return;
    const next = [...steps]; [next[i], next[j]] = [next[j], next[i]];
    setSteps(next);
  };

  const save = async () => {
    setSaving(true); setMsg('');
    try {
      const r = await fetch(`${TC_BASE}/${caseId}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: { base_url: baseUrl, steps } }),
      });
      if (!r.ok) throw new Error(await r.text());
      setMsgOk(true);
      setMsg(t('ui.saved'));
    } catch (e) {
      setMsgOk(false);
      setMsg((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ padding: 16, overflow: 'auto' }}>
      <div style={{ marginBottom: 12 }}>
        <label style={{ color: "var(--text-secondary)", fontSize: 12, display: 'block', marginBottom: 4 }}>base_url</label>
        <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)}
          placeholder="http://localhost:80"
          style={{ width: '100%', background: "var(--bg-base)", color: "var(--text-primary)", border: '1px solid var(--bg-elevated)', borderRadius: 3, padding: '6px 8px', fontSize: 12 }} />
      </div>
      <div style={{ color: "var(--text-secondary)", fontSize: 12, marginBottom: 8 }}>{t('ui.stepsNaturalLang')}</div>
      {steps.map((s, i) => (
        <div key={i} style={{ position: 'relative', paddingLeft: 24 }}>
          <div style={{ position: 'absolute', left: 0, top: 10, display: 'flex', flexDirection: 'column' }}>
            <button onClick={() => move(i, -1)} disabled={i === 0} style={{ ...moveBtn, display: 'inline-flex', alignItems: 'center' }}>
              <ChevronUp size={10} strokeWidth={1.5} />
            </button>
            <button onClick={() => move(i, 1)} disabled={i === steps.length - 1} style={{ ...moveBtn, display: 'inline-flex', alignItems: 'center' }}>
              <ChevronDown size={10} strokeWidth={1.5} />
            </button>
          </div>
          <StepEditor step={s} onChange={(ns) => set(i, ns)} onRemove={() => remove(i)} />
        </div>
      ))}
      <button onClick={add} style={{
        background: 'transparent', border: '1px dashed var(--border-strong)', color: "var(--text-secondary)",
        padding: '6px 12px', borderRadius: 3, fontSize: 12, cursor: 'pointer',
      }}>{t('ui.addStep')}</button>
      <div style={{ marginTop: 16, display: 'flex', gap: 12, alignItems: 'center' }}>
        <button onClick={save} disabled={saving} style={{
          background: "var(--accent)", color: "var(--bg-base)", border: 'none', borderRadius: 4,
          padding: '6px 16px', cursor: saving ? 'wait' : 'pointer', fontSize: 12, fontWeight: 600,
          display: 'inline-flex', alignItems: 'center', gap: 4,
        }}>{saving ? t('ui.saving') : <><Save size={12} strokeWidth={1.5} /> {t('ui.save')}</>}</button>
        {msg && (
          <span style={{ color: msgOk ? "var(--success)" : "var(--error)", fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            {msgOk ? <Check size={12} strokeWidth={1.5} /> : <X size={12} strokeWidth={1.5} />} {msg}
          </span>
        )}
      </div>
    </div>
  );
}

const moveBtn: React.CSSProperties = {
  background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer',
  fontSize: 10, padding: '1px 3px', lineHeight: 1,
};
