import { useEffect } from 'react';
import { ArrowLeft } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useRunStore } from './store/runStore';
import { useProjectStore } from '../../shared/store/projectStore';
import { useIsMobile } from '../../shared/hooks/useIsMobile';
import { CasePicker } from '../../shared/components/CasePicker';
import { CaseEditor } from './components/CaseEditor';

export function EditTab() {
  const { cases, loadingCases, selectedCaseId, loadCases, selectCase } = useRunStore();
  const { t } = useTranslation();
  const currentProjectId = useProjectStore((s) => s.currentProjectId);
  const currentVersionId = useProjectStore((s) => s.currentVersionId);
  const isMobile = useIsMobile();
  useEffect(() => { loadCases(); }, [loadCases, currentProjectId, currentVersionId]);
  const selectedCase = cases.find((c) => c.id === selectedCaseId);
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: isMobile ? 'column' : 'row' }}>
      <div style={{
        width: isMobile ? '100%' : 280,
        borderRight: isMobile ? 'none' : '1px solid var(--bg-card)',
        borderBottom: isMobile ? '1px solid var(--bg-card)' : 'none',
        ...(isMobile ? { maxHeight: 320, overflowY: 'auto' } : {}),
      }}>
        <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--bg-card)', fontSize: 13, color: "var(--text-secondary)" }}>{t('ui.casesTitle')}</div>
        <CasePicker cases={cases} selectedId={selectedCaseId} onSelect={selectCase} loading={loadingCases} emptyLabel={t('ui.noCasesHint')} />
      </div>
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {selectedCase ? (
          <CaseEditor caseId={selectedCase.id}
            initial={{ base_url: selectedCase.content.base_url, steps: selectedCase.content.steps || [] }} />
        ) : (
          <div style={{ padding: 24, color: 'var(--text-muted)', fontSize: 13, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <ArrowLeft size={13} strokeWidth={1.5} /> {t('ui.selectCaseToEdit')}
          </div>
        )}
      </div>
    </div>
  );
}
