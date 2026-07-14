import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { moduleIcons, platformIcons } from './icons';
import type { ModuleManifest } from './types';
import type { ComponentType } from 'react';

interface SideNavProps {
  modules: ModuleManifest[];
  collapsed: boolean;
  isMobile?: boolean;
  onNavigate?: () => void;
}

// 分组渲染顺序
const CATEGORY_ORDER = ['agent', 'assets', 'testing', 'ai', 'infra'];

export function SideNav({ modules, collapsed, isMobile, onNavigate }: SideNavProps) {
  const { t, i18n } = useTranslation();
  // 分组标题。agent 组无标题（直接放顶部），其余组显示标题。
  const CATEGORY_LABELS: Record<string, string> = {
    agent: '',
    assets: t('nav.assets'),
    testing: t('nav.capabilities'),
    ai: t('nav.aiGroup'),
    infra: t('nav.infrastructure'),
  };

  // 当前语言的模块名
  const moduleName = (m: ModuleManifest) => {
    if (i18n.language === 'en-US') return m.name.en ?? m.name.zh ?? m.id;
    return m.name.zh ?? m.name.en ?? m.id;
  };

  // 移动端：覆盖式抽屉（fixed，280 宽，避 TopBar 60px）；桌面：原 200↔0 in-flow
  const width = isMobile ? 280 : collapsed ? 0 : 200;

  const grouped = modules.reduce<Record<string, ModuleManifest[]>>((acc, m) => {
    (acc[m.category] ??= []).push(m);
    return acc;
  }, {});

  // 移动端与桌面：collapsed=true 时不渲染内容
  const hidden = collapsed;

  return (
    <nav
      style={{
        width,
        minWidth: collapsed && !isMobile ? 0 : 200,
        background: 'var(--bg-base)',
        borderRight: '1px solid var(--bg-card)',
        overflow: 'hidden',
        transition: 'width 0.2s',
        padding: hidden ? 0 : '12px 0',
        flexShrink: 0,
        ...(isMobile
          ? {
              position: 'fixed',
              top: 60,
              bottom: 0,
              left: 0,
              zIndex: 50,
              boxShadow: '2px 0 12px rgba(0,0,0,0.4)',
            }
          : {}),
      }}
    >
      {hidden ? null : (
        <>
          {/* Agent 为核心：直接放顶部，无分组标题 */}
          {(grouped['agent'] ?? [])
            .filter((m) => m.frontend)
            .sort((a, b) => a.order - b.order)
            .map((m) => {
              const Icon = moduleIcons[m.icon];
              return (
                <NavItem
                  key={m.id}
                  to={m.frontend!.route}
                  icon={Icon}
                  label={moduleName(m)}
                  isMobile={isMobile}
                  onNavigate={onNavigate}
                />
              );
            })}

          {/* 平台级：首页 + 总览 */}
          <div style={{ marginTop: 16 }}>
            <NavItem to="/" icon={platformIcons.Home} label={t('nav.home')} end isMobile={isMobile} onNavigate={onNavigate} />
            <NavItem to="/overview" icon={platformIcons.Overview} label={t('nav.overview')} isMobile={isMobile} onNavigate={onNavigate} />
          </div>

          {/* 其余分组（按 CATEGORY_ORDER 渲染） */}
          {CATEGORY_ORDER.filter((cat) => cat !== 'agent').map((cat) => {
            const mods = (grouped[cat] ?? []).filter((m) => m.frontend);
            if (mods.length === 0) return null;
            return (
              <div key={cat} style={{ marginTop: 16 }}>
                <div
                  style={{
                    padding: isMobile ? '6px 20px' : '4px 16px',
                    fontSize: 11,
                    color: 'var(--text-muted)',
                    textTransform: 'uppercase',
                  }}
                >
                  {CATEGORY_LABELS[cat] ?? cat}
                </div>
                {mods
                  .sort((a, b) => a.order - b.order)
                  .map((m) => {
                    const Icon = moduleIcons[m.icon];
                    return (
                      <NavItem
                        key={m.id}
                        to={m.frontend!.route}
                        icon={Icon}
                        label={moduleName(m)}
                        isMobile={isMobile}
                        onNavigate={onNavigate}
                      />
                    );
                  })}
              </div>
            );
          })}

          {/* 项目管理（平台级页面） */}
          <div style={{ marginTop: 16 }}>
            <NavItem to="/projects" icon={platformIcons.FolderKanban} label={t('nav.projectManagement')} isMobile={isMobile} onNavigate={onNavigate} />
          </div>
        </>
      )}
    </nav>
  );
}

function NavItem({
  to,
  icon: Icon,
  label,
  end,
  isMobile,
  onNavigate,
}: {
  to: string;
  icon?: ComponentType<{ size?: number }>;
  label: string;
  end?: boolean;
  isMobile?: boolean;
  onNavigate?: () => void;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      style={({ isActive }) => ({
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: isMobile ? '14px 20px' : '8px 16px',
        color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
        textDecoration: 'none',
        fontSize: 14,
        minHeight: isMobile ? 48 : undefined, // 触控目标 ≥44px
        background: isActive ? 'rgba(16,185,129,0.08)' : 'transparent',
        borderLeft: isActive ? '2px solid var(--accent)' : '2px solid transparent',
      })}
    >
      {Icon ? <Icon size={16} /> : null}
      {label}
    </NavLink>
  );
}
