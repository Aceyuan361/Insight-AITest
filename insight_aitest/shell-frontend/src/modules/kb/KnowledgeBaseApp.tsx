import { BookOpen } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { KnowledgeBase } from './components/KnowledgeBase';
import { ModuleHelpButton } from '../../shared/components/ModuleHelpButton';

export function KnowledgeBaseApp() {
  const { t } = useTranslation();
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: "var(--bg-base)", color: "var(--text-primary)" }}>
      <div
        style={{
          padding: '8px 16px',
          borderBottom: '1px solid var(--bg-card)',
          display: 'flex',
          alignItems: 'center',
        }}
      >
        <span style={{ fontSize: 13, color: "var(--text-secondary)", display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <BookOpen size={14} strokeWidth={1.5} /> {t('kb.title')}
        </span>
        <div style={{ flex: 1 }} />
        <ModuleHelpButton namespace="kb" />
      </div>
      <KnowledgeBase />
    </div>
  );
}

export default KnowledgeBaseApp;
