import { test, expect } from '@playwright/test';

/**
 * Insight-AITest 基本访问测试
 * 只验证前后端基本连通性
 */

test('前后端基本访问正常', async ({ page, request }) => {
  // 1. 验证前端页面能访问
  await page.goto('/');
  await expect(page).toHaveTitle(/Insight-AITest/);

  // 2. 验证后端 API 能响应
  const response = await request.get('http://localhost:8001/health');
  expect(response.status()).toBe(200);
});
