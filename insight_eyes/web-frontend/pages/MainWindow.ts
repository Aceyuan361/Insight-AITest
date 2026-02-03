import { Page, Locator } from '@playwright/test';

/**
 * 主窗口页面对象
 * 封装主窗口的通用操作
 */
export class MainWindow {
  readonly page: Page;
  readonly reportTab: Locator;
  readonly monitorTab: Locator;
  readonly menuBar: Locator;

  constructor(page: Page) {
    this.page = page;
    this.reportTab = page.getByText('性能报告', { exact: true });
    this.monitorTab = page.getByText('实时监控', { exact: true });
    this.menuBar = page.locator('nav').filter({ hasText: '性能监控工具' });
  }

  /**
   * 导航到应用
   */
  async goto() {
    await this.page.goto('/');
    // 等待应用加载
    await this.menuBar.waitFor({ state: 'visible', timeout: 10000 });
  }

  /**
   * 切换到性能报告标签页
   */
  async goToReportTab() {
    await this.reportTab.click();
    // 验证标签页已激活
    await expect(this.reportTab).toHaveCSS('border-bottom-color', 'rgb(0, 212, 255)');
  }

  /**
   * 切换到实时监控标签页
   */
  async goToMonitorTab() {
    await this.monitorTab.click();
    // 验证标签页已激活
    await expect(this.monitorTab).toHaveCSS('border-bottom-color', 'rgb(0, 212, 255)');
  }

  /**
   * 获取当前活动的标签页
   */
  async getActiveTab(): Promise<'monitor' | 'report'> {
    const reportBorder = await this.reportTab.evaluate(el =>
      window.getComputedStyle(el).borderBottomColor
    );
    return reportBorder === 'rgb(0, 212, 255)' ? 'report' : 'monitor';
  }
}

// 导出 expect 以便在测试中使用
import { expect as playwrightExpect } from '@playwright/test';
export const expect = playwrightExpect;
