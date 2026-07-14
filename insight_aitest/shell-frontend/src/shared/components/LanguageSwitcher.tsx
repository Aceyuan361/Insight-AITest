/**
 * 全局语言切换组件（TopBar 用）。
 * 支持中文 / 英文切换，沿用 i18n.changeLanguage + localStorage('language') 持久化。
 *
 * 紧凑图标按钮风格，适配 TopBar 右侧集群。
 */
import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';
import { useIsMobile } from '../hooks/useIsMobile';

export default function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const isMobile = useIsMobile();

  // 点击外部关闭下拉
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const currentLabel = i18n.language === 'en-US' ? 'EN' : '中';

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen((v) => !v)}
        title={t('common.language')}
        style={{
          background: 'none', border: 'none',
          color: open ? 'var(--accent)' : 'var(--text-secondary)',
          cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
          padding: 4, fontSize: 13,
          ...(isMobile ? { minWidth: 44, minHeight: 44, justifyContent: 'center', borderRadius: 4 } : {}),
        }}
        aria-label={t('common.language')}
      >
        <Globe size={18} strokeWidth={1.5} />
        {!isMobile && <span style={{ fontSize: 12 }}>{currentLabel}</span>}
      </button>
      {open && (
        <div
          style={{
            position: 'absolute', top: '100%', right: 0, marginTop: 4,
            background: 'var(--bg-elevated)', border: '1px solid var(--border-strong)',
            borderRadius: 6, boxShadow: 'var(--shadow-elevated)', zIndex: 1100,
            minWidth: 120, overflow: 'hidden',
          }}
        >
          {(['zh-CN', 'en-US'] as const).map((lng) => (
            <button
              key={lng}
              onClick={() => { i18n.changeLanguage(lng); setOpen(false); }}
              style={{
                display: 'block', width: '100%', textAlign: 'left',
                padding: '8px 14px', fontSize: 13, cursor: 'pointer',
                background: i18n.language === lng ? 'var(--accent-deep)' : 'none',
                color: i18n.language === lng ? 'var(--accent)' : 'var(--text-primary)',
                border: 'none', borderBottom: '1px solid var(--border)',
              }}
            >
              {lng === 'zh-CN' ? '简体中文' : 'English'}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
