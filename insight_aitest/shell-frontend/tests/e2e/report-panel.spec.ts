import { test, expect } from '@playwright/test';

/**
 * Insight-AITest 基本访问测试
 * 只验证前后端基本连通性
 */

test('前后端基本访问正常', async ({ page, request }) => {
  // 1. 验证前端页面能访问
  await page.goto('/');
  await expect(page).toHaveTitle(/Insight-AITest/);

  // 2. 验证后端 API 能响应（平台健康端点，带版本号）
  const response = await request.get('http://localhost:8001/api/platform/health');
  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(body.status).toBe('healthy');
  expect(body.version).toBeTruthy();
});

test('API 自动化模块深链接可直达（回归：/api 代理前缀误吞 /api-runner）', async ({ page }) => {
  // vite 代理曾用字符串 '/api' 前缀匹配，把 /api-runner 页面路由也转发给后端导致 404 白屏；
  // 修复后深链接应返回 SPA 页面而非代理 404
  const resp = await page.goto('/api-runner/dashboard');
  expect(resp?.status()).toBe(200);
  await expect(page.locator('#root')).not.toBeEmpty();
  // AppShell 已渲染（顶栏品牌存在），且不是后端 404 JSON
  await expect(page.getByText('Insight-AITest').first()).toBeVisible();
});
