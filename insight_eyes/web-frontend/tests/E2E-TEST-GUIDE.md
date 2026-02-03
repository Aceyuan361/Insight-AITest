# Insight Eye E2E 测试快速参考

## 快速开始

### 运行所有测试
```bash
cd web-frontend
npm run test:e2e
```

### 运行特定测试
```bash
# 仅运行布局验证测试
npx playwright test --grep "布局验证"

# 仅运行筛选功能测试
npx playwright test --grep "筛选功能"
```

### 调试模式
```bash
# 交互式调试
npm run test:e2e:debug

# UI 模式
npm run test:e2e:ui

# 有头模式 (可以看到浏览器)
npm run test:e2e:headed
```

### 查看报告
```bash
# 打开 HTML 报告
npm run test:e2e:report

# 或手动打开
npx playwright show-report
```

---

## 测试结构

```
tests/e2e/
└── report-panel.spec.ts    # 报告面板 E2E 测试

pages/
├── MainWindow.ts           # 主窗口页面对象
└── ReportPanel.ts          # 报告面板页面对象
```

---

## 测试套件

### 1. 报告面板 - 布局验证
测试报告面板的基本布局和控件显示。

```bash
npx playwright test --grep "报告面板 - 布局验证"
```

**测试用例:**
- 应该显示报告面板标题
- 应该显示所有筛选控件
- 应该显示会话列表和详情区域
- 平台筛选下拉框应该有三个选项
- 搜索输入框应该接受文本输入

---

### 2. 报告面板 - 会话选择和详情查看
测试会话选择和详情查看功能。

```bash
npx playwright test --grep "报告面板 - 会话选择和详情查看"
```

**测试用例:**
- 应该能够选择会话并查看详情
- 选中会话后应该显示会话详情
- 应该能够切换不同会话

---

### 3. 报告面板 - 筛选功能
测试平台筛选和搜索功能。

```bash
npx playwright test --grep "报告面板 - 筛选功能"
```

**测试用例:**
- 应该能够按平台筛选会话
- 应该能够按包名或应用名搜索
- 搜索不存在的应用应该返回空结果
- 刷新按钮应该重新加载会话列表

---

### 4. 报告面板 - 批量操作
测试批量选择和删除功能。

```bash
npx playwright test --grep "报告面板 - 批量操作"
```

**测试用例:**
- 应该能够全选所有会话
- 应该能够选中单个会话复选框
- 应该能够取消选择会话
- 批量删除按钮应该可见且可点击

---

### 5. 报告面板 - 响应式布局
测试不同屏幕尺寸下的布局。

```bash
npx playwright test --grep "报告面板 - 响应式布局"
```

**测试用例:**
- 在不同屏幕尺寸下布局应该正常

---

### 6. 报告面板 - 综合测试
测试完整的用户流程。

```bash
npx playwright test --grep "报告面板 - 综合测试"
```

**测试用例:**
- 完整的用户流程: 导航 -> 筛选 -> 选择会话 -> 查看详情

---

## Page Object Model

### MainWindow
主窗口页面对象，封装应用级别的操作。

```typescript
import { MainWindow } from '../../pages/MainWindow';

const mainWindow = new MainWindow(page);
await mainWindow.goto();
await mainWindow.goToReportTab();
```

**方法:**
- `goto()` - 导航到应用
- `goToReportTab()` - 切换到性能报告标签页
- `goToMonitorTab()` - 切换到实时监控标签页
- `getActiveTab()` - 获取当前活动的标签页

---

### ReportPanel
报告面板页面对象，封装报告面板的操作。

```typescript
import { ReportPanel } from '../../pages/ReportPanel';

const reportPanel = new ReportPanel(page);
await reportPanel.waitForLoad();
await reportPanel.setPlatformFilter('android');
await reportPanel.search('com.example.app');
await reportPanel.selectSession(0);
```

