import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { TopBar } from './TopBar';
import { SideNav } from './SideNav';
import { ConfirmDialog } from '../shared/components/ConfirmDialog';
import { Toaster } from '@/components/ui/sonner';
import { useIsMobile } from '../shared/hooks/useIsMobile';
import type { ModuleManifest } from './types';

interface AppShellProps {
  modules: ModuleManifest[];
}

export function AppShell({ modules }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const isMobile = useIsMobile();
  // 移动端语义：collapsed=false → 抽屉打开；点击遮罩/导航后收起
  const drawerOpen = isMobile && !collapsed;

  const closeDrawer = () => {
    if (isMobile) setCollapsed(true);
  };

  return (
    <div
      style={{
        height: '100dvh',
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg-base)',
      }}
    >
      <TopBar onToggleSidebar={() => setCollapsed((c) => !c)} />
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <SideNav
          modules={modules}
          collapsed={collapsed}
          isMobile={isMobile}
          onNavigate={closeDrawer}
        />
        {/* 移动端抽屉背景遮罩 */}
        {drawerOpen && (
          <div
            onClick={closeDrawer}
            style={{
              position: 'fixed',
              inset: '60px 0 0 0',
              background: 'rgba(0,0,0,0.5)',
              zIndex: 40,
              transition: 'opacity 0.2s',
            }}
          />
        )}
        <main style={{ flex: 1, overflow: 'auto' }}>
          <Outlet />
        </main>
      </div>
      <ConfirmDialog />
      <Toaster />
    </div>
  );
}
