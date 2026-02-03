/**
 * 会话报告图表组件
 * 2×3 网格布局，最多显示 6 个图表
 * 按优先级排序: cpu > fps > memory > network_down > network_up > gpu
 */
import { useEffect, useState, useMemo } from 'react';
import * as echarts from 'echarts';
import { api } from '@/services/api';
import type { MetricsData } from '@/services/api';

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

// 图表配置（完全复刻桌面版）
const CHART_CONFIGS: ChartCardConfig[] = [
  { metricId: 'cpu_app', title: 'CPU Usage', color: '#00f2ff', unit: '%', decimals: 2, yMin: 0, yMax: 100 },
  { metricId: 'fps', title: 'FPS', color: '#ffb400', unit: 'fps', decimals: 1, yMin: 0 },
  { metricId: 'memory_pss', title: 'Memory Usage', color: '#7000ff', unit: 'MB', decimals: 1, yMin: 0 },
  { metricId: 'network_down_speed', title: 'Network Download', color: '#0062ff', unit: 'KB/s', decimals: 2, yMin: 0 },
  { metricId: 'network_up_speed', title: 'Network Upload', color: '#00ff87', unit: 'KB/s', decimals: 2, yMin: 0 },
];

// 指标优先级顺序（桌面版一致）
const METRIC_PRIORITY: (keyof MetricsData)[] = [
  'cpu_app', 'fps', 'memory_pss', 'network_down_speed', 'network_up_speed'
];

export default function SessionCharts({ sessionId }: SessionChartsProps) {
  const [metrics, setMetrics] = useState<MetricsData[]>([]);
  const [loading, setLoading] = useState(false);

  // 图表容器引用
  const chartRefs = useState<Record<string, HTMLDivElement>>({} as Record<string, HTMLDivElement>)[0];
  const chartInstances = useState<Record<string, echarts.ECharts>>({} as Record<string, echarts.ECharts>)[0];

  // 加载指标数据
  useEffect(() => {
    if (!sessionId) {
      setMetrics([]);
      return;
    }

    const loadData = async () => {
      setLoading(true);
      try {
        // 获取足够多的数据点用于显示完整趋势
        const data = await api.getSessionMetrics(sessionId, 10000);
        setMetrics(data);
      } catch (error) {
        console.error('Failed to load session metrics:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [sessionId]);

  // 清理图表实例
  useEffect(() => {
    return () => {
      Object.values(chartInstances).forEach(chart => chart.dispose());
    };
  }, []);

  // 分析哪些指标有数据
  const availableMetrics = useMemo(() => {
    if (metrics.length === 0) return [];

    const available = new Set<keyof MetricsData>();
    for (const metric of metrics) {
      for (const key of METRIC_PRIORITY) {
        if (metric[key] !== undefined && metric[key] !== null) {
          available.add(key);
        }
      }
    }
    // 按优先级排序
    return METRIC_PRIORITY.filter(k => available.has(k));
  }, [metrics]);

  // 最多显示 6 个图表
  const displayMetrics = availableMetrics.slice(0, 6);

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
    if (metrics.length === 0 || displayMetrics.length === 0) return;

    // 为每个指标创建/更新图表
    displayMetrics.forEach((metricKey) => {
      const config = CHART_CONFIGS.find(c => c.metricId === metricKey);
      if (!config) return;

      const chartId = `chart-${metricKey}`;
      const container = chartRefs[chartId];
      if (!container) return;

      // 提取数据
      const timestamps = metrics.map(m => {
        const date = new Date(m.timestamp);
        return formatTime(date);
      });

      const data = metrics.map(m => m[metricKey] as number);

      // 过滤空值
      const cleanData = data.filter(v => v !== null && v !== undefined && !isNaN(v));
      if (cleanData.length === 0) return;

      // 创建或获取图表实例
      let chart = chartInstances[chartId];
      if (!chart) {
        chart = echarts.init(container);
        chartInstances[chartId] = chart;

        // 添加 resize 监听
        const handleResize = () => chart?.resize();
        window.addEventListener('resize', handleResize);
        container.addEventListener('resize', handleResize);
      }

      // 构建 ECharts 配置（完全复刻桌面版样式）
      const option: echarts.EChartsOption = {
        title: {
          text: config.title,
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
          min: config.yMin,
          max: config.yMax,
          axisLabel: {
            color: '#888888',
            formatter: `{value} ${config.unit}`,
          },
          splitLine: {
            lineStyle: { color: 'rgba(255, 255, 255, 0.08)' },
          },
          axisLine: { lineStyle: { color: '#444' } },
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
    });
  }, [metrics, displayMetrics, chartRefs, chartInstances]);

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
        <p className="text-text-secondary">请选择一个会话查看图表</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-dark-card rounded-lg border border-gray-800">
        <p className="text-text-secondary">加载图表数据中...</p>
      </div>
    );
  }

  if (metrics.length === 0) {
    return (
      <div className="flex items-center justify-center h-full bg-dark-card rounded-lg border border-gray-800">
        <p className="text-text-secondary">该会话暂无指标数据</p>
      </div>
    );
  }

  if (displayMetrics.length === 0) {
    return (
      <div className="flex items-center justify-center h-full bg-dark-card rounded-lg border border-gray-800">
        <p className="text-text-secondary">暂无可显示的图表数据</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 p-4 bg-dark-card rounded-lg border border-gray-800">
      {displayMetrics.map((metricKey) => {
        const config = CHART_CONFIGS.find(c => c.metricId === metricKey);
        if (!config) return null;

        const chartId = `chart-${metricKey}`;

        return (
          <div
            key={metricKey}
            className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden"
            style={{ minHeight: '200px' }}
          >
            <div
              ref={(el) => {
                if (el) chartRefs[chartId] = el;
              }}
              className="w-full"
              style={{ height: '200px' }}
            />
          </div>
        );
      })}
    </div>
  );
}
