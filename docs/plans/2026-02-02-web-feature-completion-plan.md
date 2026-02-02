# Web端功能完善实现计划

**日期**: 2026-02-02
**分支**: 1.0.3
**参考**: 桌面版完整实现

---

## 一、任务概述

### 1.1 监控面板交互改进（任务 #12）
- **目标**: 完全复刻桌面版的悬停效果和X轴时间刻度
- **参考文件**: `insight_eyes/desktop/ui/panels/monitor_panel_v2.py`

### 1.2 结束监控数据处理（任务 #14）
- **目标**: 停止监控时进行数据统计和HTML报告导出
- **参考文件**:
  - `insight_eyes/desktop/data/html_exporter.py`
  - `insight_eyes/desktop/ui/widgets/session_report_widget.py`

### 1.3 报告面板和配置面板完善（任务 #13）
- **目标**: 完全复刻桌面版的所有高级功能
- **参考文件**:
  - `insight_eyes/desktop/ui/panels/report_panel.py`
  - `insight_eyes/desktop/ui/panels/config_panel.py`

---

## 二、任务 #12: 监控面板交互改进

### 2.1 ECharts Tooltip 悬停效果

**桌面版实现**（`monitor_panel_v2.py:407-486`）:
```python
def _on_mouse_moved(self, pos):
    # 1. 检查鼠标是否在图表区域
    # 2. 找到最近的数据点（idx = int(round(x_pos))）
    # 3. 显示垂直参考线（pg.InfiniteLine）
    # 4. 显示数据点标记（ScatterPlotItem）
    # 5. 显示浮动提示框（ChartTooltip）
    # 6. 自动隐藏机制（2秒后）
```

**Web端实现**:

#### 文件: `insight_eyes/web-frontend/src/components/charts/RealTimeChart.tsx`

```typescript
// 1. 配置 ECharts tooltip
const chartOption = {
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'line',
      lineStyle: { color: '#444', type: 'dashed' }
    },
    backgroundColor: 'rgba(18, 24, 36, 0.95)',
    borderColor: '#1a1f2e',
    textStyle: { color: '#e0e6ed' },
    formatter: (params: any) => {
      const point = params[0];
      const time = timestamps[point.dataIndex];
      const value = point.value;
      return `
        <div style="padding: 8px;">
          <div style="color: #94a3b8; font-size: 12px;">${title}</div>
          <div style="margin: 4px 0;">
            <span style="color: #64748b;">时间:</span>
            <span style="color: #e0e6ed; margin-left: 8px;">${time}</span>
          </div>
          <div>
            <span style="color: #64748b;">数值:</span>
            <span style="color: ${accentColor}; margin-left: 8px;">${value.toFixed(2)}${unit}</span>
          </div>
        </div>
      `;
    }
  }
};

// 2. 高亮显示数据点
series: [{
  type: 'line',
  showSymbol: false,  // 默认不显示
  emphasis: {
    focus: 'series',
    itemStyle: {
      color: accentColor,
      borderColor: accentColor,
      borderWidth: 2
    }
  },
  markPoint: {
    data: [],
    symbol: 'circle',
    symbolSize: 12,
    itemStyle: {
      color: accentColor,
      borderColor: accentColor
    }
  }
}]
```

### 2.2 X轴时间刻度处理

**桌面版实现**（`monitor_panel_v2.py:290-310`）:
```python
# 根据数据点数量动态计算间隔
if len(self.data) <= 20:
    interval = 5
elif len(self.data) <= 40:
    interval = 10
else:
    interval = 15

# 格式化时间戳
for i in range(0, len(self.data), interval):
    time_str = self.timestamps[i].strftime("%H:%M:%S")
    ticks.append((i, time_str))
```

**Web端实现**:

