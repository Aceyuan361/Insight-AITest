/**
 * 会话报告图表组件
 * 2×3 网格布局，最多显示 6 个图表
 * 按优先级排序: cpu > fps > memory > network_down > network_up > gpu
 */
import { useEffect, useState, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import * as echarts from 'echarts';
import { api } from '@/shared/api/api';
import type { MetricsData } from '@/shared/api/api';
import { chartColors, getChartNeutral } from '@/shared/theme/chart-tokens';
import { useIsMobile } from '@/shared/hooks/useIsMobile';
import { useThemeStore } from '@/shared/store/themeStore';

interface SessionChartsProps {
  sessionId: number | null;
}

// 图表卡片配置
interface ChartCardConfig {
  metricId: keyof MetricsData;
  title: string;
  color: string;
  unit: string;
  decimals: number;
  yMin?: number;
  yMax?: number;
}

// 图表配置（颜色用 chartColors 真实 hex，echarts canvas 不支持 CSS variables）
const CHART_CONFIGS: ChartCardConfig[] = [
  { metricId: 'cpu_app', title: 'CPU Usage', color: chartColors.cpu, unit: '%', decimals: 2, yMin: 0, yMax: 100 },
  { metricId: 'fps', title: 'FPS', color: chartColors.fps, unit: 'fps', decimals: 1, yMin: 0 },
  { metricId: 'memory_pss', title: 'Memory Usage', color: chartColors.memory, unit: 'MB', decimals: 1, yMin: 0 },
  { metricId: 'network_down_speed', title: 'Network Download', color: chartColors.networkDown, unit: 'KB/s', decimals: 2, yMin: 0 },
  { metricId: 'network_up_speed', title: 'Network Upload', color: chartColors.networkUp, unit: 'KB/s', decimals: 2, yMin: 0 },
];

// 指标优先级顺序（桌面版一致）
const METRIC_PRIORITY: (keyof MetricsData)[] = [
  'cpu_app', 'fps', 'memory_pss', 'network_down_speed', 'network_up_speed'
];

export default function SessionCharts({ sessionId }: SessionChartsProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const theme = useThemeStore((s) => s.theme);
  const chartNeutral = getChartNeutral(theme);
  const [metrics, setMetrics] = useState<MetricsData[]>([]);
  const [loading, setLoading] = useState(false);

  // 图表容器引用 - 使用 useRef 而不是 useState
  const chartRefs = useRef<Record<string, HTMLDivElement>>({} as Record<string, HTMLDivElement>);
  const chartInstances = useRef<Record<string, echarts.ECharts>>({} as Record<string, echarts.ECharts>);

  // 加载指标数据
  useEffect(() => {
    if (!sessionId) {
      setMetrics([]);
      return;
    }

    const loadData = async () => {
      setLoading(true);
      try {
        // 并行获取会话信息和指标数据
        const [session, data] = await Promise.all([
          api.getSession(sessionId),
          api.getSessionMetrics(sessionId, 10000)
        ]);

        console.log('[SessionCharts] 加载原始数据:', data.length, '条');
        console.log('[SessionCharts] 会话时间:', session.start_time, '-', session.end_time);

        // 后端已经返回正确的字段名（cpu_app, memory_pss, network_up_speed, network_down_speed）
        // 不需要字段名映射

        // 根据会话时间过滤数据，只显示监控期间的数据
        const startTime = new Date(session.start_time).getTime();
        const endTime = session.end_time ? new Date(session.end_time).getTime() : Date.now();

        const filteredData = data.filter(item => {
          const itemTime = new Date(item.timestamp).getTime();
          return itemTime >= startTime && itemTime <= endTime;
        });

        console.log('[SessionCharts] 过滤后数据:', filteredData.length, '条');
        console.log('[SessionCharts] 时间范围:', new Date(startTime).toLocaleTimeString(), '-', new Date(endTime).toLocaleTimeString());

        setMetrics(filteredData);
      } catch (error) {
        console.error('Failed to load session metrics:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [sessionId]);

  // 清理图表实例（组件卸载时）
  useEffect(() => {
    return () => {
      Object.values(chartInstances.current).forEach(chart => {
        if (chart && typeof chart.dispose === 'function') {
          chart.dispose();
        }
      });
      chartInstances.current = {};
    };
  }, []);

  // 当 sessionId 变化时清理旧的图表实例
  useEffect(() => {
    console.log('[SessionCharts] sessionId 变化，清理旧图表:', sessionId);
    // 清理所有旧的图表实例
    Object.values(chartInstances.current).forEach(chart => {
      if (chart && typeof chart.dispose === 'function') {
        chart.dispose();
      }
    });
    chartInstances.current = {};
    chartRefs.current = {};
  }, [sessionId]);

  // 分析哪些指标有数据
  const availableMetrics = useMemo(() => {
    if (metrics.length === 0) {
      console.log('[SessionCharts] availableMetrics: 无数据');
      return [];
    }

    const available = new Set<keyof MetricsData>();
    for (const metric of metrics) {
      for (const key of METRIC_PRIORITY) {
        if (metric[key] !== undefined && metric[key] !== null) {
          available.add(key);
        }
      }
    }
    // 按优先级排序
    const result = METRIC_PRIORITY.filter(k => available.has(k));
    console.log('[SessionCharts] availableMetrics:', result);
    console.log('[SessionCharts] 可用指标数量:', result.length);
    return result;
  }, [metrics]);

  // 最多显示 6 个图表
  const displayMetrics = availableMetrics.slice(0, 6);

  // 计算每个指标的统计数据（max, min, avg）
  const metricsStatistics = useMemo(() => {
    const stats: Record<string, { max: number; min: number; avg: number } | null> = {};

    for (const metricKey of displayMetrics) {
      const values = metrics
        .map(m => m[metricKey] as number)
        .filter(v => v !== null && v !== undefined && !isNaN(v));

      if (values.length > 0) {
        stats[metricKey] = {
          max: Math.max(...values),
          min: Math.min(...values),
          avg: values.reduce((a, b) => a + b, 0) / values.length,
        };
      } else {
        stats[metricKey] = null;
      }
    }

    return stats;
  }, [metrics, displayMetrics]);

  // 格式化时间戳（HH:mm:ss）
  const formatTime = (date: Date): string => {
    return date.toLocaleTimeString('zh-CN', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // 初始化和更新图表
  useEffect(() => {
    console.log('[SessionCharts] 图表 useEffect 触发');
    console.log('[SessionCharts] metrics.length:', metrics.length);
    console.log('[SessionCharts] displayMetrics:', displayMetrics);

    if (metrics.length === 0 || displayMetrics.length === 0) {
      console.log('[SessionCharts] 跳过图表初始化：无数据或无可显示指标');
      return;
    }

    // 使用 setTimeout 确保DOM已经渲染
    const timer = setTimeout(() => {
      console.log('[SessionCharts] 开始创建/更新图表，指标数量:', displayMetrics.length);

      // 为每个指标创建/更新图表
      displayMetrics.forEach((metricKey, index) => {
        const config = CHART_CONFIGS.find(c => c.metricId === metricKey);
        if (!config) {
          console.warn('[SessionCharts] 未找到配置:', metricKey);
          return;
        }

        const chartId = `chart-${metricKey}`;
        const container = chartRefs.current[chartId];

        console.log(`[SessionCharts] 图表 ${index} [${chartId}]:`, {
          hasContainer: !!container,
          metricKey,
          config: config.title
        });

        if (!container) {
          console.warn(`[SessionCharts] 容器未找到: ${chartId}`);
          return;
        }

        // 提取数据
        const timestamps = metrics.map(m => {
          const date = new Date(m.timestamp);
          return formatTime(date);
        });

        const data = metrics.map(m => m[metricKey] as number);

        console.log(`[SessionCharts] ${metricKey} 数据点数量:`, data.length);
        console.log(`[SessionCharts] ${metricKey} 数据样本:`, data.slice(0, 3));

        // 过滤空值
        const cleanData = data.filter(v => v !== null && v !== undefined && !isNaN(v));
        if (cleanData.length === 0) {
          console.warn(`[SessionCharts] ${metricKey} 无有效数据`);
          return;
        }

        // 创建或获取图表实例
        let chart = chartInstances.current[chartId];
        if (!chart) {
          console.log(`[SessionCharts] 创建新图表实例: ${chartId}`);
          chart = echarts.init(container);
          chartInstances.current[chartId] = chart;

          // 添加 resize 监听
          const handleResize = () => chart?.resize();
          window.addEventListener('resize', handleResize);
          container.addEventListener('resize', handleResize);
        } else {
          console.log(`[SessionCharts] 使用已存在的图表实例: ${chartId}`);
        }

        // 构建 ECharts 配置（完全复刻桌面版样式）
        const option: echarts.EChartsOption = {
          title: {
            text: config.title,
            left: 12,
            top: 10,
            textStyle: {
              color: chartNeutral.seriesLabel,
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
              lineStyle: { color: chartNeutral.axisLine, type: 'dashed' },
            },
          },
          xAxis: {
            type: 'category',
            data: timestamps,
            axisLabel: {
              color: chartNeutral.axisLabel,
              fontSize: 11,
            },
            axisLine: { lineStyle: { color: chartNeutral.axisLine } },
          },
          yAxis: {
            type: 'value',
            min: config.yMin,
            max: config.yMax,
            axisLabel: {
              color: chartNeutral.axisLabel,
              formatter: `{value} ${config.unit}`,
            },
            splitLine: {
              lineStyle: { color: chartNeutral.splitLine },
            },
            axisLine: { lineStyle: { color: chartNeutral.axisLine } },
          },
          series: [{
            type: 'line',
            data: data,
            smooth: true,
            symbol: 'none',
            lineStyle: { color: config.color, width: 2 },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: hexToRgba(config.color, 0.35) },
                  { offset: 1, color: hexToRgba(config.color, 0) },
                ],
              },
            },
          }],
        };

        chart.setOption(option, true);
        console.log(`[SessionCharts] ${chartId} 图表配置已应用`);
      });

      console.log('[SessionCharts] 所有图表创建/更新完成');
    }, 100); // 延迟100ms确保DOM渲染完成

    return () => clearTimeout(timer);
  }, [metrics, displayMetrics, chartNeutral]); // 移除 chartRefs 和 chartInstances 依赖

  // 辅助函数：十六进制颜色转 rgba
  function hexToRgba(hex: string, alpha: number): string {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  if (!sessionId) {
    return (
      <div className="flex items-center justify-center h-full bg-dark-card rounded-lg border border-gray-800">
        <p className="text-text-secondary">{t('sessionList.selectSession')}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-dark-card rounded-lg border border-gray-800">
        <p className="text-text-secondary">{t('sessionList.loadingCharts')}</p>
      </div>
    );
  }

  if (metrics.length === 0) {
    return (
      <div className="flex items-center justify-center h-full bg-dark-card rounded-lg border border-gray-800">
        <p className="text-text-secondary">{t('sessionList.noData')}</p>
      </div>
    );
  }

  if (displayMetrics.length === 0) {
    return (
      <div className="flex items-center justify-center h-full bg-dark-card rounded-lg border border-gray-800">
        <p className="text-text-secondary">{t('sessionList.noDisplayableData')}</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', height: '100%' }}>
      {/* 2列 × 3行布局 */}
      {displayMetrics.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : 'repeat(2, 1fr)',
          gridTemplateRows: isMobile ? 'none' : 'repeat(3, 1fr)',
          gap: '8px',
          flex: 1,
          minHeight: 0,
        }}>
          {displayMetrics.slice(0, 6).map((metricKey) => {
            const config = CHART_CONFIGS.find(c => c.metricId === metricKey);
            if (!config) return null;

            const chartId = `chart-${metricKey}`;

            return (
              <div
                key={metricKey}
                style={{
                  backgroundColor: "var(--bg-card)",
                  border: '1px solid var(--bg-card)',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  minHeight: '200px',
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  position: 'relative',
                }}
              >
                {/* 统计信息 - 右上角 */}
                {metricsStatistics[metricKey] && (
                  <div style={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    fontSize: '11px',
                    color: config.color,
                    fontFamily: "'Roboto Mono', monospace",
                    opacity: 0.8,
                    zIndex: 10,
                  }}>
                    Max: {metricsStatistics[metricKey]!.max.toFixed(config.decimals)}{config.unit} | Min: {metricsStatistics[metricKey]!.min.toFixed(config.decimals)}{config.unit} | Avg: {metricsStatistics[metricKey]!.avg.toFixed(config.decimals)}{config.unit}
                  </div>
                )}
                <div
                  ref={(el) => {
                    if (el) chartRefs.current[chartId] = el;
                  }}
                  style={{ width: '100%', flex: 1, minHeight: 0 }}
                />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
