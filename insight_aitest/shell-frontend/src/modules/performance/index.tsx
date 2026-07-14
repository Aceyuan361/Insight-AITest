import { lazy, Suspense } from 'react';

// 懒加载现有 MainWindow（性能模块主界面）
const MainWindow = lazy(() => import('./components/layout/MainWindow'));

/**
 * 性能模块前端入口。由平台 module-map 引用，挂载在 /performance 路由。
 */
export function PerformanceApp() {
  return (
    <Suspense fallback={<div style={{ padding: 24 }}>加载性能模块…</div>}>
      <MainWindow />
    </Suspense>
  );
}

export default PerformanceApp;
