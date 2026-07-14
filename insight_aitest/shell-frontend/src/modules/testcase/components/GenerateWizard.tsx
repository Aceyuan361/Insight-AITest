import { useEffect, useState } from 'react';
import { Sparkles, ArrowLeft, Play, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useCaseStore, type TestPoint } from '../store/caseStore';

type Step = 1 | 2 | 3;

export function GenerateWizard({ onDone }: { onDone?: () => void }) {
  const { t } = useTranslation();
  const { analyze, analyzeLoading, analyzePoints, createQuickTask, loadCases } = useCaseStore();
  const [step, setStep] = useState<Step>(1);
  const [docs, setDocs] = useState<{ id: number; filename: string }[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<number[]>([]);
  const [query, setQuery] = useState(t('testcase.defaultQuery'));
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [genProgress, setGenProgress] = useState<{ done: number; total: number } | null>(null);
  const [genStatus, setGenStatus] = useState<string>('');

  useEffect(() => {
    fetch(`/api/modules/kb/documents`).then((r) => r.json()).then(setDocs).catch(() => {});
  }, []);

  const doAnalyze = async () => {
    await analyze(query, selectedDocs.length ? selectedDocs : null);
    setStep(2);
  };

  const toggleDoc = (id: number) =>
    setSelectedDocs((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const togglePoint = (id: string) =>
    setSelected((s) => ({ ...s, [id]: !s[id] }));

  const selectedCount = Object.values(selected).filter(Boolean).length;

  const doGenerate = async () => {
    const pts = analyzePoints.filter((p) => selected[p.id]);
    setGenProgress({ done: 0, total: pts.length });
    setGenStatus(t('testcase.submittingTask'));
    try {
      // 统一走 AI /tasks/quick 创建预置任务，再 SSE 监听进度
      const { task_id } = await createQuickTask('analyze_generate', {
        test_points: pts.map(({ id: _id, summary, suggested_type, suggested_design, rationale }) => ({
          id: _id, summary, suggested_type, suggested_design, rationale,
        })),
        document_ids: selectedDocs.length ? selectedDocs : null,
      });

      setGenStatus(t('testcase.generating'));
      await streamQuickTask(task_id, async (data) => {
        // step 事件携带 current/total 进度
        if (typeof data.current === 'number' && typeof data.total === 'number') {
          setGenProgress({ done: data.current, total: data.total });
        }
      });
      setGenStatus(t('testcase.generateComplete'));
      await loadCases();
    } catch (e) {
      setGenStatus(t('testcase.generateFailed', { message: (e as Error).message }));
    }
    setStep(3);
  };

  return (
    <div style={{ padding: 24, overflow: 'auto', color: "var(--text-primary)", maxWidth: 720 }}>
      <StepHeader step={step} />

      {step === 1 && (
        <div>
          <h3 style={{ fontSize: 15, marginTop: 0 }}>{t('testcase.step1Title')}</h3>
          <div style={{ marginBottom: 12 }}>
            <div style={labelStyle}>{t('testcase.docScope')}</div>
            {docs.length === 0 && <div style={hintStyle}>{t('testcase.noDocsHint')}</div>}
            {docs.map((d) => (
              <label key={d.id} style={{ display: 'block', padding: '4px 0', fontSize: 13, color: 'var(--text-muted)' }}>
                <input type="checkbox" checked={selectedDocs.includes(d.id)}
                  onChange={() => toggleDoc(d.id)} style={{ marginRight: 8 }} />
                {d.filename}
              </label>
            ))}
          </div>
          <div style={{ marginBottom: 16 }}>
            <div style={labelStyle}>{t('testcase.analyzeTopic')}</div>
            <input style={{ ...inputStyle, width: '100%' }} value={query}
              onChange={(e) => setQuery(e.target.value)} />
          </div>
          <button onClick={doAnalyze} disabled={analyzeLoading || !query.trim()} style={{ ...primaryBtn, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            {analyzeLoading ? t('testcase.analyzing') : <><Sparkles size={13} strokeWidth={1.5} /> {t('testcase.analyzeTestPoints')}</>}
          </button>
        </div>
      )}

      {step === 2 && (
        <div>
          <h3 style={{ fontSize: 15, marginTop: 0 }}>
            {t('testcase.step2Title', { total: analyzePoints.length, selected: selectedCount })}
          </h3>
          {analyzePoints.length === 0 && (
            <div style={hintStyle}>{t('testcase.noPointsHint')}</div>
          )}
          {analyzePoints.map((p) => (
            <PointRow key={p.id} p={p} checked={!!selected[p.id]}
              onToggle={() => togglePoint(p.id)} />
          ))}
          <div style={{ marginTop: 16, display: 'flex', gap: 12 }}>
            <button onClick={() => setStep(1)} style={{ ...secondaryBtn, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <ArrowLeft size={13} strokeWidth={1.5} /> {t('testcase.back')}
            </button>
            <button onClick={doGenerate} disabled={selectedCount === 0} style={{ ...primaryBtn, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              {t('testcase.generateSelected', { count: selectedCount })} <Play size={13} strokeWidth={1.5} />
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div>
          <h3 style={{ fontSize: 15, marginTop: 0 }}>{t('testcase.step3Title')}</h3>
          {genProgress && (
            <div style={{ marginBottom: 8, fontSize: 14, color: "var(--success)", display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <Check size={14} strokeWidth={1.5} /> {t('testcase.generatedCount', { done: genProgress.done, total: genProgress.total })}
            </div>
          )}
          {genStatus && (
            <div style={{ marginBottom: 16, fontSize: 12, color: "var(--text-muted)" }}>{genStatus}</div>
          )}
          <button onClick={onDone} style={primaryBtn}>{t('testcase.viewCaseList')}</button>
        </div>
      )}
    </div>
  );
}

/**
 * 监听 AI 任务 SSE 流（GET /api/modules/ai/tasks/{id}/stream）。
 * 采用与 taskStore.streamTask 一致的 fetch + ReadableStream 解析方式
 * （EventSource 不支持自定义 header，这里无需 header 故可用，但为统一风格用 fetch 流）。
 * 收到 done/error/cancelled 事件后 resolve。
 */
async function streamQuickTask(taskId: number, onData: (data: Record<string, unknown>) => void): Promise<void> {
  const res = await fetch(`/api/modules/ai/tasks/${taskId}/stream`);
  if (!res.body) return;
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop()!;
    for (const evt of events) {
      const type = evt.match(/^event: (.+)$/m)?.[1];
      const dataStr = evt.match(/^data: (.+)$/m)?.[1] ?? '{}';
      let data: Record<string, unknown>;
      try { data = JSON.parse(dataStr); } catch { continue; }
      onData(data);
      if (type === 'done' || type === 'error' || type === 'cancelled') return;
    }
  }
}

function StepHeader({ step }: { step: Step }) {
  const { t } = useTranslation();
  const labels = [t('testcase.stepLabel1'), t('testcase.stepLabel2'), t('testcase.stepLabel3')];
  return (
    <div style={{ display: 'flex', gap: 8, marginBottom: 20, fontSize: 12 }}>
      {[1, 2, 3].map((n) => (
        <span key={n} style={{
          padding: '4px 10px', borderRadius: 4,
          background: step >= n ? 'rgba(91,140,123,0.12)' : "var(--bg-card)",
          border: step >= n ? '1px solid var(--accent)' : '1px solid var(--bg-elevated)',
          color: step >= n ? "var(--accent)" : 'var(--text-secondary)',
          display: 'inline-flex', alignItems: 'center', gap: 4,
        }}>
          {step > n ? <Check size={11} strokeWidth={1.5} /> : null}{labels[n - 1]}
        </span>
      ))}
    </div>
  );
}

function PointRow({ p, checked, onToggle }: {
  p: TestPoint; checked: boolean; onToggle: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div onClick={onToggle} style={{
      padding: 10, marginBottom: 8, borderRadius: 6, cursor: 'pointer',
      background: checked ? 'rgba(91,140,123,0.06)' : 'var(--bg-base)',
      border: checked ? '1px solid var(--accent)' : '1px solid var(--bg-card)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <input type="checkbox" checked={checked} onChange={onToggle} readOnly />
        <span style={{ color: "var(--text-primary)", fontSize: 14, flex: 1 }}>{p.summary}</span>
        <span style={tagStyle}>{p.suggested_type}</span>
        <span style={tagStyle}>{p.suggested_design}</span>
      </div>
      {p.rationale && <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>{t('testcase.rationaleLabel', { rationale: p.rationale })}</div>}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', borderRadius: 4,
  color: "var(--text-primary)", padding: '8px', fontFamily: 'inherit', fontSize: 13,
};
const labelStyle: React.CSSProperties = { fontSize: 12, color: "var(--text-secondary)", marginBottom: 6 };
const hintStyle: React.CSSProperties = { fontSize: 12, color: 'var(--text-muted)', padding: '8px 0' };
const tagStyle: React.CSSProperties = {
  fontSize: 10, color: 'var(--chart-2)', border: '1px solid var(--chart-2)',
  padding: '0 6px', borderRadius: 3,
};
const primaryBtn: React.CSSProperties = {
  background: "var(--accent)", color: "var(--bg-base)", border: 'none', borderRadius: 6,
  padding: '8px 20px', cursor: 'pointer', fontWeight: 600,
};
const secondaryBtn: React.CSSProperties = {
  background: 'none', border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)",
  borderRadius: 6, padding: '8px 16px', cursor: 'pointer',
};
