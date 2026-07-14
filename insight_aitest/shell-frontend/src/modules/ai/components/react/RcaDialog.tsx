import { useTranslation } from 'react-i18next';
import type { TaskRca } from '../../store/taskStore';
import { Modal } from '../../../../components/ui/modal';
import { text, RADIUS, SPRING } from '../agentStyles';

/** 任务中止时的根因分析（RCA）弹窗。展示 reason / rca / trace 摘要。 */
export function RcaDialog({
  open,
  rca,
  onClose,
}: {
  open: boolean;
  rca: TaskRca | null;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  return (
    <Modal
      open={open}
      onOpenChange={(o) => { if (!o) onClose(); }}
      title={t('ai.rcaTitle')}
      width="min(560px, 90vw)"
    >
      {rca ? (
        <div style={{ padding: '8px 20px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* 中止 step */}
          <Section label={t('ai.rcaAbortStep')}>
            <span style={{ fontSize: 13, color: text.primary }}>Step {rca.step_index}</span>
          </Section>

          {/* 原因 */}
          {rca.reason && (
            <Section label={t('ai.rcaAbortReason')}>
              <div style={{ fontSize: 13, color: text.primary, lineHeight: 1.6 }}>
                {rca.reason}
              </div>
            </Section>
          )}

          {/* RCA 详情 */}
          {Object.keys(rca.rca || {}).length > 0 && (
            <Section label={t('ai.rcaRootCause')}>
              <pre style={preStyle}>{JSON.stringify(rca.rca, null, 2)}</pre>
            </Section>
          )}

          {/* trace 摘要 */}
          {rca.trace && rca.trace.length > 0 && (
            <Section label={t('ai.rcaTraceSummary', { count: rca.trace.length })}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {rca.trace.map((e, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      gap: 8,
                      fontSize: 11,
                      color: text.secondary,
                      padding: '4px 0',
                      borderBottom: i < rca.trace.length - 1 ? '1px solid var(--hairline-soft)' : 'none',
                    }}
                  >
                    <span style={{ color: text.muted, flexShrink: 0 }}>
                      s{e.step_index}·i{e.iteration}
                    </span>
                    <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {e.action?.skill}{e.action?.desc ? `：${e.action.desc}` : ''}
                    </span>
                    <span style={{ color: e.decision === 'abort' ? 'var(--error)' : text.muted, flexShrink: 0 }}>
                      {e.decision}
                    </span>
                  </div>
                ))}
              </div>
            </Section>
          )}
        </div>
      ) : (
        <div style={{ padding: 20, fontSize: 13, color: text.muted }}>{t('ai.rcaNoData')}</div>
      )}

      <div style={{ padding: '0 20px 20px', display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: '1px solid var(--border-strong)',
            color: text.secondary,
            borderRadius: 10,
            padding: '8px 16px',
            cursor: 'pointer',
            fontSize: 13,
            transition: `all 0.15s ${SPRING}`,
          }}
        >
          {t('common.close')}
        </button>
      </div>
    </Modal>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ fontSize: 10, color: text.accent, fontWeight: 600, letterSpacing: '0.04em' }}>
        {label}
      </div>
      {children}
    </div>
  );
}

const preStyle: React.CSSProperties = {
  margin: 0,
  padding: '8px 10px',
  background: 'var(--bg-card)',
  border: '1px solid var(--border)',
  borderRadius: RADIUS.sm,
  fontSize: 11,
  lineHeight: 1.5,
  color: text.secondary,
  fontFamily: 'var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace)',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
  maxHeight: 220,
  overflow: 'auto',
};