**方法:**
- `waitForLoad()` - 等待报告面板加载完成
- `getSelectedPlatform()` - 获取当前选中的平台筛选
- `setPlatformFilter(platform)` - 设置平台筛选
- `search(text)` - 输入搜索文本
- `clearSearch()` - 清空搜索
- `refresh()` - 点击刷新按钮
- `getSessionCount()` - 获取会话列表中显示的会话数量
- `isEmptyState()` - 检查是否显示空状态
- `selectSession(index)` - 点击指定索引的会话
- `getSelectedSessionId()` - 获取选中的会话ID
- `selectAllSessions()` - 全选所有会话
- `getSelectedSessionCount()` - 获取选中的会话数量
- `selectSessionCheckbox(index)` - 选中指定索引的会话复选框
- `isBatchDeleteButtonVisible()` - 检查批量删除按钮是否可见
- `screenshotLayout(path)` - 截图保存报告面板布局
- `screenshotFullPage(path)` - 截图保存完整页面

---

## 选择器策略

### 优先级
1. **data-testid** - 最稳定，推荐使用
2. **文本内容** - 仅用于静态文本
3. **CSS 属性** - 作为备选
4. **XPath** - 最后选择

### 示例

```typescript
// 推荐: 使用 data-testid
const button = page.getByTestId('submit-button');

// 可接受: 使用文本
const title = page.getByText('测试报告');

// 备选: 使用 CSS 选择器
const input = page.locator('input[placeholder*="搜索"]');

// 最后: 使用 XPath
const element = page.locator('//*[@id="app"]/div/button');
```

---

## 断言示例

```typescript
import { expect } from '@playwright/test';

// 可见性断言
await expect(element).toBeVisible();
await expect(element).not.toBeVisible();

// 文本断言
await expect(element).toContainText('测试报告');
await expect(element).toHaveText('测试报告');

// 属性断言
await expect(input).toHaveValue('test');
await expect(select).toHaveValue('android');

// 数量断言
await expect(elements).toHaveCount(5);

// 状态断言
await expect(button).toBeEnabled();
await expect(button).toBeDisabled();
await expect(checkbox).toBeChecked();
```

---

## 等待策略

```typescript
// 等待元素可见
await page.waitForSelector('[data-testid="session-list"]');

// 等待导航完成
await page.waitForLoadState('networkidle');

// 等待特定条件
await page.waitForURL('**/report');

// 等待固定时间 (不推荐，仅作备选)
await page.waitForTimeout(1000);
```

---

## 截图和录屏

```typescript
// 截图
await page.screenshot({ path: 'screenshot.png' });
await page.screenshot({ path: 'full.png', fullPage: true });

// 元素截图
await element.screenshot({ path: 'element.png' });

// 失败时自动截图 (在 playwright.config.ts 中配置)
use: {
  screenshot: 'only-on-failure',
}
```

---

## Trace 查看

```bash
# 查看失败测试的 trace
npx playwright show-trace test-results/[test-name]-chromium/trace.zip
```

---

## 常见问题

### 1. 测试超时
```typescript
// 增加测试超时时间
test('慢速测试', async ({ page }) => {
  test.setTimeout(60000); // 60 秒
  // ...
});
```

### 2. 元素未找到
```typescript
// 使用更宽松的等待
await expect(element).toBeVisible({ timeout: 10000 });
```

### 3. 测试不稳定
```typescript
// 添加重试
test.retry(3, '不稳定的测试', async ({ page }) => {
  // ...
});
```

---

## CI/CD 集成

测试在以下情况自动运行:
- Push 到 main/develop 分支
- 创建 Pull Request
- 手动触发 (workflow_dispatch)

查看工作流: `.github/workflows/e2e-tests.yml`

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `playwright.config.ts` | Playwright 配置 |
| `tests/e2e/report-panel.spec.ts` | 报告面板测试 |
| `pages/ReportPanel.ts` | 报告面板页面对象 |
| `src/components/panels/ReportPanel.tsx` | 报告面板组件 |
| `src/components/widgets/SessionList.tsx` | 会话列表组件 |
| `E2E-TEST-REPORT.md` | 详细测试报告 |

---

## 更多资源

- [Playwright 文档](https://playwright.dev)
- [Playwright 测试最佳实践](https://playwright.dev/docs/best-practices)
- [Playwright 选择器指南](https://playwright.dev/docs/selectors)
