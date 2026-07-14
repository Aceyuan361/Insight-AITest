import { useEffect, useState } from 'react';
import { Play, RefreshCw, Check, X, AlertTriangle, Loader } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useBatchStore } from '../store/batchStore';

export function BatchExec() {
  const { cases, loadingCases, runs, selectedRun, executing,
          loadCases, execute, loadRuns, loadDetail } = useBatchStore();
  const { t } = useTranslation();
  const [selected, setSelected] = useState<number[]>([]);
  const [baseUrl, setBaseUrl] = useState('');

  useEffect(() => {
    loadCases();
    loadRuns();
  }, [loadCases, loadRuns]);

  const toggle = (id: number) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const doExecute = async () => {
    if (selected.length === 0) return;
    await execute(selected, baseUrl || undefined);
    setSelected([]);
  };

  const statusColor = (s: string) =>
    s === 'passed' ? 'var(--success)' : s === 'failed' ? 'var(--error)' : s === 'error' ? 'var(--chart-3)' : 'var(--chart-4)';

  return (
    <div style={{ height: '100%', display: 'flex' }}>
      {/* 左：用例选择 */}
      <div style={{ width: 300, borderRight: '1px solid var(--bg-card)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--bg-card)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{t('ui.casesSelectedCount', { count: selected.length })}</span>
          {loadingCases && <Loader size={12} className="animate-spin" style={{ color: 'var(--text-muted)' }} />}
        </div>
        <div style={{ flex: 1, overflow: 'auto' }}>
          {cases.map((c) => (
            <label key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 16px', fontSize: 12, color: "var(--text-secondary)", cursor: 'pointer' }}>
              <input type="checkbox" checked={selected.includes(c.id)} onChange={() => toggle(c.id)} />
              {c.title}
            </label>
          ))}
          {cases.length === 0 && <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: 11 }}>{t('ui.noBatchCases')}</div>}
        </div>
        <div style={{ padding: '8px 16px', borderTop: '1px solid var(--bg-card)', display: 'flex', flexDirection: 'column', gap: 6 }}>
          <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder={t('ui.sharedBaseUrlPlaceholder')}
            style={inputStyle} />
          <button onClick={doExecute} disabled={executing || selected.length === 0} style={{
            ...primaryBtn, opacity: executing || selected.length === 0 ? 0.5 : 1,
            cursor: executing || selected.length === 0 ? 'not-allowed' : 'pointer',
          }}>
            {executing ? t('ui.submitting') : <><Play size={12} strokeWidth={1.5} /> {t('ui.batchExecCount', { count: selected.length })}</>}
          </button>
        </div>
      </div>

      {/* 中：执行历史 */}
      <div style={{ width: 340, borderRight: '1px solid var(--bg-card)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--bg-card)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{t('ui.batchHistory')}</span>
          <button onClick={() => loadRuns()} style={iconBtn}><RefreshCw size={11} strokeWidth={1.5} /></button>
        </div>
        <div style={{ flex: 1, overflow: 'auto' }}>
          {runs.map((r) => (
            <div key={r.id} onClick={() => loadDetail(r.id)} style={{
              padding: '8px 16px', borderBottom: '1px solid var(--bg-card)', cursor: 'pointer',
              background: selectedRun?.id === r.id ? 'var(--surface-tint)' : undefined,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: "var(--text-primary)" }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: statusColor(r.status), flexShrink: 0 }} />
                {r.name}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                {t('ui.passedOfTotal', { passed: r.passed, total: r.total })}
                {r.failed > 0 && ` · ${t('ui.failedCount', { count: r.failed })}`}
                {r.error > 0 && ` · ${t('ui.errorCount', { count: r.error })}`}
                {r.status === 'running' && ` · ${t('ui.executing')}`}
              </div>
            </div>
          ))}
          {runs.length === 0 && <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: 11 }}>{t('ui.noBatchHistory')}</div>}
        </div>
      </div>

      {/* 右：详情 */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--bg-card)', fontSize: 13, color: "var(--text-secondary)" }}>{t('ui.batchDetail')}</div>
        <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
          {!selectedRun ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{t('ui.selectBatchRecord')}</div>
          ) : (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <span style={{ fontSize: 14, color: "var(--text-primary)", fontWeight: 600 }}>{selectedRun.name}</span>
                <span style={{ fontSize: 11, color: statusColor(selectedRun.status), display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                  {selectedRun.status === 'passed' ? <Check size={11} /> : selectedRun.status === 'running' ? <Loader size={11} className="animate-spin" /> : selectedRun.status === 'error' ? <AlertTriangle size={11} /> : <X size={11} />}
                  {selectedRun.status}
                </span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12 }}>
                {t('ui.batchSummaryLine', { passed: selectedRun.passed, total: selectedRun.total, failed: selectedRun.failed, error: selectedRun.error })}
                {selectedRun.config?.base_url && ` · URL: ${selectedRun.config.base_url}`}
              </div>
              {selectedRun.child_runs?.map((cr) => (
                <div key={cr.id} style={{
                  background: 'var(--bg-card)', borderRadius: 4, padding: 10, marginBottom: 6,
                  borderLeft: `3px solid ${statusColor(cr.status)}`,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                    <span style={{ color: statusColor(cr.status), fontSize: 11 }}>
                      {cr.status === 'passed' ? <Check size={12} /> : cr.status === 'error' ? <AlertTriangle size={12} /> : <X size={12} />}
                    </span>
                    <span style={{ color: "var(--text-primary)", fontSize: 12 }}>{cr.case_title}</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: 11, marginLeft: 'auto' }}>{t('ui.batchStepSummary', { passed: cr.passed_steps, total: cr.total_steps, duration: cr.duration_ms })}</span>
                  </div>
                </div>
              ))}
              {selectedRun.status === 'running' && (
                <div style={{ fontSize: 11, color: 'var(--chart-4)', marginTop: 8, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                  <RefreshCw size={11} className="animate-spin" /> {t('ui.refreshing')}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%', background: "var(--bg-base)", color: "var(--text-primary)", border: '1px solid var(--bg-elevated)',
  borderRadius: 3, padding: '4px 8px', fontSize: 12,
};
const primaryBtn: React.CSSProperties = {
  background: "var(--accent)", color: "var(--bg-base)", border: 'none', borderRadius: 4,
  padding: '6px 12px', fontSize: 12, fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 4,
};
const iconBtn: React.CSSProperties = {
  background: 'transparent', border: 'none', color: "var(--text-muted)", cursor: 'pointer',
  display: 'inline-flex', alignItems: 'center', padding: 2,
};
