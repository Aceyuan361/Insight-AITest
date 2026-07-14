import type { MetricCardConfig } from '@/shared/types';
import { chartColors } from '@/shared/theme/chart-tokens';

export const ALL_METRIC_CARDS: MetricCardConfig[] = [
  {
    metricId: 'cpu',
    title: 'CPU Usage (%)',
    color: chartColors.cpu,  // chart-1（原 var(--accent) 降饱和）
    yMin: 0,
    yMax: 100,
    decimals: 2,  // 匹配桌面版：2位小数
    unit: '%',
    enabled: true,
    priority: 1,
  },
  {
    metricId: 'memory',
    title: 'Memory Usage (MB)',
    color: chartColors.memory,  // chart-2（原紫降饱和）
    yMin: 0,
    decimals: 2,  // 匹配桌面版：2位小数
    unit: 'MB',
    enabled: true,
    priority: 2,
  },
  {
    metricId: 'fps',
    title: 'Frame Rate (FPS)',
    color: chartColors.fps,  // chart-3（原 var(--chart-3) 降饱和）
    decimals: 2,  // 匹配桌面版：2位小数
    unit: 'FPS',
    enabled: true,
    priority: 3,
  },
  {
    metricId: 'network_up',
    title: 'Network Upload (KB/s)',
    color: chartColors.networkUp,  // chart-4（原 var(--chart-4) 降饱和）
    yMin: 0,
    decimals: 1,  // 匹配桌面版：1位小数
    unit: 'KB/s',
    enabled: true,
    priority: 4,
  },
  {
    metricId: 'network_down',
    title: 'Network Download (KB/s)',
    color: chartColors.networkDown,  // chart-5（原蓝降饱和）
    yMin: 0,
    decimals: 1,  // 匹配桌面版：1位小数
    unit: 'KB/s',
    enabled: true,
    priority: 5,
  },
  {
    metricId: 'gpu',
    title: 'GPU Usage (%)',
    color: chartColors.gpu,  // chart-6（原 var(--chart-6) 降饱和，默认禁用）
    yMin: 0,
    yMax: 100,
    decimals: 0,  // 匹配桌面版：0位小数
    unit: '%',
    enabled: false,  // 默认禁用（与桌面版一致）
    priority: 6,
  },
];
