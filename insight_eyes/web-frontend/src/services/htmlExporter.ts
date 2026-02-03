/**
 * HTML 报告导出服务
 * 生成包含 ECharts 图表的交互式 HTML 报告
 * 完全复刻桌面版 html_exporter.py 的功能
 */

import type { Session, Device } from '@/types';

// 后端 API 返回的 MetricsData 类型
export interface ApiMetricsData {
  id: number;
  session_id: number;
  timestamp: string;
  fps?: number;
  cpu_app?: number;
  memory_pss?: number;
  network_up_speed?: number;
  network_down_speed?: number;
}

// 统计数据类型（需要先定义，因为 Statistics 会引用它）
export interface MetricStats {
  max: number;
  min: number;
  avg: number;
  median: number;
  count: number;
}

// 统计数据接口
export interface Statistics {
  fps?: MetricStats | undefined;
  cpu_app?: MetricStats | undefined;
  memory_pss?: MetricStats | undefined;
  network_up?: MetricStats | undefined;
  network_down?: MetricStats | undefined;
}

// HTML 导出上下文
interface HtmlExportContext {
  title: string;
  session: SessionInfo;
  device: Device | null;
  statistics: Statistics;
  alerts: AlertInfo[];
  charts: Record<string, any>;
  duration: string;
  export_time: string;
}

interface SessionInfo {
  id: number;
  device_id: string;
  package_name: string;
  app_name?: string;
  platform: string;
  start_time: string;
  end_time?: string;
  duration_seconds: number;
  sample_interval: number;
}

interface AlertInfo {
  timestamp: string;
  metric_type: string;
  severity: string;
  description: string;
  threshold?: number;
  current_value?: number;
}

/**
 * 计算统计数据
 */
function calculateStatistics(metrics: ApiMetricsData[]): Statistics {
  const extractValues = (key: keyof ApiMetricsData): number[] => {
    const values: (number | string | undefined)[] = metrics.map(m => m[key]);
    const numbers = values.filter((v): v is number => typeof v === 'number' && !isNaN(v));
    return numbers;
  };

  const calcStats = (values: number[]): MetricStats | undefined => {
    if (values.length === 0) return undefined;

    const max = Math.max(...values);
    const min = Math.min(...values);
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    const sorted = [...values].sort((a, b) => a - b);
    const medianIndex = Math.floor(sorted.length / 2);
    const median = sorted[medianIndex];

    return { max, min, avg, median, count: values.length };
  };

  return {
    fps: calcStats(extractValues('fps')),
    cpu_app: calcStats(extractValues('cpu_app')),
    memory_pss: calcStats(extractValues('memory_pss')),
    network_up: calcStats(extractValues('network_up_speed')),
    network_down: calcStats(extractValues('network_down_speed')),
  };
}

/**
 * 构建 ECharts 图表配置
 */
function buildChartConfigs(metrics: ApiMetricsData[]): Record<string, any> {
  const timestamps = metrics.map(m => {
    const date = new Date(m.timestamp);
    return date.toLocaleTimeString('zh-CN', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  });

  const charts: Record<string, any> = {};

  // FPS 图表
  const fpsData = metrics.map(m => m.fps);
  if (fpsData.some(v => v != null)) {
    charts.fps = buildEchartsConfig(
      'FPS',
      timestamps,
      fpsData,
      '#ffb400',
      'fps'
    );
  }

  // CPU 图表
  const cpuData = metrics.map(m => m.cpu_app);
  if (cpuData.some(v => v != null)) {
    charts.cpu = buildEchartsConfig(
      'CPU Usage',
      timestamps,
      cpuData,
      '#00f2ff',
      '%'
    );
  }

  // Memory 图表
  const memData = metrics.map(m => m.memory_pss);
  if (memData.some(v => v != null)) {
    charts.memory = buildEchartsConfig(
      'Memory Usage',
      timestamps,
      memData,
      '#7000ff',
      'MB'
    );
  }

  // Network Up 图表
  const upData = metrics.map(m => m.network_up_speed);
  if (upData.some(v => v != null)) {
    charts.network_up = buildEchartsConfig(
      'Network Upload',
      timestamps,
      upData,
      '#00ff87',
      'KB/s'
    );
  }

  // Network Down 图表
  const downData = metrics.map(m => m.network_down_speed);
  if (downData.some(v => v != null)) {
    charts.network_down = buildEchartsConfig(
      'Network Download',
      timestamps,
      downData,
      '#0062ff',
      'KB/s'
    );
  }

  return charts;
}

/**
 * 构建 ECharts 配置
 */
function buildEchartsConfig(
  title: string,
  timestamps: string[],
  data: (number | null | undefined)[],
  color: string,
  unit: string
): any {
  // 过滤掉空值，只保留有效数字
  const cleanData = data.filter((v): v is number => v != null && !isNaN(v));

  return {
    title: {
      text: title,
      left: 'center',
      top: 10,
      textStyle: {
        color: '#e0e6ed',
        fontSize: 14,
      },
    },
    grid: {
      top: 40,
      left: 60,
      right: 30,
      bottom: 30,
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'line',
        lineStyle: { color: '#444', type: 'dashed' },
      },
    },
    xAxis: {
      type: 'category',
      data: timestamps,
      axisLabel: {
        color: '#888888',
        fontSize: 11,
      },
      axisLine: { lineStyle: { color: '#444' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#888888',
        formatter: `{value} ${unit}`,
      },
      splitLine: {
        lineStyle: { color: 'rgba(255, 255, 255, 0.08)' },
      },
      axisLine: { lineStyle: { color: '#444' } },
    },
    series: [{
      type: 'line',
      data: cleanData,
      smooth: true,
      symbol: 'none',
      lineStyle: { color, width: 2 },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: hexToRgba(color, 0.35) },
            { offset: 1, color: hexToRgba(color, 0) },
          ],
        },
      },
    }],
  };
}

