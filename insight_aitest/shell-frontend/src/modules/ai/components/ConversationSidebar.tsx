import { useTranslation } from 'react-i18next';
import { useTaskStore } from '../store/taskStore';
import { useConfirmStore } from '../../../shared/store/confirmStore';
import { useAgentProfileStore } from '../store/agentProfileStore';
import { AgentIdentityCard } from './AgentIdentityCard';
import { Bot, Check, X, Loader, Circle, CircleDot, Cog } from 'lucide-react';

export interface ConversationSidebarProps {
  isMobile?: boolean;
}

/** Task 状态 → 显示颜色 + 图标 */
const STATUS_BADGE: Record<string, { labelKey: string; color: string; bg: string; Icon: typeof Check }> = {
  done: { labelKey: 'ai.statusDone', color: 'var(--chart-4)', bg: 'rgba(82,196,26,0.12)', Icon: Check },
  failed: { labelKey: 'ai.statusFailed', color: 'var(--error)', bg: 'rgba(255,77,79,0.12)', Icon: X },
  cancelled: { labelKey: 'ai.statusCancelled', color: "var(--text-secondary)", bg: 'rgba(136,136,136,0.12)', Icon: X },
  running: { labelKey: 'ai.statusRunning', color: "var(--accent)", bg: 'rgba(16,185,129,0.12)', Icon: Loader },
  pending_select: { labelKey: 'ai.statusPendingSelect', color: 'var(--chart-3)', bg: 'rgba(250,173,20,0.12)', Icon: CircleDot },
  pending_confirm: { labelKey: 'ai.statusPendingConfirm', color: 'var(--chart-3)', bg: 'rgba(250,173,20,0.12)', Icon: CircleDot },
  strategizing: { labelKey: 'ai.statusStrategizing', color: "var(--accent)", bg: 'rgba(16,185,129,0.12)', Icon: Cog },
  understanding: { labelKey: 'ai.statusUnderstanding', color: "var(--accent)", bg: 'rgba(16,185,129,0.12)', Icon: Cog },
};

export function ConversationSidebar({ isMobile }: ConversationSidebarProps) {
  const { tasks, currentTask, deleteTask, resetConversation, selectTask } = useTaskStore();
  const { confirm } = useConfirmStore();
  const agentName = useAgentProfileStore((s) => s.name);
  const { t } = useTranslation();

  return (
    <div
      style={{
        width: isMobile ? '100%' : 240,
        borderRight: '1px solid var(--bg-card)',
        display: 'flex',
        flexDirection: 'column',
        background: "var(--bg-base)",
        ...(isMobile ? { maxHeight: 240, overflowY: 'auto' } : {}),
      }}
    >
      {/* 新建任务 */}
      <div style={{ padding: '12px 12px 8px' }}>
        <button
          onClick={() => resetConversation()}
          style={{
            width: '100%',
            background: 'var(--bg-card)',
            border: '1px solid var(--bg-elevated)',
            color: 'var(--accent)',
            padding: '8px',
            borderRadius: 6,
            cursor: 'pointer',
          }}
        >
          {t('ai.newTask')}
        </button>
      </div>

      {/* 任务历史列表（按 conversation 分组） */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {tasks.length === 0 && (
          <div style={{ padding: '24px 16px', color: 'var(--text-muted)', fontSize: 12, textAlign: 'center', lineHeight: 1.8 }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><Bot size={13} strokeWidth={1.5} /> {agentName}</span><br />
            <span style={{ color: 'var(--text-muted)', whiteSpace: 'pre-line' }}>
              {t('ai.taskFlowHint')}
            </span>
          </div>
        )}
        {(() => {
          const grouped = new Map<number, typeof tasks>();
          const orphans: typeof tasks = [];
          for (const task of tasks) {
            if (task.conversation_id != null) {
              const group = grouped.get(task.conversation_id) || [];
              group.push(task);
              grouped.set(task.conversation_id, group);
            } else {
              orphans.push(task);
            }
          }

          const renderTaskItem = (task: typeof tasks[0], indent: boolean) => {
            const badge = STATUS_BADGE[task.status] || { labelKey: '', color: "var(--text-secondary)", bg: 'transparent', Icon: Circle };
            const active = currentTask?.id === task.id;
            return (
              <div
                key={task.id}
                onClick={() => selectTask(task.id)}
                title={t('ai.viewTaskHint')}
                style={{
                  padding: indent ? '4px 12px 4px 24px' : '8px 12px',
                  cursor: 'pointer',
                  background: active ? 'rgba(91,140,123,0.08)' : 'transparent',
                  borderLeft: active ? '2px solid var(--accent)' : '2px solid transparent',
                  display: 'flex', flexDirection: 'column', gap: 2,
                  transition: 'background 0.15s ease',
                }}
                onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = 'rgba(136,136,136,0.06)'; }}
                onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = 'transparent'; }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{
                    flex: 1, fontSize: 11, color: active ? "var(--accent)" : 'var(--text-secondary)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }} title={task.intent}>
                    {task.intent?.slice(0, 30) || t('ai.noIntent')}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      confirm({
                        title: t('ai.confirmDeleteTaskTitle'),
                        message: t('ai.confirmDeleteTaskMsg', { name: task.intent?.slice(0, 30) || '' }),
                        variant: 'danger',
                        onConfirm: () => deleteTask(task.id),
                      });
                    }}
                    style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12,
                      ...(isMobile ? { minWidth: 44, minHeight: 44, padding: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' } : {}) }}
                  >×</button>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{
                    fontSize: 9, padding: '1px 5px', borderRadius: 8,
                    color: badge.color, background: badge.bg, border: `1px solid ${badge.color}33`,
                    display: 'inline-flex', alignItems: 'center', gap: 2,
                  }}>
                    <badge.Icon size={9} strokeWidth={1.5} />
                    {t(badge.labelKey)}
                  </span>
                  <span style={{ fontSize: 9, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                    {new Date(task.created_at).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })}
                  </span>
                </div>
              </div>
            );
          };

          const elements: React.ReactNode[] = [];
          for (const [convId, convTasks] of grouped) {
            const groupTitle = convTasks[0]?.intent?.slice(0, 30) || t('ai.noIntent');
            const anyActive = convTasks.some(t => currentTask?.id === t.id);
            elements.push(
              <div key={`conv-${convId}`}>
                <div style={{
                  padding: '6px 12px 2px', fontSize: 10, fontWeight: 600,
                  color: anyActive ? 'var(--accent)' : 'var(--text-muted)',
                  textTransform: 'uppercase' as const, letterSpacing: '0.5px',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>{groupTitle}</div>
                {convTasks.map(t => renderTaskItem(t, true))}
              </div>
            );
          }
          {orphans.map(t => renderTaskItem(t, false))}
          return elements;
        })()}
      </div>

      <AgentIdentityCard isMobile={isMobile} />
    </div>
  );
}
