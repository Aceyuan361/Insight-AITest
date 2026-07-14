import { useEffect, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useSuiteStore } from './store/suiteStore';
import { SuiteList } from './components/suite/SuiteList';
import { SuitePanel } from './components/suite/SuitePanel';
import { useIsMobile } from '../../shared/hooks/useIsMobile';

export function SuitesTab() {
  const { suites, selectedSuiteId, loadSuites, selectSuite } = useSuiteStore();
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const [creating, setCreating] = useState(false);
  useEffect(() => { loadSuites(); }, [loadSuites]);
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: isMobile ? 'column' : 'row' }}>
      <div style={{
        width: isMobile ? '100%' : 280,
        borderRight: isMobile ? 'none' : '1px solid var(--bg-card)',
        borderBottom: isMobile ? '1px solid var(--bg-card)' : 'none',
        ...(isMobile ? { maxHeight: 320, overflowY: 'auto' } : {}),
      }}>
        <SuiteList suites={suites} selectedId={selectedSuiteId}
          onSelect={(id) => { setCreating(false); selectSuite(id); }}
          onNew={() => { setCreating(true); selectSuite(null as any); }} />
      </div>
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {creating || selectedSuiteId ? (
          <SuitePanel suiteId={selectedSuiteId} onNew={() => setCreating(false)} />
        ) : (
          <div style={{ padding: 24, color: 'var(--text-muted)', fontSize: 13, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <ArrowLeft size={13} strokeWidth={1.5} /> {t('api.selectSuitePrompt')}
          </div>
        )}
      </div>
    </div>
  );
}
