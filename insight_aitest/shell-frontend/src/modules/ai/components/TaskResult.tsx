import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useTaskStore } from '../store/taskStore';
import { glassPanelStrong, primaryButton, text, RADIUS } from './agentStyles';

export function TaskResult() {
  const { currentTask } = useTaskStore();
  const navigate = useNavigate();
  const { t } = useTranslation();
  if (!currentTask) return null;

  const result = currentTask.result || {};
  const caseIds: number[] = (result.case_ids as number[]) || [];
  const summary = (result.summary as string) || '';
  const isFailed = currentTask.status === 'failed';

  // 从步骤结果中提取执行类 step 的汇总
  const steps = (result.steps as Array<Record<string, unknown>>) || [];
  const execSteps = steps
    .map((s) => s.result as Record<string, unknown> | undefined)
    .filter((r): r is Record<string, unknown> => !!r && typeof r.status === 'string');
  const passedExec = execSteps.filter((r) => r.status === 'passed').length;
  const failedExec = execSteps.filter((r) => r.status === 'failed').length;
  const totalFixRounds = execSteps.reduce(
    (acc, r) => acc + (typeof r.fix_rounds === 'number' ? r.fix_rounds : 0),
    0,
  );
  const hasExecResults = execSteps.length > 0;

  return (
    <div
      style={{
        ...glassPanelStrong,
        padding: 16,
        borderRadius: RADIUS.lg,
        borderLeft: `3px solid ${isFailed ? 'rgba(248,113,113,0.5)' : 'rgba(52,211,153,0.5)'}`,
      }}
    >
      <div
        style={{
          fontSize: 14,
          fontWeight: 600,
          color: isFailed ? text.danger : text.success,
          marginBottom: 8,
        }}
      >
        {isFailed ? t('ai.taskFailed') : t('ai.taskCompleted')}
      </div>
      {summary && (
        <div style={{ fontSize: 13, color: text.secondary, lineHeight: 1.6 }}>{summary}</div>
      )}

      {/* 执行结果汇总 */}
      {hasExecResults && (
        <div
          style={{
            display: 'flex',
            gap: 16,
            marginTop: 10,
            padding: '8px 12px',
            borderRadius: RADIUS.sm,
            background: 'var(--surface-tint)',
            border: '1px solid var(--hairline-soft)',
            fontSize: 12,
          }}
        >
          <span>
            <span style={{ color: text.muted }}>{t('ai.execVerification')}</span>
            <span style={{ color: text.success, fontWeight: 600 }}>{t('ai.passedCount', { count: passedExec })}</span>
            {failedExec > 0 && (
              <span style={{ color: text.danger, fontWeight: 600 }}>{t('ai.failedCount', { count: failedExec })}</span>
            )}
          </span>
          {totalFixRounds > 0 && (
            <span style={{ color: text.accent }}>{t('ai.autoFixRounds', { count: totalFixRounds })}</span>
          )}
        </div>
      )}

      {currentTask.error && (
        <div style={{ fontSize: 12, color: text.danger, marginTop: 8 }}>{currentTask.error}</div>
      )}
      {caseIds.length > 0 && (
        <div style={{ marginTop: 14, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            onClick={() => navigate('/testcase')}
            style={{
              ...primaryButton,
              transition: 'all 0.15s cubic-bezier(0.16,1,0.3,1)',
            }}
            onMouseDown={(e) => { e.currentTarget.style.transform = 'scale(0.97)'; }}
            onMouseUp={(e) => { e.currentTarget.style.transform = 'scale(1)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)'; }}
          >
            {t('ai.viewCaseList')}
          </button>
          {hasExecResults && (
            <button
              onClick={() => navigate('/api-runner')}
              style={{
                ...primaryButton,
                background: 'var(--surface-hover)',
                transition: 'all 0.15s cubic-bezier(0.16,1,0.3,1)',
              }}
              onMouseDown={(e) => { e.currentTarget.style.transform = 'scale(0.97)'; }}
              onMouseUp={(e) => { e.currentTarget.style.transform = 'scale(1)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)'; }}
            >
              {t('ai.viewExecDetail')}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
