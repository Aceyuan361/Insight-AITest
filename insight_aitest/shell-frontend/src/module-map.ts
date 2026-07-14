import { lazy, type ComponentType } from 'react';

const PerformanceApp = lazy(() =>
  import('./modules/performance').then((m) => ({ default: m.PerformanceApp })),
);
const ExampleApp = lazy(() =>
  import('./modules/example').then((m) => ({ default: m.ExampleApp })),
);
const AIApp = lazy(() =>
  import('./modules/ai').then((m) => ({ default: m.AIApp })),
);
const KnowledgeBaseApp = lazy(() =>
  import('./modules/kb').then((m) => ({ default: m.KnowledgeBaseApp })),
);
const TestCaseApp = lazy(() =>
  import('./modules/testcase').then((m) => ({ default: m.TestCaseApp })),
);
const ApiApp = lazy(() =>
  import('./modules/api').then((m) => ({ default: m.ApiApp })),
);
const UIApp = lazy(() =>
  import('./modules/ui').then((m) => ({ default: m.UIApp })),
);

// 静态模块映射表。每加一个模块在此加一行。
// key 格式：<模块id>:<导出名>，与 manifest 的 frontend.entry 一致。
export const moduleMap: Record<string, ComponentType> = {
  'performance:PerformanceApp': PerformanceApp,
  'example:ExampleApp': ExampleApp,
  'ai:AIApp': AIApp,
  'kb:KnowledgeBaseApp': KnowledgeBaseApp,
  'testcase:TestCaseApp': TestCaseApp,
  'api:ApiApp': ApiApp,
  'ui:UIApp': UIApp,
};

// 子路由映射。key = moduleId（与 manifest m.id 一致），value = { subPath: lazy 组件 }。
// 与 moduleMap 同模式 lazy 解析，子视图与根 App 同 chunk（同 barrel 导出）。
export const childrenMap: Record<string, Record<string, ComponentType>> = {
  ai: {
    agent: lazy(() => import('./modules/ai').then((m) => ({ default: m.AgentWorkbench }))),
  },
  api: {
    cases: lazy(() => import('./modules/api').then((m) => ({ default: m.CasesTab }))),
    suites: lazy(() => import('./modules/api').then((m) => ({ default: m.SuitesTab }))),
    envs: lazy(() => import('./modules/api').then((m) => ({ default: m.EnvironmentPanel }))),
    dashboard: lazy(() => import('./modules/api').then((m) => ({ default: m.Dashboard }))),
    schedules: lazy(() => import('./modules/api').then((m) => ({ default: m.SchedulePanel }))),
  },
  ui: {
    exec: lazy(() => import('./modules/ui').then((m) => ({ default: m.ExecTab }))),
    edit: lazy(() => import('./modules/ui').then((m) => ({ default: m.EditTab }))),
    dashboard: lazy(() => import('./modules/ui').then((m) => ({ default: m.Dashboard }))),
    batch: lazy(() => import('./modules/ui').then((m) => ({ default: m.BatchExec }))),
    schedules: lazy(() => import('./modules/ui').then((m) => ({ default: m.SchedulePanel }))),
    settings: lazy(() => import('./modules/ui').then((m) => ({ default: m.VisionConfig }))),
    mobile: lazy(() => import('./modules/ui').then((m) => ({ default: m.MobilePlaceholder }))),
  },
  testcase: {
    list: lazy(() => import('./modules/testcase').then((m) => ({ default: m.CaseEditor }))),
    generate: lazy(() => import('./modules/testcase').then((m) => ({ default: m.GenerateWizard }))),
    image: lazy(() => import('./modules/testcase').then((m) => ({ default: m.ImageGeneratePanel }))),
  },
};
