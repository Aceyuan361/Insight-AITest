import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Menu, X } from 'lucide-react';
import { platformIcons } from './icons';
import { SettingsPanel } from '../modules/ai/components/SettingsPanel';
import { ProjectSelector } from './ProjectSelector';
import { useIsMobile } from '../shared/hooks/useIsMobile';
import LanguageSwitcher from '../shared/components/LanguageSwitcher';

interface TopBarProps {
  onToggleSidebar: () => void;
}

export function TopBar({ onToggleSidebar }: TopBarProps) {
  const { t } = useTranslation();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const isMobile = useIsMobile();

  return (
    <>
      <header
        style={{
          height: 60,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          background: "var(--bg-base)",
          borderBottom: '1px solid var(--bg-card)',
          color: "var(--text-primary)",
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            onClick={onToggleSidebar}
            style={{
              background: 'none',
              border: 'none',
              color: "var(--text-primary)",
              cursor: 'pointer',
              fontSize: 18,
              ...(isMobile ? { minWidth: 44, minHeight: 44, display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 4 } : {}),
            }}
            aria-label={t('topbar.toggleSidebar')}
          >
            <Menu size={18} strokeWidth={1.5} />
          </button>
          <strong>Insight-AITest 平台</strong>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <ProjectSelector />
          <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>v2.0.0</span>
          <LanguageSwitcher />
          <button
            onClick={() => setSettingsOpen(true)}
            title={t('topbar.modelAndPlatformSettings')}
            style={{
              background: 'none',
              border: 'none',
              color: settingsOpen ? "var(--accent)" : "var(--text-secondary)",
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              padding: 4,
              ...(isMobile ? { minWidth: 44, minHeight: 44, justifyContent: 'center', borderRadius: 4 } : {}),
            }}
            aria-label={t('topbar.settings')}
          >
            <platformIcons.Settings size={18} />
          </button>
        </div>
      </header>

      {settingsOpen && (
        <div
          onClick={() => setSettingsOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.6)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'center',
            paddingTop: 40,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: 'min(640px, 92vw)',
              maxHeight: '85vh',
              background: "var(--bg-base)",
              border: '1px solid var(--bg-elevated)',
              borderRadius: 10,
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 20px',
                borderBottom: '1px solid var(--bg-card)',
                flexShrink: 0,
              }}
            >
              <strong style={{ color: "var(--text-primary)", fontSize: 14 }}>{t('topbar.platformSettings')}</strong>
              <button
                onClick={() => setSettingsOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: "var(--text-secondary)",
                  cursor: 'pointer',
                  fontSize: 18,
                }}
                aria-label={t('common.close')}
              >
                <X size={16} strokeWidth={1.5} />
              </button>
            </div>
            <div style={{ overflow: 'auto' }}>
              <SettingsPanel />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
