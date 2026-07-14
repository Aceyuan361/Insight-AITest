import { motion, useReducedMotion } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { Check } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { AgentPhase } from '../store/taskStore';
import { ThinkingPanel } from './ThinkingPanel';

/** 格式化秒数为 mm:ss */
function fmtElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

const STAGES: { key: string; labelKey: string; phases: AgentPhase[] }[] = [
  { key: 'understand', labelKey: 'ai.progressUnderstand', phases: ['uploading', 'understanding'] },
  { key: 'strategize', labelKey: 'ai.progressStrategize', phases: ['strategizing'] },
  { key: 'execute', labelKey: 'ai.progressExecute', phases: ['executing'] },
];

/**
 * 骨架屏式进度（替换原 BreathingIndicator 呼吸光球）。
 * 三段线性进度条：理解 / 策略 / 执行。
 * thinking 非 null 时内嵌 ThinkingPanel 展示实时思考过程。
 */
export function AgentProgress({
  phase,
  message,
  thinking,
}: {
  phase: AgentPhase;
  message: string;
  thinking?: string | null;
}) {
  const reduce = useReducedMotion();
  const { t } = useTranslation();
  const currentStageIdx = STAGES.findIndex((s) => s.phases.includes(phase));
  const showThinking = thinking !== null && thinking !== undefined && thinking.length > 0;
  const isBusy = currentStageIdx >= 0;  // 任何非 idle/done/error 阶段都计时

  // 所有繁忙阶段计时器
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!isBusy) { setElapsed(0); return; }
    const start = Date.now();
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [isBusy]);

  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      style={{
        padding: '12px 16px', marginBottom: 16, borderRadius: 12,
        background: 'var(--bg-card)', border: '1px solid var(--border)',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <span style={{ fontSize: 13, color: 'var(--accent)', fontWeight: 500 }}>
            {message}
            {elapsed > 0 && (
              <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 8, fontWeight: 400 }}>
                ⏱ {fmtElapsed(elapsed)}
              </span>
            )}
          </span>
        {currentStageIdx >= 0 && (
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {t('ai.stepProgress', { current: currentStageIdx + 1, total: STAGES.length })}
          </span>
        )}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        {STAGES.map((stage, i) => {
          const done = i < currentStageIdx;
          const current = i === currentStageIdx;
          return (
            <div key={stage.key} style={{ flex: 1, height: 4, borderRadius: 2, background: 'var(--bg-elevated)', overflow: 'hidden', position: 'relative' }}>
              {(done || current) && (
                <motion.div
                  initial={reduce ? false : { width: '0%' }}
                  animate={{ width: done ? '100%' : '65%' }}
                  transition={{ duration: 0.6, ease: 'easeOut' }}
                  style={{ height: '100%', background: 'var(--accent)', borderRadius: 2 }}
                />
              )}
              {done && (
                <Check strokeWidth={1.5} size={10} style={{ position: 'absolute', right: 2, top: -3, color: 'var(--accent)' }} />
              )}
            </div>
          );
        })}
      </div>
      {showThinking && (
        <div style={{ marginTop: 10 }}>
          <ThinkingPanel thinking={thinking!} streaming />
        </div>
      )}
    </motion.div>
  );
}
