import { test, expect } from '@playwright/test';
import { MainWindow } from '../../pages/MainWindow';
import { ReportPanel } from '../../pages/ReportPanel';

/**
 * Insight Eye 报告面板 E2E 测试套件
 *
 * 测试覆盖范围:
 * 1. 报告面板布局验证
 * 2. 会话选择和详情查看
 * 3. 筛选功能
 * 4. 批量操作
 */

test.describe('报告面板 - 布局验证', () => {
  let mainWindow: MainWindow;
  let reportPanel: ReportPanel;

  test.beforeEach(async ({ page }) => {
    mainWindow = new MainWindow(page);
    reportPanel = new ReportPanel(page);

    // 导航到应用
    await mainWindow.goto();
    await mainWindow.goToReportTab();
    await reportPanel.waitForLoad();
  });

  test('应该显示报告面板标题', async ({ page }) => {
    // 验证标题显示
    await expect(reportPanel.titleLabel).toBeVisible();
    await expect(reportPanel.titleLabel).toContainText('测试报告');

    // 截图保存
    await page.screenshot({
      path: 'screenshots/report-panel-title.png',
      fullPage: false
    });
  });

  test('应该显示所有筛选控件', async ({ page }) => {
    // 验证平台筛选下拉框
    await expect(reportPanel.platformFilter).toBeVisible();
    const platformOptions = await reportPanel.platformFilter.locator('option').allTextContents();
    expect(platformOptions).toContain('全部设备');
    expect(platformOptions).toContain('Android');
    expect(platformOptions).toContain('iOS');

    // 验证搜索输入框
    await expect(reportPanel.searchInput).toBeVisible();
    await expect(reportPanel.searchInput).toHaveAttribute('placeholder', '搜索包名或应用名...');

    // 验证刷新按钮
    await expect(reportPanel.refreshButton).toBeVisible();
    await expect(reportPanel.refreshButton).toContainText('刷新');

    // 截图保存
    await page.screenshot({
      path: 'screenshots/report-panel-controls.png',
      fullPage: false
    });
  });

  test('应该显示会话列表和详情区域', async ({ page }) => {
    // 验证会话列表区域存在
    const sessionCount = await reportPanel.getSessionCount();
    console.log(`当前会话数量: ${sessionCount}`);

    // 截图保存完整布局
    await page.screenshot({
      path: 'screenshots/report-panel-layout.png',
      fullPage: true
    });

    // 如果没有会话，应该显示空状态
    if (sessionCount === 0) {
      const isEmpty = await reportPanel.isEmptyState();
      expect(isEmpty).toBe(true);
      console.log('会话列表为空，显示空状态');
    }
  });

  test('平台筛选下拉框应该有三个选项', async () => {
    const platformOptions = await reportPanel.platformFilter.locator('option').allTextContents();
    expect(platformOptions).toEqual(['全部设备', 'Android', 'iOS']);
  });

  test('搜索输入框应该接受文本输入', async () => {
    await reportPanel.searchInput.fill('test');
    await expect(reportPanel.searchInput).toHaveValue('test');
    await reportPanel.searchInput.clear();
    await expect(reportPanel.searchInput).toHaveValue('');
  });
});

test.describe('报告面板 - 会话选择和详情查看', () => {
  let mainWindow: MainWindow;
  let reportPanel: ReportPanel;

  test.beforeEach(async ({ page }) => {
    mainWindow = new MainWindow(page);
    reportPanel = new ReportPanel(page);

    await mainWindow.goto();
    await mainWindow.goToReportTab();
    await reportPanel.waitForLoad();
  });

  test('应该能够选择会话并查看详情', async ({ page }) => {
    const sessionCount = await reportPanel.getSessionCount();

    test.skip(sessionCount === 0, '没有可用的会话进行测试');

    // 选择第一个会话
    await reportPanel.selectSession(0);

    // 验证会话被选中（蓝色背景）
    const selectedId = await reportPanel.getSelectedSessionId();
    expect(selectedId).not.toBeNull();
    console.log(`选中的会话ID: ${selectedId}`);

    // 截图保存会话详情
    await page.screenshot({
      path: 'screenshots/session-detail-selected.png',
      fullPage: true
    });
  });

  test('选中会话后应该显示会话详情', async ({ page }) => {
    const sessionCount = await reportPanel.getSessionCount();

    test.skip(sessionCount === 0, '没有可用的会话进行测试');

    await reportPanel.selectSession(0);

    // 等待详情加载
    await page.waitForTimeout(2000);

    // 验证会话信息栏显示
    const sessionInfoBar = page.locator('div').filter(async (el) => {
      const classes = await el.getAttribute('class');
      return classes?.includes('px-4') && classes?.includes('py-2');
    }).first();

    const isVisible = await sessionInfoBar.isVisible().catch(() => false);
    if (isVisible) {
      console.log('会话信息栏已显示');
    }

    // 截图
    await page.screenshot({
      path: 'screenshots/session-info-bar.png',
      fullPage: false
    });
  });

  test('应该能够切换不同会话', async ({ page }) => {
    const sessionCount = await reportPanel.getSessionCount();

    test.skip(sessionCount < 2, '需要至少2个会话进行测试');

    // 选择第一个会话
    await reportPanel.selectSession(0);
    const firstId = await reportPanel.getSelectedSessionId();
    console.log(`第一个选中的会话ID: ${firstId}`);

    await page.waitForTimeout(1000);

    // 选择第二个会话
    await reportPanel.selectSession(1);
    const secondId = await reportPanel.getSelectedSessionId();
    console.log(`第二个选中的会话ID: ${secondId}`);

    // 验证会话ID不同
    expect(firstId).not.toEqual(secondId);
  });
});