```typescript
// 在 addDataPoint 时保存时间戳
const timestamps: string[] = [];
const data: number[] = [];

const addDataPoint = (value: number) => {
  const now = new Date();
  const timeStr = now.toLocaleTimeString('zh-CN', { hour12: false });
  timestamps.push(timeStr);
  data.push(value);

  // 限制最大点数
  if (timestamps.length > 120) {
    timestamps.shift();
    data.shift();
  }

  // 更新X轴刻度
  updateXAxisTicks();
};

const updateXAxisTicks = () => {
  const interval = data.length <= 20 ? 5 : data.length <= 40 ? 10 : 15;
  const ticks: string[] = [];

  for (let i = 0; i < data.length; i += interval) {
    ticks.push(timestamps[i]);
  }

  chartOption.xAxis.data = ticks;
  chartOption.xAxis.axisLabel.interval = interval - 1;
};
```

### 2.3 实现清单

- [ ] 配置 ECharts tooltip
- [ ] 添加垂直参考线（axisPointer）
- [ ] 实现数据点高亮（emphasis + markPoint）
- [ ] 动态X轴时间刻度
- [ ] 测试悬停效果

---

## 三、任务 #14: 结束监控数据处理

### 3.1 数据统计计算

**停止监控时需要计算**:
1. **会话时长**: 开始时间到结束时间
2. **样本总数**: 采集的数据点数量
3. **各项指标统计**: max, min, avg, median

**实现位置**: `insight_eyes/web-frontend/src/store/monitoringStore.ts`

```typescript
async stopMonitoring() {
  if (!this.currentSession) return;

  // 1. 计算会话时长
  const endTime = new Date().toISOString();
  const startTime = this.currentSession.start_time;
  const duration = new Date(endTime).getTime() - new Date(startTime).getTime();

  // 2. 计算统计数据
  const metrics = this.currentMetrics;
  const statistics = {
    cpu: calculateStats(metrics.map(m => m.cpu_app)),
    memory: calculateStats(metrics.map(m => m.memory_pss)),
    fps: calculateStats(metrics.map(m => m.fps)),
    network_up: calculateStats(metrics.map(m => m.network_up_speed)),
    network_down: calculateStats(metrics.map(m => m.network_down_speed))
  };

  // 3. 保存到数据库
  await updateSession(this.currentSession.id, {
    end_time: endTime,
    duration_seconds: duration / 1000,
    statistics
  });

  // 4. 清空当前会话
  this.currentSession = null;
  this.currentMetrics = [];
}

function calculateStats(values: number[]) {
  const valid = values.filter(v => v != null && !isNaN(v));
  if (valid.length === 0) return null;

  const max = Math.max(...valid);
  const min = Math.min(...valid);
  const avg = valid.reduce((a, b) => a + b, 0) / valid.length;
  const sorted = [...valid].sort((a, b) => a - b);
  const median = sorted[Math.floor(sorted.length / 2)];

  return { max, min, avg, median, count: valid.length };
}
```

### 3.2 HTML报告导出

**桌面版模板** (`html_exporter.py:274-470`):
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <script src="./echarts.min.js"></script>
    <style>
        body { background-color: #0a0e17; color: #e0e6ed; }
        .chart-grid { display: grid; grid-template-columns: repeat(2, 1fr); }
        .chart { width: 100%; height: 300px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ title }}</h1>
            <div class="session-info">...</div>
        </div>
        <div class="stats-section">...</div>
        <div class="chart-grid">
            {% for chart_id, chart_config in charts.items() %}
            <div id="chart-{{ chart_id }}" class="chart"></div>
            {% endfor %}
        </div>
        <div class="alerts-section">...</div>
    </div>
    <script>
        {% for chart_id, chart_config in charts.items() %}
        var chart = echarts.init(document.getElementById('chart-{{ chart_id }}'));
        chart.setOption({{ chart_config | tojson }});
        {% endfor %}
    </script>
</body>
</html>
```

**Web端实现**:

#### 文件: `insight_eyes/web-frontend/src/services/htmlExporter.ts`

```typescript
interface HtmlExportContext {
  title: string;
  session: any;
  device: any;
  statistics: any;
  alerts: any[];
  charts: Record<string, any>;
  duration: string;
  export_time: string;
}

