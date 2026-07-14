import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react';
import { useTaskStore } from '../../store/taskStore';
import { glassPanelStrong, primaryButton, text, RADIUS, SPRING } from '../agentStyles';

/** 一条测试点（agent message.content 里 JSON 数组的元素结构）
 *  兼容新旧字段名：新结构 summary/suggested_type/suggested_design，
 *  旧结构 description/type_hint/design_hint。 */
interface TestPoint {
  id?: string | number;
  summary?: string;
  description?: string;
  suggested_type?: string;
  type_hint?: string;
  suggested_design?: string;
  design_hint?: string;
}

/** 测试点审阅卡片（用例审阅面板阶段 1）。
 *  展示 agent 提取的测试点，允许移除不想要的，确认范围后触发生成。 */
export function TestPointCard({ taskId }: { taskId: number }) {
  const messages = useTaskStore((s) => s.messages);
  const generateBatch = useTaskStore((s) => s.generateBatch);
  const phase = useTaskStore((s) => s.phase);
  const [generating, setGenerating] = useState(false);
  const { t } = useTranslation();

  // 找到该 task 对应的 test_points 卡片消息
  const msg = useMemo(
    () => messages.find((m) => m.card === 'test_points' && m.taskId === taskId),
    [messages, taskId],
  );

  const points: TestPoint[] = useMemo(() => {
    if (!msg?.content) return [];
    try {
      const parsed = JSON.parse(msg.content);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }, [msg?.content]);

  // 已移除的点 id 集合
  const [removed, setRemoved] = useState<Set<string>>(new Set());
  const keyOf = (p: TestPoint, i: number): string => String(p.id ?? `idx-${i}`);

  const visible = points.filter((p, i) => !removed.has(keyOf(p, i)));

  if (!msg) return null;

  const removePoint = (k: string) =>
    setRemoved((s) => {
      const next = new Set(s);
      next.add(k);
      return next;
    });

  const confirm = async () => {
    if (visible.length === 0 || isBusy) return;
    setGenerating(true);
    try {
      // generateBatch 在 store 内部从 useProjectStore 读 project/version
      await generateBatch(taskId, visible as unknown as Record<string, unknown>[]);
    } finally {
      // streamTask 走完后（done/error/cancelled）恢复按钮，允许重试或再次确认
      setGenerating(false);
    }
  };

  // phase 非 executing 时即使 generating 被遗留也允许交互（finally 已兜底 reset）
  const isBusy = generating && phase === 'executing';

  return (
    <div
      style={{
        ...glassPanelStrong,
        padding: 16,
        borderRadius: RADIUS.lg,
        borderLeft: '3px solid rgba(91,140,123,0.5)',
      }}
    >
      <div
        style={{
          fontSize: 11,
          color: text.accent,
          fontWeight: 600,
          marginBottom: 6,
          letterSpacing: '0.04em',
        }}
      >
        {t('ai.testPointReview')}
      </div>
      <p style={{ fontSize: 12, color: text.muted, marginBottom: 14 }}>
        {t('ai.testPointHint', { total: points.length })}
      </p>

      {visible.length === 0 ? (
        <p style={{ fontSize: 13, color: text.muted, margin: '8px 0' }}>
          {t('ai.allRemoved')}
        </p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {visible.map((p, i) => {
            const k = keyOf(p, i);
            return (
              <div
                key={k}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 10,
                  padding: '8px 10px',
                  borderRadius: RADIUS.md,
                  background: 'var(--bg-card)',
                  border: '1px solid var(--hairline-soft)',
                  transition: `all 0.15s ${SPRING}`,
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, color: text.primary, lineHeight: 1.5, wordBreak: 'break-word' }}>
                    {p.summary || p.description || t('ai.noDescription')}
                  </div>
                  {(p.suggested_type || p.type_hint || p.suggested_design || p.design_hint) && (
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
                      {(p.suggested_type || p.type_hint) && (
                        <span style={badgeStyle('type')}>{p.suggested_type || p.type_hint}</span>
                      )}
                      {(p.suggested_design || p.design_hint) && (
                        <span style={badgeStyle('design')}>{p.suggested_design || p.design_hint}</span>
                      )}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => removePoint(k)}
                  title={t('ai.removePoint')}
                  style={{
                    flexShrink: 0,
                    background: 'none',
                    border: 'none',
                    color: text.muted,
                    cursor: 'pointer',
                    padding: 2,
                    lineHeight: 0,
                    transition: `color 0.15s ${SPRING}`,
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = text.danger)}
                  onMouseLeave={(e) => (e.currentTarget.style.color = text.muted)}
                >
                  <X size={14} strokeWidth={1.5} />
                </button>
              </div>
            );
          })}
        </div>
      )}

      <div style={{ marginTop: 14 }}>
        <button
          onClick={confirm}
          disabled={visible.length === 0 || isBusy}
          title={isBusy ? t('ai.generatingHint') : t('ai.confirmScopeHint')}
          style={{
            ...primaryButton,
            opacity: visible.length === 0 || isBusy ? 0.4 : 1,
            transition: `all 0.15s ${SPRING}`,
          }}
        >
          {isBusy ? t('ai.generatingHint') : t('ai.confirmScopeBtn', { count: visible.length })}
        </button>
        {!isBusy && (
          <div style={{ fontSize: 10, color: text.muted, marginTop: 6 }}>
            {t('ai.confirmScopeFooter')}
          </div>
        )}
      </div>
    </div>
  );
}

/** 测试点小徽章样式 */
function badgeStyle(kind: 'type' | 'design'): React.CSSProperties {
  const isType = kind === 'type';
  return {
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: '0.03em',
    color: isType ? text.secondary : text.accent,
    background: isType ? 'var(--surface-hover)' : 'rgba(16,185,129,0.08)',
    border: `1px solid ${isType ? 'var(--hairline-soft)' : 'rgba(16,185,129,0.2)'}`,
    padding: '2px 8px',
    borderRadius: RADIUS.sm,
  };
}
