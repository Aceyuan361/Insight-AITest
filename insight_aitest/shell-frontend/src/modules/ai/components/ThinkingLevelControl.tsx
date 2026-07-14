import * as Tooltip from '@radix-ui/react-tooltip';
import { useTranslation } from 'react-i18next';
import { Brain, HelpCircle } from 'lucide-react';
import { text, RADIUS, SPRING } from './agentStyles';

/**
 * 思考级别选择器 + 「？」规则提示。
 *
 * 级别：off（关闭）/ low（低）/ medium（中）/ high（高）。
 * 开关始终可主动开启；不支持思考参数的模型由后端安全忽略（不注入参数）。
 * 「？」hover 显示规则说明（每级含义 + 耗时/token 提醒）。
 *
 * 受控组件：value/onchange 由父组件管理（会话级 thinking_level）。
 */

export type ThinkingLevel = 'off' | 'low' | 'medium' | 'high';

const LEVELS: { value: ThinkingLevel; labelKey: string }[] = [
  { value: 'off', labelKey: 'ai.thinkingOff' },
  { value: 'low', labelKey: 'ai.thinkingLevelLow' },
  { value: 'medium', labelKey: 'ai.thinkingLevelMedium' },
  { value: 'high', labelKey: 'ai.thinkingLevelHigh' },
];

interface Props {
  value: ThinkingLevel;
  onChange: (level: ThinkingLevel) => void;
  size?: 'sm' | 'md';
  isMobile?: boolean;
}

export function ThinkingLevelControl({
  value,
  onChange,
  size = 'sm',
  isMobile,
}: Props) {
  const fontSize = size === 'sm' ? 11 : 12;
  const padding = isMobile ? '8px 10px' : '4px 10px';
  const { t } = useTranslation();

  return (
    <Tooltip.Provider delayDuration={200}>
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        <Brain
          size={13}
          strokeWidth={1.5}
          style={{ color: value !== 'off' ? text.accent : text.muted, flexShrink: 0 }}
        />
        <div
          role="radiogroup"
          aria-label={t('ai.thinkingLevelAriaLabel')}
          style={{
            display: 'inline-flex',
            border: `1px solid var(--border-strong)`,
            borderRadius: RADIUS.sm,
            overflow: 'hidden',
          }}
        >
          {LEVELS.map((lv) => {
            const active = value === lv.value;
            return (
              <button
                key={lv.value}
                role="radio"
                aria-checked={active}
                onClick={() => onChange(lv.value)}
                style={{
                  ...(!isMobile ? {} : { minWidth: 44, minHeight: 44, display: 'flex', alignItems: 'center', justifyContent: 'center' }),
                  padding,
                  fontSize,
                  cursor: 'pointer',
                  border: 'none',
                  borderRight: lv.value !== 'high' ? `1px solid var(--bg-elevated)` : 'none',
                  background: active ? 'rgba(16,185,129,0.14)' : 'transparent',
                  color: active ? text.accent : text.secondary,
                  fontWeight: active ? 600 : 400,
                  transition: `all 0.15s ${SPRING}`,
                  fontFamily: 'inherit',
                }}
                onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = 'rgba(136,136,136,0.08)'; }}
                onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = 'transparent'; }}
              >
                {t(lv.labelKey)}
              </button>
            );
          })}
        </div>

        {/* 「？」规则提示 */}
        <Tooltip.Root>
          <Tooltip.Trigger asChild>
            <button
              type="button"
              aria-label={t('ai.thinkingLevelHelpAria')}
              style={{
                background: 'none', border: 'none', cursor: 'help', padding: 2,
                color: text.muted, display: 'inline-flex', alignItems: 'center',
                transition: `color 0.15s ${SPRING}`,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = text.secondary)}
              onMouseLeave={(e) => (e.currentTarget.style.color = text.muted)}
            >
              <HelpCircle size={14} strokeWidth={1.5} />
            </button>
          </Tooltip.Trigger>
          <Tooltip.Portal>
            <Tooltip.Content
              sideOffset={6}
              style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-strong)',
                borderRadius: RADIUS.sm,
                padding: '10px 12px',
                maxWidth: 280,
                boxShadow: 'var(--shadow-elevated)',
                zIndex: 1100,
              }}
            >
              <ThinkingRules />
              <Tooltip.Arrow style={{ fill: 'var(--bg-elevated)', stroke: 'var(--border-strong)' }} />
            </Tooltip.Content>
          </Tooltip.Portal>
        </Tooltip.Root>
      </div>
    </Tooltip.Provider>
  );
}

function ThinkingRules() {
  const { t } = useTranslation();
  return (
    <div style={{ fontSize: 11, lineHeight: 1.7, color: text.secondary }}>
      <div style={{ fontWeight: 600, color: text.primary, marginBottom: 6 }}>{t('ai.thinkingRulesTitle')}</div>
      <Rule label={t('ai.thinkingOff')} desc={t('ai.thinkingRuleOffDesc')} />
      <Rule label={t('ai.thinkingLevelLow')} desc={t('ai.thinkingRuleLowDesc')} />
      <Rule label={t('ai.thinkingLevelMedium')} desc={t('ai.thinkingRuleMediumDesc')} />
      <Rule label={t('ai.thinkingLevelHigh')} desc={t('ai.thinkingRuleHighDesc')} />
      <div style={{ marginTop: 6, paddingTop: 6, borderTop: '1px solid var(--bg-card)', color: text.muted }}>
        {t('ai.thinkingRuleFooter')}
      </div>
    </div>
  );
}

function Rule({ label, desc }: { label: string; desc: string }) {
  return (
    <div style={{ display: 'flex', gap: 6, marginBottom: 2 }}>
      <span style={{ color: text.accent, fontWeight: 600, flexShrink: 0, width: 28 }}>{label}</span>
      <span style={{ color: text.secondary }}>{desc}</span>
    </div>
  );
}

/** 把旧的 thinking_enabled (bool) 迁移到 thinking_level（兼容历史数据）。 */
export function migrateThinkingLevel(raw: unknown): ThinkingLevel {
  if (raw === true) return 'medium';
  if (raw === false) return 'off';
  if (typeof raw === 'string' && ['off', 'low', 'medium', 'high'].includes(raw)) {
    return raw as ThinkingLevel;
  }
  return 'off';
}
