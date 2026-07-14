import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ConversationSidebar } from './components/ConversationSidebar';
import { AgentWorkbench } from './components/AgentWorkbench';
import { useConversationStore } from './store/conversationStore';
import { useTaskStore } from './store/taskStore';
import { useConfigStore } from './store/configStore';
import { useAgentProfileStore } from './store/agentProfileStore';
import { useProjectStore } from '../../shared/store/projectStore';
import { useIsMobile } from '../../shared/hooks/useIsMobile';
import { Bot } from 'lucide-react';
import { ModuleHelpButton } from '../../shared/components/ModuleHelpButton';

export function AIApp() {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const { loadConversations } = useConversationStore();
  const { loadTasks } = useTaskStore();
  const { config, loadConfig } = useConfigStore();
  const agentName = useAgentProfileStore((s) => s.name);
  const currentProjectId = useProjectStore((s) => s.currentProjectId);

  useEffect(() => {
    loadConversations();
    loadTasks();
    loadConfig();
  }, [currentProjectId]);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: isMobile ? 'column' : 'row', background: "var(--bg-base)", color: "var(--text-primary)" }}>
      <ConversationSidebar isMobile={isMobile} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
        <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--bg-card)', display: 'flex', gap: 12, alignItems: 'center' }}>
          <span style={{ fontSize: 13, color: "var(--text-secondary)", display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <Bot size={14} strokeWidth={1.5} /> {agentName}
          </span>
          {config && (
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{t('ai.modelInfo', { model: config.chat_model })}</span>
          )}
          <div style={{ flex: 1 }} />
          <ModuleHelpButton namespace="ai" />
        </div>
        <AgentWorkbench />
      </div>
    </div>
  );
}

export default AIApp;
