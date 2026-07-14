import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Package, Check, X } from 'lucide-react';
import { moduleIcons } from './icons';
import type { ModuleManifest } from './types';

interface DashboardProps {
  modules: ModuleManifest[];
}

const RECENT_KEY = 'insight-eye-recent-modules';
const RECENT_MAX = 4;

function readRecent(): string[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
  } catch {
    return [];
  }
}

function pushRecent(id: string) {
  const cur = readRecent().filter((x) => x !== id);
  cur.unshift(id);
  localStorage.setItem(RECENT_KEY, JSON.stringify(cur.slice(0, RECENT_MAX)));
}

export function Dashboard({ modules }: DashboardProps) {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);
  const recent = readRecent();

  const moduleName = (m: ModuleManifest) =>
    i18n.language === 'en-US' ? (m.name.en ?? m.name.zh ?? m.id) : (m.name.zh ?? m.name.en ?? m.id);
  const moduleDesc = (m: ModuleManifest) =>
    i18n.language === 'en-US' ? (m.description.en ?? m.description.zh ?? '') : (m.description.zh ?? m.description.en ?? '');

  useEffect(() => {
    fetch('/api/platform/health')
      .then((r) => setBackendHealthy(r.ok))
      .catch(() => setBackendHealthy(false));
  }, []);

  const dashboardModules = modules
    .filter((m) => m.frontend?.nav.show_in_dashboard)
    .sort((a, b) => a.order - b.order);

  const cardStyle: React.CSSProperties = {
    textAlign: 'left',
    background: "var(--bg-card)",
    border: '1px solid var(--bg-card)',
    borderRadius: 8,
    padding: 20,
    cursor: 'pointer',
    color: "var(--text-primary)",
  };
  const chipStyle: React.CSSProperties = {
    background: "var(--bg-card)",
    border: '1px solid var(--bg-elevated)',
    borderRadius: 4,
    padding: '4px 10px',
    color: 'var(--text-muted)',
    cursor: 'pointer',
  };

  return (
    <div style={{ padding: 24, color: "var(--text-primary)" }}>
      <h1 style={{ marginBottom: 4 }}>Insight-AITest {i18n.language === 'en-US' ? 'Platform' : '平台'}</h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>{t('dashboard.versionTag')}</p>

      {recent.length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <h3 style={{ color: "var(--accent)" }}>{t('dashboard.recentModules')}</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {recent.map((id) => {
              const m = modules.find((x) => x.id === id);
              if (!m?.frontend) return null;
              return (
                <button
                  key={id}
                  onClick={() => navigate(m.frontend!.route)}
                  style={chipStyle}
                >
                  {moduleName(m)}
                </button>
              );
            })}
          </div>
        </section>
      )}

      <section>
        <h3 style={{ color: "var(--accent)" }}>{t('dashboard.allModules')}</h3>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: 16,
          }}
        >
          {dashboardModules.map((m) => {
            const Icon = moduleIcons[m.icon];
            return (
              <button
                key={m.id}
                onClick={() => {
                  pushRecent(m.id);
                  navigate(m.frontend!.route);
                }}
                style={cardStyle}
              >
                <div style={{ fontSize: 28, marginBottom: 8 }}>
                  {Icon ? <Icon size={28} /> : <Package size={28} strokeWidth={1.5} />}
                </div>
                <div style={{ fontWeight: 600 }}>{moduleName(m)}</div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
                  {moduleDesc(m)}
                </div>
              </button>
            );
          })}
        </div>
      </section>

      <section style={{ marginTop: 32, fontSize: 12, color: "var(--text-muted)" }}>
        {i18n.language === 'en-US' ? 'Backend status: ' : '后端状态：'}
        {backendHealthy === null ? (i18n.language === 'en-US' ? 'Checking…' : '检测中…') : (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            {backendHealthy
              ? <><Check size={12} strokeWidth={1.5} /> {i18n.language === 'en-US' ? 'Healthy' : '正常'}</>
              : <><X size={12} strokeWidth={1.5} /> {i18n.language === 'en-US' ? 'Unreachable' : '不可达'}</>}
          </span>
        )}
        {i18n.language === 'en-US' ? ' · Loaded modules: ' : ' · 已加载模块：'}
        {modules.length}
      </section>
    </div>
  );
}