export async function exportHtmlReport(sessionId: number): Promise<boolean> {
  // 1. 获取会话数据
  const session = await getSession(sessionId);
  const device = await getDevice(session.device_id);
  const metrics = await getSessionMetrics(sessionId);
  const alerts = await getSessionAlerts(sessionId);

  // 2. 计算统计数据
  const statistics = calculateStatistics(metrics);

  // 3. 构建图表配置
  const charts = buildChartConfigs(metrics);

  // 4. 准备模板上下文
  const context: HtmlExportContext = {
    title: `性能测试报告 - ${session.package_name}`,
    session: { ...session, start_time: formatTime(session.start_time) },
    device,
    statistics,
    alerts,
    charts,
    duration: formatDuration(session.duration_seconds),
    export_time: new Date().toLocaleString('zh-CN')
  };

  // 5. 渲染HTML模板
  const htmlContent = renderHtmlTemplate(context);

  // 6. 下载文件
  const filename = `report_${Date.now()}_${session.package_name}.html`;
  downloadHtmlFile(htmlContent, filename);

  return true;
}

function buildChartConfigs(metrics: any[]): Record<string, any> {
  // 构建 ECharts 配置
  const timestamps = metrics.map(m => formatTimestamp(m.timestamp));

  return {
    fps: buildEchartsConfig('FPS', timestamps, metrics.map(m => m.fps), '#ffb400'),
    cpu: buildEchartsConfig('CPU', timestamps, metrics.map(m => m.cpu_app), '#00f2ff'),
    memory: buildEchartsConfig('Memory', timestamps, metrics.map(m => m.memory_pss), '#7000ff'),
    network_up: buildEchartsConfig('Network Up', timestamps, metrics.map(m => m.network_up_speed), '#00ff87'),
    network_down: buildEchartsConfig('Network Down', timestamps, metrics.map(m => m.network_down_speed), '#0062ff')
  };
}

