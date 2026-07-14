import { useLocation, useNavigate, Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Tabs } from '../../components/ui/tabs';
import { ModuleHelpButton } from '../../shared/components/ModuleHelpButton';

const TAB_KEYS = ['cases', 'suites', 'envs', 'dashboard', 'schedules'] as const;

export function ApiApp() {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const TABS = [
    { key: 'cases', label: t('api.tabCases') },
    { key: 'suites', label: t('api.tabSuites') },
    { key: 'envs', label: t('api.tabEnvs') },
    { key: 'dashboard', label: t('api.tabDashboard') },
    { key: 'schedules', label: t('api.tabSchedules') },
  ];
  // 当前 tab 从 URL 末段派生
  const seg = location.pathname.split('/').filter(Boolean).pop() ?? 'cases';
  const tab = TAB_KEYS.includes(seg as typeof TAB_KEYS[number]) ? seg : 'cases';
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: "var(--bg-base)", color: "var(--text-primary)" }}>
      <div style={{ display: 'flex', alignItems: 'center', borderBottom: '1px solid var(--bg-card)' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Tabs tabs={TABS} value={tab} onChange={(k) => navigate(k, { replace: true })} />
        </div>
        <div style={{ flexShrink: 0, paddingRight: 12 }}>
          <ModuleHelpButton namespace="api" />
        </div>
      </div>
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <Outlet />
      </div>
    </div>
  );
}

export default ApiApp;
