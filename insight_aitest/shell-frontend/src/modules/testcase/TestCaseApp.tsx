import { useEffect } from 'react';
import { useLocation, useNavigate, Outlet } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { CaseList } from './components/CaseList';
import { useCaseStore } from './store/caseStore';
import { useProjectStore } from '../../shared/store/projectStore';
import { useIsMobile } from '../../shared/hooks/useIsMobile';
import { ModuleHelpButton } from '../../shared/components/ModuleHelpButton';

type View = 'list' | 'generate' | 'image';

export function TestCaseApp() {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { loadCases, activeId, createCase } = useCaseStore();
  const currentProjectId = useProjectStore((s) => s.currentProjectId);
  const currentVersionId = useProjectStore((s) => s.currentVersionId);
  const isMobile = useIsMobile();

  useEffect(() => { loadCases(); }, [loadCases, currentProjectId, currentVersionId]);

  const seg = location.pathname.split('/').filter(Boolean).pop() ?? 'list';
  const view: View = (['list', 'generate', 'image'].includes(seg) ? seg : 'list') as View;

  const handleNew = async () => {
    await createCase({ title: t('testcase.defaultCaseTitle'), type: 'functional', content: { steps: [], expected: '' } });
    navigate('list', { replace: true });
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: isMobile ? 'column' : 'row', background: "var(--bg-base)", color: "var(--text-primary)" }}>
      <CaseList
        isMobile={isMobile}
        onNew={handleNew}
        onAnalyze={() => navigate('generate')}
        onFromImage={() => navigate('image')}
      />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--bg-card)',
          display: 'flex', gap: 12, alignItems: 'center' }}>
          {view !== 'list' && (
            <button onClick={() => navigate('list')} style={{
              background: 'none', border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)",
              padding: '4px 10px', borderRadius: 4, cursor: 'pointer',
              display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <ArrowLeft size={12} strokeWidth={1.5} /> {t('testcase.backToList')}
            </button>
          )}
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            {view === 'list' ? (activeId ? t('testcase.caseDetail') : t('testcase.generate'))
              : view === 'generate' ? t('testcase.aiAnalyzeGenerate') : t('testcase.screenshotGenerateUi')}
          </span>
          <div style={{ flex: 1 }} />
          <ModuleHelpButton namespace="testcase" />
        </div>
        <Outlet />
      </div>
    </div>
  );
}

export default TestCaseApp;
