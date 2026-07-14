import { useTranslation } from 'react-i18next';
import { useTaskStore } from '../store/taskStore';
import { glassPanel, text, RADIUS } from './agentStyles';
import { Check, X, Circle } from 'lucide-react';

/** 执行类 step 的 result 字段 shape（execute_api_case / execute_ui_case / run_api_suite 返回） */
interface ExecStepResult {
  status?: string;
  fix_rounds?: number;
  passed_steps?: number;
  total_steps?: number;
  failures?: StepFailure[];
  title?: string;
  case_id?: number;
}

/** 单个失败步骤明细 */
interface StepFailure {
  step_index?: number;
  error?: string;
  status_code?: number;
}

/** 把 Record<string, unknown> 窄化成 ExecStepResult（运行时不变，tsc 能检查字段拼写） */
function asExecResult(r: unknown): ExecStepResult {
  return (r ?? {}) as ExecStepResult;
}

export function TaskProgress() {
  const { stepLogs, currentTask } = useTaskStore();
  const { t } = useTranslation();
  const total = currentTask?.total_steps || 0;
  const done = stepLogs.filter((l) => l.type === 'step_done').length;
  const failed = stepLogs.filter((l) => l.type === 'step_error').length;
  const progressPct = total > 0 ? Math.round(((done + failed) / total) * 100) : 0;

  return (
    <div style={{ ...glassPanel, padding: 16, borderRadius: RADIUS.lg }}>
      {/* 进度条 */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
          <span style={{ fontSize: 11, color: text.accent, fontWeight: 600, letterSpacing: '0.04em' }}>
            {t('ai.execRunning')}
          </span>
          <span style={{ fontSize: 11, color: text.muted }}>
            {done + failed}/{total}
          </span>
        </div>
        <div
          style={{
            height: 3,
            borderRadius: 2,
            background: 'var(--track)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${progressPct}%`,
              background: 'linear-gradient(90deg, var(--accent), var(--accent-hover))',
              borderRadius: 2,
              transition: 'width 0.4s cubic-bezier(0.16,1,0.3,1)',
              boxShadow: '0 0 8px rgba(91,140,123,0.3)',
            }}
          />
        </div>
      </div>

      {/* 步骤列表 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {stepLogs.map((log, i) => {
          const status = log.type;
          const er = asExecResult(log.result);
          // 执行类 step：展示通过/失败状态 + 修复轮数
          const isExecStep = status === 'step_done' && !!er.status;
          const execStatus = isExecStep ? er.status! : null;
          const fixRounds = er.fix_rounds;
          const failures = er.failures;
          const passedSteps = er.passed_steps;
          const totalSteps = er.total_steps;

          // 执行 step 的颜色：passed=绿，failed/error=红
          const execOk = execStatus === 'passed';
          const borderClr = isExecStep
            ? (execOk ? 'rgba(52,211,153,0.15)' : 'rgba(248,113,113,0.15)')
            : status === 'step_done' ? 'rgba(52,211,153,0.15)'
            : status === 'step_error' ? 'rgba(248,113,113,0.15)' : 'rgba(91,140,123,0.12)';

          return (
            <div
              key={i}
              style={{
                padding: '8px 12px',
                borderRadius: RADIUS.sm,
                fontSize: 13,
                border: `1px solid ${borderClr}`,
                background: 'var(--bg-card)',
                animation: 'agent-msg-enter 0.3s ease',
              }}
            >
              <span style={{ color: text.primary, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                {status === 'step_done'
                  ? (isExecStep ? (execOk ? <Check size={12} strokeWidth={1.5} /> : <X size={12} strokeWidth={1.5} />)
                    : <Check size={12} strokeWidth={1.5} />)
                  : status === 'step_error' ? <X size={12} strokeWidth={1.5} />
                  : <Circle size={12} strokeWidth={1.5} />}
                <span>{log.desc}</span>
              </span>
              {status === 'step_done' && !isExecStep && er.title && (
                <span style={{ color: text.muted, marginLeft: 8 }}>
                  {er.title}
                </span>
              )}
              {/* 执行类 step：展示通过率 + 修复轮数 */}
              {isExecStep && (
                <span style={{ marginLeft: 8, fontSize: 12 }}>
                  <span style={{ color: execOk ? text.success : text.danger }}>
                    {execOk ? t('ai.execPassed') : t('ai.execFailed')}
                  </span>
                  {passedSteps !== undefined && totalSteps !== undefined && (
                    <span style={{ color: text.muted }}> ({passedSteps}/{totalSteps})</span>
                  )}
                  {fixRounds !== undefined && fixRounds > 0 && (
                    <span style={{ color: text.accent, marginLeft: 4 }}>{t('ai.fixRoundsHint', { count: fixRounds })}</span>
                  )}
                </span>
              )}
              {/* 执行失败：折叠展示失败摘要 */}
              {isExecStep && !execOk && failures && failures.length > 0 && (
                <div style={{ marginTop: 4, fontSize: 12, color: text.danger, lineHeight: 1.5 }}>
                  {failures.slice(0, 2).map((f, fi) => (
                    <div key={fi}>
                      · {t('ai.stepFailurePrefix', { index: f.step_index })}: {f.status_code ? `HTTP ${f.status_code}` : ''} {f.error ? `— ${f.error.slice(0, 80)}` : ''}
                    </div>
                  ))}
                </div>
              )}
              {status === 'step_error' && log.error && (
                <div style={{ color: text.danger, marginTop: 4, fontSize: 12 }}>{log.error}</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