/**
 * 十六进制颜色转 rgba
 */
function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * 格式化时长
 */
function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${Math.floor(seconds)}秒`;
  }
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  if (minutes < 60) {
    return `${minutes}分${secs}秒`;
  }
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}小时${mins}分${secs}秒`;
}

/**
 * 格式化时间戳
 */
function formatTimestamp(ts: string): string {
  const date = new Date(ts);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

/**
 * 导出 HTML 报告
 */
export async function exportHtmlReport(
  session: Session,
  metrics: ApiMetricsData[],
  device: Device | null,
  alerts: any[] = []
): Promise<void> {
  // 1. 计算统计数据
  const statistics = calculateStatistics(metrics);

  // 2. 构建图表配置
  const charts = buildChartConfigs(metrics);

  // 3. 准备会话信息
  const sessionInfo: SessionInfo = {
    id: session.id,
    device_id: session.device_id,
    package_name: session.app_package,
    app_name: session.app_name,
    platform: session.platform,
    start_time: formatTimestamp(session.start_time),
    end_time: session.end_time ? formatTimestamp(session.end_time) : undefined,
    duration_seconds: Math.floor((Date.now() - new Date(session.start_time).getTime()) / 1000),
    sample_interval: 1000, // TODO: 从 API 获取
  };

  // 4. 格式化告警
  const formattedAlerts: AlertInfo[] = alerts.map(a => ({
    timestamp: formatTimestamp(a.timestamp),
    metric_type: a.metric_type || 'unknown',
    severity: a.severity || 'warning',
    description: a.description || a.message || '',
    threshold: a.threshold,
    current_value: a.current_value,
  }));

  // 5. 准备模板上下文
  const context: HtmlExportContext = {
    title: `性能测试报告 - ${session.app_package}`,
    session: sessionInfo,
    device,
    statistics,
    alerts: formattedAlerts,
    charts,
    duration: formatDuration(sessionInfo.duration_seconds),
    export_time: new Date().toLocaleString('zh-CN'),
  };

  // 6. 生成 HTML 内容
  const htmlContent = renderHtmlTemplate(context);

  // 7. 下载文件
  const filename = `report_${Date.now()}_${session.app_package.replace(/\./g, '_')}.html`;
  downloadHtmlFile(htmlContent, filename);
}

/**
 * 渲染 HTML 模板（完全复刻桌面版）
 */
function renderHtmlTemplate(context: HtmlExportContext): string {
  const { title, session, device, statistics, alerts, charts, duration, export_time } = context;

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background-color: #0a0e17;
            color: #e0e6ed;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #121824 0%, #1a1f2e 100%);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            border: 1px solid #1a1f2e;
        }
        .header h1 {
            color: #00d4ff;
            margin-bottom: 16px;
        }
        .session-info {
            color: #94a3b8;
            font-size: 14px;
            line-height: 1.8;
        }
        .chart-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }
        .chart-container {
            background-color: #121824;
            border-radius: 12px;
            padding: 16px;
            border: 1px solid #1a1f2e;
        }
        .chart {
            width: 100%;
            height: 300px;
        }
        .alerts-section {
            background-color: #121824;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #1a1f2e;
        }
        .alerts-section h2 {
            color: #ef4444;
            margin-bottom: 16px;
        }
        .alert-item {
            padding: 12px;
            margin-bottom: 8px;
            background-color: rgba(239, 68, 68, 0.1);
            border-radius: 6px;
            border-left: 3px solid #ef4444;
        }
        .stats-section {
            background-color: #121824;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid #1a1f2e;
        }
        .stats-section h2 {
            color: #00d4ff;
            margin-bottom: 16px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
        }
        .stat-card {
            background-color: #0a0e17;
            border-radius: 8px;
            padding: 16px;
            border: 1px solid #1a1f2e;
        }
        .stat-card .title {
            color: #94a3b8;
            font-size: 12px;
            margin-bottom: 8px;
        }
        .stat-card .value {
            color: #e0e6ed;
            font-size: 20px;
            font-weight: bold;
        }
        .stat-card .detail {
            color: #64748b;
            font-size: 11px;
            margin-top: 4px;
        }
        .footer {
            text-align: center;
            color: #64748b;
            font-size: 12px;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>${title}</h1>
            <div class="session-info">
                ${device ? `📱 设备: ${device.name}<br>` : ''}
                📱 应用: ${session.app_name || session.package_name}<br>
                ⏰ 时间: ${session.start_time}
                ${session.end_time ? `- ${session.end_time}` : ''}<br>
                ⏱️ 监控时长: ${duration}<br>
                📊 采样间隔: ${session.sample_interval}ms
            </div>
        </div>

        ${statistics ? renderStatisticsSection(statistics) : ''}

        <div class="chart-grid">
            ${Object.entries(charts).map(([chartId]) => `
                <div class="chart-container">
                    <div id="chart-${chartId}" class="chart"></div>
                </div>
            `).join('')}
        </div>

        ${alerts.length > 0 ? renderAlertsSection(alerts) : ''}

        <div class="footer">
            导出时间: ${export_time} | Insight Eye v1.0.3
        </div>
    </div>

    <script>
        ${renderChartScripts(charts)}
    </script>
</body>
</html>`;
}

/**
 * 渲染统计区域
 */
function renderStatisticsSection(statistics: Statistics): string {
  return `
        <div class="stats-section">
            <h2>📊 性能统计</h2>
            <div class="stats-grid">
                ${statistics.fps ? renderStatCard('FPS', statistics.fps.avg.toFixed(1), `max: ${statistics.fps.max} min: ${statistics.fps.min}`, '#ffb400') : ''}
                ${statistics.cpu_app ? renderStatCard('CPU (应用)', statistics.cpu_app.avg.toFixed(2) + '%', `max: ${statistics.cpu_app.max}% min: ${statistics.cpu_app.min}%`, '#00f2ff') : ''}
                ${statistics.memory_pss ? renderStatCard('内存', statistics.memory_pss.avg.toFixed(1) + ' MB', `max: ${statistics.memory_pss.max} MB min: ${statistics.memory_pss.min} MB`, '#7000ff') : ''}
                ${statistics.network_up ? renderStatCard('网络上行', statistics.network_up.avg.toFixed(2) + ' KB/s', `max: ${statistics.network_up.max} KB/s`, '#00ff87') : ''}
                ${statistics.network_down ? renderStatCard('网络下行', statistics.network_down.avg.toFixed(2) + ' KB/s', `max: ${statistics.network_down.max} KB/s`, '#0062ff') : ''}
            </div>
        </div>
    `;
}

/**
 * 渲染统计卡片
 */
function renderStatCard(title: string, value: string, detail: string, color: string): string {
  return `
        <div class="stat-card">
            <div class="title">${title}</div>
            <div class="value" style="color: ${color}">${value}</div>
            <div class="detail">${detail}</div>
        </div>
  `;
}

/**
 * 渲染告警区域
 */
function renderAlertsSection(alerts: AlertInfo[]): string {
  return `
        <div class="alerts-section">
            <h2>⚠️ 告警记录 (${alerts.length})</h2>
            ${alerts.map(alert => `
                <div class="alert-item">
                    <strong>${alert.timestamp}</strong>
                    ${alert.description}
                    ${alert.threshold ? ` (阈值: ${alert.threshold}, 当前: ${alert.current_value})` : ''}
                </div>
            `).join('')}
        </div>
    `;
}

/**
 * 渲染图表脚本
 */
function renderChartScripts(charts: Record<string, any>): string {
  return Object.entries(charts).map(([chartId, chartConfig]) => `
        (function() {
            var chart = echarts.init(document.getElementById('chart-${chartId}'));
            chart.setOption(${JSON.stringify(chartConfig)});
            window.addEventListener('resize', function() { chart.resize(); });
        })();
  `).join('');
}

/**
 * 下载 HTML 文件
 */
function downloadHtmlFile(content: string, filename: string): void {
  const blob = new Blob([content], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
