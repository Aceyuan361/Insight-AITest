import { useLocation, useNavigate, Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Tabs } from '../../components/ui/tabs';
import { Smartphone, Globe, Construction } from 'lucide-react';
import { ModuleHelpButton } from '../../shared/components/ModuleHelpButton';

const WEB_TAB_KEYS = ['exec', 'edit', 'dashboard', 'batch', 'schedules', 'settings'] as const;

export function UIApp() {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const seg = location.pathname.split('/').filter(Boolean).pop() ?? 'exec';

  const tabLabelKey: Record<string, string> = {
    exec: 'ui.tabExec',
    edit: 'ui.tabEdit',
    dashboard: 'ui.tabDashboard',
    batch: 'ui.tabBatch',
    schedules: 'ui.tabSchedules',
    settings: 'ui.tabSettings',
  };
  const webTabs = WEB_TAB_KEYS.map((key) => ({ key, label: t(tabLabelKey[key]) }));

  // 顶层分组：web / mobile
  const isMobileSection = seg === 'mobile';
  const webTab = webTabs.some((t) => t.key === seg) ? seg : 'exec';

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: "var(--bg-base)", color: "var(--text-primary)" }}>
      {/* 顶层分组切换：Web / 移动端 */}
      <div style={{
        display: 'flex', gap: 0, padding: '4px 16px 0', alignItems: 'center',
        borderBottom: '1px solid var(--bg-card)',
      }}>
        <SectionButton
          active={!isMobileSection}
          onClick={() => navigate('exec', { replace: true })}
          icon={<Globe size={13} strokeWidth={1.5} />}
          label={t('ui.web')}
        />
        <SectionButton
          active={isMobileSection}
          onClick={() => navigate('mobile', { replace: true })}
          icon={<Smartphone size={13} strokeWidth={1.5} />}
          label={t('ui.mobile')}
        />
        <div style={{ flex: 1 }} />
        <ModuleHelpButton namespace="ui" />
      </div>

      {isMobileSection ? (
        <MobilePlaceholder />
      ) : (
        <>
          <Tabs tabs={webTabs} value={webTab} onChange={(k) => navigate(k, { replace: true })} />
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <Outlet />
          </div>
        </>
      )}
    </div>
  );
}

function SectionButton({ active, onClick, icon, label }: {
  active: boolean; onClick: () => void; icon: React.ReactNode; label: string;
}) {
  return (
    <button onClick={onClick} style={{
      background: active ? 'var(--surface-hover)' : 'transparent',
      border: 'none', borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
      color: active ? 'var(--text-primary)' : 'var(--text-muted)',
      padding: '6px 16px', cursor: 'pointer', fontSize: 13, fontWeight: active ? 600 : 400,
      display: 'inline-flex', alignItems: 'center', gap: 5, marginBottom: -1,
    }}>
      {icon}
      {label}
    </button>
  );
}

export function MobilePlaceholder() {
  const { t } = useTranslation();
  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      padding: 48, gap: 16,
    }}>
      <Construction size={48} strokeWidth={1} style={{ color: 'var(--chart-4)', opacity: 0.6 }} />
      <h2 style={{ fontSize: 18, color: "var(--text-primary)", margin: 0 }}>{t('ui.mobileTitle')}</h2>
      <p style={{ fontSize: 13, color: "var(--text-muted)", textAlign: 'center', maxWidth: 400, lineHeight: 1.6 }}>
        {t('ui.mobileComingSoonDesc')}
        <br />
        {t('ui.mobileAppiumDesc')}
      </p>
      <div style={{
        background: 'var(--bg-card)', borderRadius: 8, padding: 12, marginTop: 8,
        fontSize: 11, color: 'var(--text-muted)', maxWidth: 400, lineHeight: 1.5,
      }}>
        {t('ui.mobileArchHint')}
      </div>
    </div>
  );
}

export default UIApp;