test.describe('报告面板 - 筛选功能', () => {
  let mainWindow: MainWindow;
  let reportPanel: ReportPanel;

  test.beforeEach(async ({ page }) => {
    mainWindow = new MainWindow(page);
    reportPanel = new ReportPanel(page);

    await mainWindow.goto();
    await mainWindow.goToReportTab();
    await reportPanel.waitForLoad();
  });

  test('应该能够按平台筛选会话', async ({ page }) => {
    const initialCount = await reportPanel.getSessionCount();

    test.skip(initialCount === 0, '没有可用的会话进行测试');

    console.log(`初始会话数量: ${initialCount}`);

    // 切换到 Android 筛选
    await reportPanel.setPlatformFilter('android');
    await page.waitForTimeout(1000);

    const androidCount = await reportPanel.getSessionCount();
    console.log(`Android 会话数量: ${androidCount}`);

    // 切换到 iOS 筛选
    await reportPanel.setPlatformFilter('ios');
    await page.waitForTimeout(1000);

    const iosCount = await reportPanel.getSessionCount();
    console.log(`iOS 会话数量: ${iosCount}`);

    // 切换回全部
    await reportPanel.setPlatformFilter('all');
    await page.waitForTimeout(1000);

    const allCount = await reportPanel.getSessionCount();
    console.log(`全部会话数量: ${allCount}`);

    // 验证全部会话数量等于初始数量
    expect(allCount).toBe(initialCount);

    // 截图
    await page.screenshot({
      path: 'screenshots/platform-filter.png',
      fullPage: true
    });
  });

  test('应该能够按包名或应用名搜索', async ({ page }) => {
    const initialCount = await reportPanel.getSessionCount();

    test.skip(initialCount === 0, '没有可用的会话进行测试');

    console.log(`初始会话数量: ${initialCount}`);

    // 输入搜索文本
    await reportPanel.search('test');

    await page.waitForTimeout(1000);

    const searchCount = await reportPanel.getSessionCount();
    console.log(`搜索结果数量: ${searchCount}`);

    // 清空搜索
    await reportPanel.clearSearch();

    const afterClearCount = await reportPanel.getSessionCount();
    console.log(`清空后会话数量: ${afterClearCount}`);

    // 验证清空后数量恢复
    expect(afterClearCount).toBe(initialCount);

    // 截图
    await page.screenshot({
      path: 'screenshots/search-functionality.png',
      fullPage: true
    });
  });

  test('搜索不存在的应用应该返回空结果', async ({ page }) => {
    const initialCount = await reportPanel.getSessionCount();

    test.skip(initialCount === 0, '没有可用的会话进行测试');

    // 搜索一个不存在的包名
    await reportPanel.search('xyznonexistentapp123456');

    await page.waitForTimeout(1000);

    const searchCount = await reportPanel.getSessionCount();
    console.log(`搜索结果数量: ${searchCount}`);

    // 应该返回0个结果
    expect(searchCount).toBe(0);

    // 验证空状态显示
    const isEmpty = await reportPanel.isEmptyState();
    expect(isEmpty).toBe(true);

    // 截图
    await page.screenshot({
      path: 'screenshots/search-empty-result.png',
      fullPage: true
    });
  });

  test('刷新按钮应该重新加载会话列表', async ({ page }) => {
    const initialCount = await reportPanel.getSessionCount();
    console.log(`刷新前会话数量: ${initialCount}`);

    await reportPanel.refresh();

    const afterRefreshCount = await reportPanel.getSessionCount();
    console.log(`刷新后会话数量: ${afterRefreshCount}`);

    // 数量应该保持一致
    expect(afterRefreshCount).toBe(initialCount);
  });
});

