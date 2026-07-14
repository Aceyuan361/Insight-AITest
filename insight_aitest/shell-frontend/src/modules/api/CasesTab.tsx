import { useEffect, useState } from 'react';
import { Play, ArrowLeft } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useRunStore } from './store/runStore';
import { useProjectStore } from '../../shared/store/projectStore';
import { CasePicker } from '../../shared/components/CasePicker';
import { RunList } from '../../shared/components/RunList';
import { RunDetail } from './components/RunDetail';
import { EnvironmentSelect } from './components/EnvironmentSelect';
import { useIsMobile } from '../../shared/hooks/useIsMobile';

export function CasesTab() {
  const { cases, loadingCases, selectedCaseId, runs, selectedRun, executing,
          loadCases, selectCase, execute, loadRunDetail } = useRunStore();
  const { t } = useTranslation();
  const [envId, setEnvId] = useState<number | null>(null);
  const isMobile = useIsMobile();
  const currentProjectId = useProjectStore((s) => s.currentProjectId);
  const currentVersionId = useProjectStore((s) => s.currentVersionId);
  useEffect(() => { loadCases(); }, [loadCases, currentProjectId, currentVersionId]);
  const selectedCase = cases.find((c) => c.id === selectedCaseId);
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: isMobile ? 'column' : 'row' }}>
      <div style={{
        width: isMobile ? '100%' : 280,
        borderRight: isMobile ? 'none' : '1px solid var(--bg-card)',
        borderBottom: isMobile ? '1px solid var(--bg-card)' : 'none',
        display: 'flex',
        flexDirection: 'column',
        ...(isMobile ? { maxHeight: 320, overflowY: 'auto' } : {}),
      }}>
        <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--bg-card)', fontSize: 13, color: "var(--text-secondary)" }}>{t('api.casesTitle')}</div>
        <CasePicker cases={cases} selectedId={selectedCaseId} onSelect={selectCase} loading={loadingCases} emptyLabel={t('api.noCaseHint')} />
      </div>
      <div style={{
        width: isMobile ? '100%' : 340,
        borderRight: isMobile ? 'none' : '1px solid var(--bg-card)',
        borderBottom: isMobile ? '1px solid var(--bg-card)' : 'none',
        display: 'flex',
        flexDirection: 'column',
        ...(isMobile ? { maxHeight: 400, overflowY: 'auto' } : {}),
      }}>
        <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--bg-card)', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 13, color: "var(--text-primary)", flex: 1, minWidth: 80 }}>{selectedCase ? selectedCase.title : t('api.selectCase')}</span>
          <EnvironmentSelect value={envId} onChange={setEnvId} />
          {selectedCase && (
            <button onClick={() => execute(selectedCase.id, envId)} disabled={executing} style={{
              background: "var(--accent)", color: "var(--bg-base)", border: 'none', borderRadius: 4,
              padding: '4px 12px', cursor: executing ? 'wait' : 'pointer', fontSize: 12, fontWeight: 600,
              display: 'inline-flex', alignItems: 'center', gap: 4,
            }}>{executing ? t('api.executing') : <><Play size={12} strokeWidth={1.5} /> {t('api.execute')}</>}</button>
          )}
        </div>
        {selectedCase ? (
          <RunList runs={runs} selectedRunId={selectedRun?.id ?? null} onSelect={loadRunDetail} emptyLabel={t('api.noCaseRuns')} />
        ) : (
          <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <ArrowLeft size={12} strokeWidth={1.5} /> {t('api.selectCase')}
          </div>
        )}
      </div>
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--bg-card)', fontSize: 13, color: "var(--text-secondary)" }}>{t('api.runDetailTitle')}</div>
        <div style={{ flex: 1, overflow: 'auto' }}><RunDetail run={selectedRun} /></div>
      </div>
    </div>
  );
}
