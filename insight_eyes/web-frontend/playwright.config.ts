import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright 配置文件
 * 用于 Insight Eye 报告面板 E2E 测试
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
    baseURL: 'http://localhost:5173',
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
  // webServer 已禁用 - 需要手动启动开发服务器
  // 运行测试前请先执行: npm run dev
});
