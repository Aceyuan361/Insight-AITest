import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright 配置文件
 * 用于 Insight-AITest 报告面板 E2E 测试
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false, // 报告面板测试顺序执行，避免竞争
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'playwright-results.json' }],
    ['junit', { outputFile: 'playwright-results.xml' }],
    ['list']
  ],
  use: {
    baseURL: process.env.CI ? 'http://localhost:4173' : 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15000,
    navigationTimeout: 30000,
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
      },
    },
  ],
  // CI 环境下自动启动后端 API 和前端预览服务器
  webServer: process.env.CI ? [
    {
      command: 'cd ../.. && python -m insight_aitest',
      port: 8001,
      timeout: 60000,
      reuseExistingServer: false,
    },
    {
      command: 'npm run preview',
      port: 4173,
      timeout: 120000,
      reuseExistingServer: false,
    },
  ] : undefined,
});
