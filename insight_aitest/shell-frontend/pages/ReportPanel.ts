import { Page, Locator } from '@playwright/test';

/**
 * 报告面板页面对象
 * 封装报告面板的所有交互操作
 */
export class ReportPanel {
  readonly page: Page;
  readonly header: Locator;
  readonly titleLabel: Locator;
  readonly platformFilter: Locator;
  readonly searchInput: Locator;
  readonly refreshButton: Locator;
  readonly sessionList: Locator;
  readonly sessionDetail: Locator;

  constructor(page: Page) {
    this.page = page;
    this.header = page.locator('div').filter({ hasText: /^测试报告$/ }).first();
    this.titleLabel = page.getByText('测试报告', { exact: true });
    this.platformFilter = page.locator('select').filter({ hasText: '全部设备' });
    this.searchInput = page.locator('input[placeholder*="搜索包名或应用名"]');
    this.refreshButton = page.locator('button').filter({ hasText: '刷新' }).first();
    // 会话列表容器 - 使用更具体的选择器
    this.sessionList = page.locator('div').filter(async (el) => {
      const style = await el.evaluate(e => window.getComputedStyle(e).backgroundColor);
      const maxW = await el.evaluate(e => window.getComputedStyle(e).maxWidth);
      return style === 'rgb(18, 24, 36)' && maxW === '300px';
    }).first();
    // 会话详情区域
    this.sessionDetail = page.locator('div').filter(async (el) => {
      const classes = await el.getAttribute('class');
      return classes?.includes('h-full') && classes?.includes('overflow-hidden');
    }).nth(1);
  }

  /**
   * 等待报告面板加载完成
   */
  async waitForLoad() {
    await this.titleLabel.waitFor({ state: 'visible', timeout: 10000 });
    await this.platformFilter.waitFor({ state: 'visible', timeout: 5000 });
    await this.searchInput.waitFor({ state: 'visible', timeout: 5000 });
    await this.refreshButton.waitFor({ state: 'visible', timeout: 5000 });
  }

  /**
   * 获取当前选中的平台筛选
   */
  async getSelectedPlatform(): Promise<'all' | 'android' | 'ios'> {
    const value = await this.platformFilter.inputValue();
    return value as 'all' | 'android' | 'ios';
  }

  /**
   * 设置平台筛选
   */
  async setPlatformFilter(platform: 'all' | 'android' | 'ios') {
    await this.platformFilter.selectOption(platform);
    // 等待筛选生效
    await this.page.waitForTimeout(500);
  }

  /**
   * 输入搜索文本
   */
  async search(text: string) {
    await this.searchInput.clear();
    await this.searchInput.fill(text);
    // 等待搜索结果更新
    await this.page.waitForTimeout(500);
  }

  /**
   * 清空搜索
   */
  async clearSearch() {
    await this.searchInput.clear();
    await this.page.waitForTimeout(500);
  }

  /**
   * 点击刷新按钮
   */
  async refresh() {
    await this.refreshButton.click();
    // 等待刷新完成
    await this.page.waitForTimeout(1000);
  }

  /**
   * 获取会话列表中显示的会话数量
   */
  async getSessionCount(): Promise<number> {
    // 等待会话列表加载
    await this.page.waitForTimeout(1000);

    // 查找所有会话行
    const sessionRows = this.page.locator('div').filter(async (el) => {
      const text = await el.textContent();
      return text && /^#\d+$/.test(text.trim());
    });

    const count = await sessionRows.count();
    return count;
  }

  /**
   * 检查是否显示空状态
   */
  async isEmptyState(): Promise<boolean> {
    const emptyStateText = this.page.getByText('暂无会话记录');
    const isVisible = await emptyStateText.isVisible().catch(() => false);
    return isVisible;
  }

  /**
   * 点击指定索引的会话
   */
  async selectSession(index: number) {
    // 查找所有包含会话ID的元素
    const sessionElements = this.page.locator('span').filter(async (el) => {
      const text = await el.textContent();
      return text && /^#\d+$/.test(text.trim());
    });

    const count = await sessionElements.count();
    if (count === 0) {
      throw new Error('没有可用的会话');
    }

    if (index >= count) {
      throw new Error(`会话索引 ${index} 超出范围，总共只有 ${count} 个会话`);
    }

    await sessionElements.nth(index).click();
    // 等待详情加载
    await this.page.waitForTimeout(1000);
  }

  /**
   * 获取选中的会话ID
   */
  async getSelectedSessionId(): Promise<number | null> {
    // 查找被选中的会话行（蓝色背景）
    const selectedRow = this.page.locator('div').filter(async (el) => {
      const bgColor = await el.evaluate(e => window.getComputedStyle(e).backgroundColor);
      return bgColor === 'rgb(0, 212, 255)';
    }).first();

    const isVisible = await selectedRow.isVisible().catch(() => false);
    if (!isVisible) return null;

    // 从选中的行中提取会话ID
    const sessionIdText = await selectedRow.locator('span').filter(async (el) => {
      const text = await el.textContent();
      return text && /^#\d+$/.test(text.trim());
    }).first().textContent();

    if (sessionIdText) {
      return parseInt(sessionIdText.replace('#', ''), 10);
    }
    return null;
  }

  /**
   * 全选所有会话
   */
  async selectAllSessions() {
    // 查找表头的复选框
    const headerCheckbox = this.page.locator('input[type="checkbox"]').first();
    await headerCheckbox.check();
    await this.page.waitForTimeout(500);
  }

  /**
   * 获取选中的会话数量
   */
  async getSelectedSessionCount(): Promise<number> {
    // 查找被选中的复选框数量
    const checkedCheckboxes = this.page.locator('input[type="checkbox"]:checked');
    const count = await checkedCheckboxes.count();
    return count;
  }

  /**
   * 选中指定索引的会话复选框
   */
  async selectSessionCheckbox(index: number) {
    // 查找所有会话行的复选框（排除表头的）
    const checkboxes = this.page.locator('input[type="checkbox"]').nth(index + 1);
    await checkboxes.check();
    await this.page.waitForTimeout(500);
  }

  /**
   * 检查批量删除按钮是否可见
   */
  async isBatchDeleteButtonVisible(): Promise<boolean> {
    const batchDeleteBtn = this.page.locator('button').filter({ hasText: '批量删除' });
    return await batchDeleteBtn.isVisible().catch(() => false);
  }

  /**
   * 截图保存报告面板布局
   */
  async screenshotLayout(path: string) {
    await this.header.screenshot({ path });
  }

  /**
   * 截图保存完整页面
   */
  async screenshotFullPage(path: string) {
    await this.page.screenshot({
      path,
      fullPage: true
    });
  }
}
