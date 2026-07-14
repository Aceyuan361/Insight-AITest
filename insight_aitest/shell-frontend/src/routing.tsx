import { createElement, type ReactNode } from 'react';
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import { AppShell } from './shell/AppShell';
import { Dashboard } from './shell/Dashboard';
import { DashboardOverview } from './shell/DashboardOverview';
import { ProjectsPage } from './shell/ProjectsPage';
import { PlatformError } from './shell/PlatformError';
import { MissingModule } from './shell/MissingModule';
import { moduleMap, childrenMap } from './module-map';
import type { ModuleManifest } from './shell/types';

export function PlatformRouter({ modules }: { modules: ModuleManifest[] }): ReactNode {
  const moduleRoutes = modules
    .filter((m) => m.frontend)
    .map((m) => {
      const entry = resolveEntry(m.frontend!.entry);
      const children = childrenMap[m.id];
      if (!children) {
        return { path: m.frontend!.route, element: entry };
      }
      // 嵌套：根路径重定向到默认子视图（childrenMap 声明顺序第一个）+ 每个子 path 一个路由
      const defaultSub = Object.keys(children)[0];
      return {
        path: m.frontend!.route,
        element: entry,
        children: [
          { index: true, element: <Navigate to={defaultSub} replace /> },
          ...Object.entries(children).map(([subPath, Comp]) => ({
            path: subPath,
            element: createElement(Comp),
          })),
        ],
      };
    });

  const router = createBrowserRouter([
    {
      path: '/',
      element: <AppShell modules={modules} />,
      errorElement: <PlatformError />,
      children: [
        { index: true, element: <Dashboard modules={modules} /> },
        { path: 'overview', element: <DashboardOverview /> },
        { path: 'projects', element: <ProjectsPage /> },
        ...moduleRoutes,
      ],
    },
  ]);

  return <RouterProvider router={router} />;
}

function resolveEntry(entry: string) {
  const Comp = moduleMap[entry];
  if (!Comp) return <MissingModule entry={entry} />;
  return createElement(Comp);
}