function renderHtmlTemplate(context: HtmlExportContext): string {
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>${context.title}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
    <style>
        ${getTemplateStyles()}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>${context.title}</h1>
            <div class="session-info">
                ${context.device ? `📱 设备: ${context.device.name}<br>` : ''}
                📱 应用: ${context.session.package_name}<br>
                ⏰ 时间: ${context.session.start_time}
                ${context.session.end_time ? `- ${context.session.end_time}` : ''}<br>
                ⏱️ 监控时长: ${context.duration}
            </div>
        </div>
        ${renderStatisticsSection(context.statistics)}
        ${renderChartsSection(context.charts)}
        ${renderAlertsSection(context.alerts)}
        <div class="footer">
            导出时间: ${context.export_time} | Insight Eye v1.0.3
        </div>
    </div>
    <script>
        ${renderChartScripts(context.charts)}
    </script>
</body>
</html>`;
}
```

### 3.3 实现清单

- [ ] 添加数据统计计算函数
- [ ] 在 stopMonitoring 中调用统计
- [ ] 创建 HTML 导出服务
- [ ] 实现 ECharts 配置生成
- [ ] 实现 Jinja2 风格模板渲染
- [ ] 添加文件下载功能
- [ ] 测试完整流程

---

## 四、任务 #13: 报告面板和配置面板完善

### 4.1 报告面板功能

**桌面版功能** (`report_panel.py:23-200`):
1. 会话列表表格（支持多选）
2. 筛选和搜索
3. 会话详情展示（分屏布局）
4. 导出 HTML 报告
5. 删除会话（单个/批量）

**Web端实现**:

#### 文件: `insight_eyes/web-frontend/src/components/panels/ReportPanel.tsx`

```typescript
// 1. 添加会话选择和多选功能
const [selectedSessions, setSelectedSessions] = useState<number[]>([]);

// 2. 添加批量操作按钮
<div className="header-actions">
  <button onClick={handleExportHtml}>导出HTML报告</button>
  <button onClick={handleBatchDelete} className="danger">批量删除</button>
</div>

// 3. 会话详情展示（双击或点击查看按钮）
function SessionDetailView({ sessionId }: { sessionId: number }) {
  const [session, setSession] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [charts, setCharts] = useState(null);

  useEffect(() => {
    loadSessionDetail(sessionId);
  }, [sessionId]);

  return (
    <div className="session-detail">
      <div className="info-bar">{/* 会话信息 */}</div>
      <div className="split-view">
        <div className="charts-area">{/* 图表网格 */}</div>
        <div className="stats-panel">{/* 统计面板 */}</div>
      </div>
      <div className="actions">
        <button onClick={() => exportHtml(sessionId)}>导出HTML报告</button>
        <button onClick={() => deleteSession(sessionId)} className="danger">删除会话</button>
      </div>
    </div>
  );
}
```

### 4.2 配置面板功能

**桌面版功能** (`config_panel.py`):
1. 采集设置（采样间隔）
2. 阈值设置（CPU、内存、FPS、网络）
3. 数据保留设置
4. 配置导入/导出
5. 重置为默认值

**Web端实现**:

#### 文件: `insight_eyes/web-frontend/src/components/panels/ConfigPanel.tsx`

```typescript
// 1. 添加配置导入/导出按钮
<div className="config-actions">
  <button onClick={handleExportConfig}>导出配置</button>
  <button onClick={handleImportConfig}>导入配置</button>
  <button onClick={handleResetConfig} className="danger">重置为默认</button>
  <button onClick={handleOpenConfigDir}>打开配置目录</button>
</div>

// 2. 导出配置功能
async function handleExportConfig() {
  const config = monitoringStore.getState().config;
  const configJson = JSON.stringify(config, null, 2);
  const blob = new Blob([configJson], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `insight-eye-config-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// 3. 导入配置功能
async function handleImportConfig() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';
  input.onchange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    const config = JSON.parse(text);
    await monitoringStore.getState().updateConfig(config);
  };
  input.click();
}
```

### 4.3 实现清单

**报告面板**:
- [ ] 添加会话详情查看组件
- [ ] 实现导出HTML按钮
- [ ] 实现删除会话功能
- [ ] 实现批量删除功能
- [ ] 添加搜索和筛选

**配置面板**:
- [ ] 添加配置导入按钮
- [ ] 添加配置导出按钮
- [ ] 添加重置配置功能
- [ ] 添加打开配置目录功能
- [ ] 实现配置文件验证

---

## 五、实施顺序

### 阶段 1: 监控面板交互（优先级最高）
1. ECharts tooltip 配置
2. 数据点高亮效果
3. X轴时间刻度动态更新
4. 测试和调优

### 阶段 2: 数据处理和导出
1. 添加统计计算函数
2. 在 stopMonitoring 中集成
3. 创建 HTML 导出服务
4. 测试导出功能

### 阶段 3: 报告面板完善
1. 会话详情查看组件
2. 导出和删除功能
3. 批量操作支持
4. UI 优化

### 阶段 4: 配置面板完善
1. 配置导入/导出
2. 重置功能
3. 打开配置目录
4. 测试完整流程

---

## 六、技术要点

### 6.1 ECharts Tooltip 高级配置
- `axisPointer.type = 'line'` 垂直参考线
- `emphasis` 数据点高亮
- 自定义 `formatter` 函数

### 6.2 时间刻度动态更新
- 根据数据点数量计算间隔
- 保持最多120个数据点
- 时间格式化 `HH:mm:ss`

### 6.3 HTML 模板渲染
- 使用模板字符串（类似 Jinja2）
- ECharts 配置序列化
- 霓虹主题样式复用

### 6.4 统计计算
- 排除 null 和 NaN 值
- 计算中位数
- 格式化输出

---

**预计工作量**: 4-6小时
**验收标准**:
1. 悬停显示时间和数值，带垂直参考线
2. 停止监控时自动计算统计数据
3. 可导出包含图表的HTML报告
4. 报告面板可查看详情和删除会话
5. 配置面板支持导入/导出
