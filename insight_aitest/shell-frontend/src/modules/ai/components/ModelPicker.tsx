import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, Check, Cpu } from 'lucide-react';
import { useConfigStore } from '../store/configStore';
import { text, RADIUS, SPRING } from './agentStyles';

/**
 * 模型快速切换器（输入栏内联，Cursor 风格）。
 *
 * 点击展开当前所有 Provider，选择后即时切换 active provider（全局生效）。
 * 当前生效的 Provider 显示其 name + chat_model。
 * 若未配置任何 Provider，显示"未配置"并提示去设置。
 */
interface Props {
  size?: 'sm' | 'md';
  isMobile?: boolean;
}

export function ModelPicker({ size = 'sm', isMobile }: Props) {
  const { config, activateProvider, loadConfig, saving } = useConfigStore();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const { t } = useTranslation();

  useEffect(() => {
    if (!config) loadConfig();
  }, [config, loadConfig]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const providers = config?.providers || [];
  const activeId = config?.active_provider_id || '';
  const active = providers.find((p) => p.id === activeId);

  const fontSize = size === 'sm' ? 11 : 12;
  const iconSize = size === 'sm' ? 13 : 14;
  const padding = isMobile ? '8px 10px' : '4px 10px';

  const handlePick = async (id: string) => {
    setOpen(false);
    if (id === activeId) return;
    try {
      await activateProvider(id);
    } catch (e: any) {
      alert(e.message || t('ai.switchFailed'));
    }
  };

  return (
    <div ref={ref} style={{ position: 'relative', display: 'inline-flex' }}>
      <button
        onClick={() => setOpen((v) => !v)}
        disabled={saving}
        title={active ? `${active.name} · ${active.chat_model}` : t('ai.noProviderConfigured')}
        style={{
          ...(isMobile ? { minWidth: 44, minHeight: 44, justifyContent: 'center' } : {}),
          padding,
          fontSize,
          cursor: saving ? 'wait' : 'pointer',
          border: '1px solid var(--border-strong)',
          borderRadius: RADIUS.sm,
          background: 'transparent',
          color: active ? text.secondary : text.muted,
          fontFamily: 'inherit',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          maxWidth: isMobile ? undefined : 200,
          transition: `all 0.15s ${SPRING}`,
        }}
      >
        <Cpu size={iconSize} strokeWidth={1.5} />
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {active ? active.chat_model : t('ai.noProviderConfigured')}
        </span>
        <ChevronDown size={iconSize - 2} strokeWidth={1.5} style={{ opacity: 0.6, flexShrink: 0 }} />
      </button>

      {open && (
        <div
          style={{
            position: 'absolute',
            bottom: '100%',
            right: 0,
            marginBottom: 4,
            minWidth: 240,
            maxWidth: 300,
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: RADIUS.sm,
            boxShadow: 'var(--shadow-elevated)',
            zIndex: 100,
            overflow: 'hidden',
          }}
        >
          <div style={{ padding: '6px 10px', fontSize: 10, color: text.muted, fontWeight: 600, letterSpacing: '0.04em', borderBottom: '1px solid var(--border)' }}>
            {t('ai.switchModelGlobal')}
          </div>
          {providers.length === 0 ? (
            <div style={{ padding: 12, fontSize: 12, color: text.muted }}>
              {t('ai.noProviderHint')}
            </div>
          ) : (
            <div style={{ maxHeight: 280, overflow: 'auto' }}>
              {providers.map((p) => {
                const isActive = p.id === activeId;
                return (
                  <button
                    key={p.id}
                    onClick={() => handlePick(p.id)}
                    style={{
                      width: '100%',
                      padding: '8px 10px',
                      border: 'none',
                      background: isActive ? 'rgba(91,140,123,0.12)' : 'transparent',
                      cursor: 'pointer',
                      textAlign: 'left',
                      fontFamily: 'inherit',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                    }}
                    onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = 'var(--bg-elevated)'; }}
                    onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 12, color: isActive ? text.accent : text.primary, fontWeight: isActive ? 600 : 400, display: 'flex', alignItems: 'center', gap: 6 }}>
                        {p.name}
                        {!p.api_key_set && (
                          <span style={{ fontSize: 9, color: 'var(--error)', border: '1px solid var(--error)', borderRadius: 2, padding: '0 4px' }}>{t('ai.noKeyShort')}</span>
                        )}
                      </div>
                      <div style={{ fontSize: 11, color: text.muted, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {p.chat_model || '—'}
                      </div>
                    </div>
                    {isActive && <Check size={13} strokeWidth={2} style={{ color: text.accent, flexShrink: 0 }} />}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