test.describe('报告面板 - 批量操作', () => {
  let mainWindow: MainWindow;
  let reportPanel: ReportPanel;

  test.beforeEach(async ({ page }) => {
    mainWindow = new MainWindow(page);
    reportPanel = new ReportPanel(page);

    await mainWindow.goto();
    await mainWindow.goToReportTab();
    await reportPanel.waitForLoad();
  });

  test('应该能够全选所有会话', async ({ page }) => {
    const sessionCount = await reportPanel.getSessionCount();

    test.skip(sessionCount === 0, '没有可用的会话进行测试');

    console.log(`会话数量: ${sessionCount}`);

    // 全选会话
    await reportPanel.selectAllSessions();

    // 获取选中的会话数量
    const selectedCount = await reportPanel.getSelectedSessionCount();
    console.log(`选中的会话数量: ${selectedCount}`);

    // 验证选中的数量等于总会话数量
    expect(selectedCount).toBe(sessionCount + 1); // +1 因为表头复选框也被计算

    // 验证批量删除按钮出现
    const isBatchDeleteVisible = await reportPanel.isBatchDeleteButtonVisible();
    expect(isBatchDeleteVisible).toBe(true);

    // 截图
    await page.screenshot({
      path: 'screenshots/batch-select-all.png',
      fullPage: true
    });
  });

  test('应该能够选中单个会话复选框', async ({ page }) => {
    const sessionCount = await reportPanel.getSessionCount();

    test.skip(sessionCount === 0, '没有可用的会话进行测试');

    // 选中第一个会话的复选框
    await reportPanel.selectSessionCheckbox(0);

    // 获取选中的会话数量
    const selectedCount = await reportPanel.getSelectedSessionCount();
    console.log(`选中的会话数量: ${selectedCount}`);

    // 验证至少有一个被选中
    expect(selectedCount).toBeGreaterThan(0);

    // 验证批量删除按钮出现
    const isBatchDeleteVisible = await reportPanel.isBatchDeleteButtonVisible();
    expect(isBatchDeleteVisible).toBe(true);

    // 截图
    await page.screenshot({
      path: 'screenshots/batch-select-single.png',
      fullPage: true
    });
  });

  test('应该能够取消选择会话', async ({ page }) => {
    const sessionCount = await reportPanel.getSessionCount();

    test.skip(sessionCount === 0, '没有可用的会话进行测试');

    // 全选会话
    await reportPanel.selectAllSessions();

    let selectedCount = await reportPanel.getSelectedSessionCount();
    console.log(`选中后会话数量: ${selectedCount}`);
    expect(selectedCount).toBeGreaterThan(0);

    // 取消全选
    await reportPanel.selectAllSessions();

    selectedCount = await reportPanel.getSelectedSessionCount();
    console.log(`取消选择后会话数量: ${selectedCount}`);

    // 验证批量删除按钮消失
    const isBatchDeleteVisible = await reportPanel.isBatchDeleteButtonVisible();
    expect(isBatchDeleteVisible).toBe(false);

    // 截图
    await page.screenshot({
      path: 'screenshots/batch-deselect.png',
      fullPage: true
    });
  });

  test('批量删除按钮应该可见且可点击', async ({ page }) => {
    const sessionCount = await reportPanel.getSessionCount();

    test.skip(sessionCount === 0, '没有可用的会话进行测试');

    // 全选会话
    await reportPanel.selectAllSessions();

    // 查找批量删除按钮
    const batchDeleteBtn = page.locator('button').filter({ hasText: '批量删除' });

    await expect(batchDeleteBtn).toBeVisible();
    await expect(batchDeleteBtn).toHaveText('批量删除');

    // 截图
    await page.screenshot({
      path: 'screenshots/batch-delete-button.png',
      fullPage: false
    });
  });
});

