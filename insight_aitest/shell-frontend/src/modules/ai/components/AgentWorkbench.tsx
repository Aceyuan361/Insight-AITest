import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useTaskStore, type AgentMessage } from '../store/taskStore';
import { useAgentProfileStore } from '../store/agentProfileStore';
import { AgentInput } from './AgentInput';
import { UnderstandCard } from './UnderstandCard';
import { StrategyCard } from './StrategyCard';
import { TaskProgress } from './TaskProgress';
import { TaskResult } from './TaskResult';
import { AgentProgress } from './AgentProgress';
import { TestPointCard } from './cards/TestPointCard';
import { CaseReviewCard } from './cards/CaseReviewCard';
import { StepTrace } from './react/StepTrace';
import { RcaDialog } from './react/RcaDialog';
import { ThinkingPanel } from './ThinkingPanel';
import { ThinkingLevelControl, type ThinkingLevel } from './ThinkingLevelControl';
import { KbToggle } from './KbToggle';
import { ModelPicker } from './ModelPicker';
import { glassInputBar, text, SPRING, RADIUS } from './agentStyles';
import { RotateCcw } from 'lucide-react';
import agentAvatarDefault from '../../../assets/agent-avatar.jpg';

export function AgentWorkbench() {
  const { messages, phase, phaseMessage, streamingThinking, streamingMessage, resetConversation, stopStreaming, thinkingLevel, setThinkingLevel, kbMode, setKbMode, selectedDocIds, setSelectedDocIds } = useTaskStore();
  const agentName = useAgentProfileStore((s) => s.name);
  const agentAvatar = useAgentProfileStore((s) => s.avatar);
  const avatarSrc = agentAvatar ?? agentAvatarDefault;
  const scrollRef = useRef<HTMLDivElement>(null);
  const { t } = useTranslation();

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, phase, streamingMessage, streamingThinking]);

  const busy = phase === 'uploading' || phase === 'understanding' || phase === 'strategizing' || phase === 'executing';
  const showStreamingBubble = streamingMessage !== null && streamingMessage !== undefined;
  const showThinkingChain = busy && (streamingThinking !== null && streamingThinking !== undefined);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
      <style>{aiKeyframes}</style>
      {/* 对话区域 */}
      <div ref={scrollRef} style={{ flex: 1, overflow: 'auto', padding: '24px 0' }}>
        <div style={{ maxWidth: 720, margin: '0 auto', padding: '0 24px' }}>
          {messages.length === 0 && !busy && <AgentWelcomeState name={agentName} avatar={avatarSrc} />}
          {messages.map((msg, i) => (
            <MessageBubble key={i} msg={msg} />
          ))}
          {/* 思维链 */}
          {showThinkingChain && (
            <ThinkingPanel thinking={streamingThinking!} streaming />
          )}
          {/* 流式文本气泡（LLM 生成中） */}
          {showStreamingBubble && (
            <MessageBubble
              msg={{ role: 'agent', card: 'chat', content: streamingMessage + ' ▌' }}
            />
          )}
          {/* 等待首个 token */}
          {busy && !showStreamingBubble && !showThinkingChain && (
            <div style={{ marginBottom: 16, color: text.muted, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)', animation: 'agent-pulse 1.2s ease-in-out infinite' }} />
              {phaseMessage || t('ai.thinkingDefault')}
            </div>
          )}
          {/* 任务进度 */}
          {busy && (
            <>
              <AgentProgress phase={phase} message={phaseMessage} thinking={streamingThinking} />
              {(phase === 'understanding' || phase === 'strategizing') && (
                <div style={{ textAlign: 'center', marginBottom: 12 }}>
                  <button
                    onClick={stopStreaming}
                    style={{
                      background: 'none', border: '1px solid var(--border-strong)', color: 'var(--text-secondary)',
                      borderRadius: 999, padding: '4px 16px', cursor: 'pointer', fontSize: 11,
                    }}
                  >
                    {t('ai.stopGen')}
                  </button>
                </div>
              )}
            </>
          )}
          {/* 流式中可中断 */}
          {busy && (showStreamingBubble || showThinkingChain) && (
            <div style={{ textAlign: 'center', marginBottom: 12 }}>
              <button
                onClick={stopStreaming}
                style={{
                  background: 'none', border: '1px solid var(--border-strong)', color: 'var(--text-secondary)',
                  borderRadius: 999, padding: '4px 16px', cursor: 'pointer', fontSize: 11,
                }}
              >
                {t('ai.stopGen')}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 浮动输入栏（Spotlight 风格，悬浮在对话区上方） */}
      <div style={{ padding: '0 24px 16px' }}>
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          {/* 思考级别 + 知识库检索 + 模型切换控制（输入栏上方） */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginBottom: 6 }}>
            <ModelPicker size="sm" />
            <KbToggle
              mode={kbMode}
              onModeChange={setKbMode}
              selectedDocIds={selectedDocIds}
              onDocIdsChange={setSelectedDocIds}
            />
            <ThinkingLevelControl
              value={thinkingLevel}
              onChange={(lv: ThinkingLevel) => setThinkingLevel(lv)}
              size="sm"
            />
          </div>
          <div style={{ ...glassInputBar, padding: 12 }}>
            <AgentInput />
          </div>
          {messages.length > 0 && (
            <button
              onClick={() => resetConversation()}
              style={{
                background: 'none', border: 'none', color: text.muted,
                cursor: 'pointer', fontSize: 11, marginTop: 8, padding: 0,
                transition: `color 0.2s ${SPRING}`,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = text.secondary)}
              onMouseLeave={(e) => (e.currentTarget.style.color = text.muted)}
            >
              <RotateCcw size={11} strokeWidth={1.5} style={{ verticalAlign: '-1px', marginRight: 4 }} />{t('ai.startNew')}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function AgentWelcomeState({ name, avatar }: { name: string; avatar: string }) {
  const { t } = useTranslation();
  return (
    <div style={{ textAlign: 'center', padding: '60px 20px 40px' }}>
      <img
        src={avatar}
        alt={t('ai.agentAvatarAlt', { name })}
        style={{
          width: 120, height: 120, borderRadius: '50%', objectFit: 'cover',
          margin: '0 auto 20px', display: 'block',
          border: '1px solid var(--border)', boxShadow: 'var(--shadow-elevated)',
        }}
      />
      <p style={{ fontSize: 15, lineHeight: 1.4, color: text.primary, maxWidth: 360, margin: '0 auto 6px', fontWeight: 500 }}>
        {t('ai.welcomeHi', { name })}
      </p>
      <p style={{ fontSize: 13, lineHeight: 1.8, color: text.secondary, maxWidth: 360, margin: '0 auto' }}>
        {t('ai.welcomeDesc')}
        <br />
        {t('ai.welcomeUploadHint')}
      </p>
    </div>
  );
}

function MessageBubble({ msg }: { msg: AgentMessage }) {
  const isUser = msg.role === 'user';
  const { t } = useTranslation();
  // ReAct trace / rca：progress 卡片下展示 trace，中止时弹出 RCA
  const trace = useTaskStore((s) => (msg.taskId ? s.trace[msg.taskId] : undefined));
  const taskRca = useTaskStore((s) => (msg.taskId ? s.rca[msg.taskId] : undefined));
  const [rcaOpen, setRcaOpen] = useState(false);
  const hasTrace = !!trace && Object.keys(trace).length > 0;
  // 当出现 rca 且尚未交互关闭时，默认展示
  const rcaVisible = !!taskRca && rcaOpen;

  // card 类消息（understand/strategies/progress/result）走卡片渲染；chat 走普通气泡
  if (!isUser && msg.card && msg.card !== 'chat') {
    return (
      <div style={{ marginBottom: 16, animation: 'agent-msg-enter 0.4s cubic-bezier(0.16,1,0.3,1)' }}>
        {msg.card === 'understand' && msg.content && <UnderstandCard summary={msg.content} />}
        {msg.card === 'strategies' && <StrategyCard />}
        {msg.card === 'progress' && <TaskProgress />}
        {msg.card === 'result' && <TaskResult />}
        {msg.card === 'test_points' && msg.taskId && <TestPointCard taskId={msg.taskId} />}
        {msg.card === 'case_review' && msg.taskId && <CaseReviewCard taskId={msg.taskId} />}
        {/* ReAct trace：progress 卡片下按 step 折叠展示 */}
        {msg.card === 'progress' && msg.taskId && hasTrace && (
          <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.04em', marginBottom: 2, paddingLeft: 2 }}>
              {t('ai.reactTrace')}
            </div>
            {Object.entries(trace!)
              .sort(([a], [b]) => Number(a) - Number(b))
              .map(([idx, entries]) => (
                <StepTrace key={idx} stepIndex={Number(idx)} entries={entries} />
              ))}
          </div>
        )}
        {/* 中止时：在 trace 区下方放一个"查看根因分析"入口 */}
        {msg.card === 'progress' && msg.taskId && taskRca && (
          <div style={{ marginTop: 8 }}>
            <button
              onClick={() => setRcaOpen(true)}
              style={{
                background: 'rgba(220,38,38,0.08)',
                border: '1px solid rgba(220,38,38,0.3)',
                color: 'var(--error)',
                borderRadius: 999,
                padding: '4px 14px',
                cursor: 'pointer',
                fontSize: 11,
                fontWeight: 600,
              }}
            >
              {t('ai.abortedRca')}
            </button>
          </div>
        )}
        {msg.taskId && taskRca && (
          <RcaDialog open={rcaVisible} rca={taskRca} onClose={() => setRcaOpen(false)} />
        )}
      </div>
    );
  }

  return (
    <div
      style={{
        marginBottom: 16,
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        animation: 'agent-msg-enter 0.35s cubic-bezier(0.16,1,0.3,1)',
      }}
    >
      <div
        style={{
          maxWidth: '80%',
          padding: '12px 16px',
          borderRadius: isUser ? `${RADIUS.lg}px ${RADIUS.lg}px 4px ${RADIUS.lg}px` : `${RADIUS.lg}px ${RADIUS.lg}px ${RADIUS.lg}px 4px`,
          background: isUser ? 'rgba(16,185,129,0.12)' : 'var(--bg-card)',
          border: isUser ? '1px solid rgba(16,185,129,0.25)' : '1px solid var(--border)',
          fontSize: 14,
          color: text.primary,
          lineHeight: 1.6,
          boxShadow: 'var(--shadow-card)',
        }}
      >
        {/* chat 模式的思考过程（落定后可折叠） */}
        {!isUser && msg.thinking && <ThinkingPanel thinking={msg.thinking} />}
        {isUser ? (
          <span>{msg.content}</span>
        ) : (
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {msg.content || ''}
            </ReactMarkdown>
          </div>
        )}
        {msg.files && msg.files.length > 0 && (
          <div style={{ marginTop: 8, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {msg.files.map((f, i) => (
              <span
                key={i}
                style={{
                  fontSize: 11,
                  color: text.accent,
                  background: 'rgba(16,185,129,0.08)',
                  border: '1px solid rgba(16,185,129,0.2)',
                  padding: '2px 8px',
                  borderRadius: RADIUS.sm,
                }}
              >
                {f}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** AI 入场动画 keyframe（Stage 4：删呼吸/光球后只剩入场） */
const aiKeyframes = `
@keyframes agent-msg-enter {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes agent-pulse {
  0%, 100% { opacity: 0.4; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}
`;