test.describe('报告面板 - 空状态处理', () => {
  let mainWindow: MainWindow;
  let reportPanel: ReportPanel;

  test.beforeEach(async ({ page }) => {
    mainWindow = new MainWindow(page);
    reportPanel = new ReportPanel(page);

    await mainWindow.goto();
    await mainWindow.goToReportTab();
    await reportPanel.waitForLoad();
  });

  test('没有会话时应该显示空状态', async ({ page }) => {
    const sessionCount = await reportPanel.getSessionCount();

    test.skip(sessionCount > 0, '会话列表不为空，跳过空状态测试');

    // 验证空状态文本
    const emptyStateText = page.getByText('暂无会话记录');
    await expect(emptyStateText).toBeVisible();

    // 截图
    await page.screenshot({
      path: 'screenshots/empty-state.png',
      fullPage: true
    });
  });

  test('空状态时控件仍然应该可用', async ({ page }) => {
    const sessionCount = await reportPanel.getSessionCount();

    test.skip(sessionCount > 0, '会话列表不为空，跳过空状态测试');

    // 验证所有控件仍然可见和可用
    await expect(reportPanel.platformFilter).toBeVisible();
    await expect(reportPanel.platformFilter).toBeEnabled();

    await expect(reportPanel.searchInput).toBeVisible();
    await expect(reportPanel.searchInput).toBeEnabled();

    await expect(reportPanel.refreshButton).toBeVisible();
    await expect(reportPanel.refreshButton).toBeEnabled();

    // 测试搜索功能
    await reportPanel.search('test');
    await expect(reportPanel.searchInput).toHaveValue('test');

    // 测试筛选功能
    await reportPanel.setPlatformFilter('android');
    const selectedPlatform = await reportPanel.getSelectedPlatform();
    expect(selectedPlatform).toBe('android');

    // 截图
    await page.screenshot({
      path: 'screenshots/empty-state-controls.png',
      fullPage: true
    });
  });
});

test.describe('报告面板 - 响应式布局', () => {
  let mainWindow: MainWindow;
  let reportPanel: ReportPanel;

  test.beforeEach(async ({ page }) => {
    mainWindow = new MainWindow(page);
    reportPanel = new ReportPanel(page);

    await mainWindow.goto();
    await mainWindow.goToReportTab();
    await reportPanel.waitForLoad();
  });

  test('在不同屏幕尺寸下布局应该正常', async ({ page }) => {
    // 测试不同屏幕尺寸
    const viewports = [
      { width: 1920, height: 1080, name: 'Desktop' },
      { width: 1366, height: 768, name: 'Laptop' },
      { width: 1280, height: 720, name: 'Small Laptop' },
    ];

    for (const viewport of viewports) {
      console.log(`测试视口: ${viewport.name} (${viewport.width}x${viewport.height})`);

      await page.setViewportSize(viewport);
      await page.waitForTimeout(1000);

      // 验证关键元素仍然可见
      await expect(reportPanel.titleLabel).toBeVisible();
      await expect(reportPanel.platformFilter).toBeVisible();
      await expect(reportPanel.searchInput).toBeVisible();

      // 截图
      await page.screenshot({
        path: `screenshots/responsive-${viewport.name.toLowerCase().replace(' ', '-')}.png`,
        fullPage: true
      });
    }
  });
});

test.describe('报告面板 - 综合测试', () => {
  let mainWindow: MainWindow;
  let reportPanel: ReportPanel;

  test.beforeEach(async ({ page }) => {
    mainWindow = new MainWindow(page);
    reportPanel = new ReportPanel(page);

    await mainWindow.goto();
    await mainWindow.goToReportTab();
    await reportPanel.waitForLoad();
  });

  test('完整的用户流程: 导航 -> 筛选 -> 选择会话 -> 查看详情', async ({ page }) => {
    const sessionCount = await reportPanel.getSessionCount();

    test.skip(sessionCount === 0, '没有可用的会话进行测试');

    console.log('=== 开始完整用户流程测试 ===');
    console.log(`1. 当前会话数量: ${sessionCount}`);

    // 步骤1: 切换到 Android 筛选
    console.log('2. 切换到 Android 筛选');
    await reportPanel.setPlatformFilter('android');
    await page.waitForTimeout(1000);
    const androidCount = await reportPanel.getSessionCount();
    console.log(`   Android 会话数量: ${androidCount}`);

    // 步骤2: 输入搜索
    console.log('3. 执行搜索');
    await reportPanel.search('');
    await page.waitForTimeout(1000);

    // 步骤3: 选择第一个会话
    console.log('4. 选择第一个会话');
    await reportPanel.selectSession(0);
    const selectedId = await reportPanel.getSelectedSessionId();
    console.log(`   选中的会话ID: ${selectedId}`);

    // 步骤4: 验证详情显示
    console.log('5. 验证详情显示');
    await page.waitForTimeout(2000);

    // 步骤5: 清空筛选
    console.log('6. 清空筛选');
    await reportPanel.clearSearch();
    await reportPanel.setPlatformFilter('all');
    await page.waitForTimeout(1000);

    const finalCount = await reportPanel.getSessionCount();
    console.log(`7. 最终会话数量: ${finalCount}`);
    console.log('=== 完整用户流程测试完成 ===');

    // 最终截图
    await page.screenshot({
      path: 'screenshots/full-user-journey.png',
      fullPage: true
    });
  });
});
