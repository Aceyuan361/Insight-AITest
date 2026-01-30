import type { MetricCardConfig } from '@/types';

export const ALL_METRIC_CARDS: MetricCardConfig[] = [
  {
    metricId: 'cpu',
    title: 'CPU Usage (%)',
    color: '#00f2ff',  // 青色 - CPU
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
    color: '#9370DB',  // 紫色 - 内存（与桌面版一致）
    yMin: 0,
    decimals: 2,  // 匹配桌面版：2位小数
    unit: 'MB',
    enabled: true,
    priority: 2,
  },
  {
    metricId: 'fps',
    title: 'Frame Rate (FPS)',
    color: '#ffb400',  // 橙色 - FPS
    decimals: 2,  // 匹配桌面版：2位小数
    unit: 'FPS',
    enabled: true,
    priority: 3,
  },
  {
    metricId: 'network_up',
    title: 'Network Upload (KB/s)',
    color: '#00ff87',  // 绿色 - 上传
    yMin: 0,
    decimals: 1,  // 匹配桌面版：1位小数
    unit: 'KB/s',
    enabled: true,
    priority: 4,
  },
  {
    metricId: 'network_down',
    title: 'Network Download (KB/s)',
    color: '#00BFFF',  // 蓝色 - 下载（与桌面版一致）
    yMin: 0,
    decimals: 1,  // 匹配桌面版：1位小数
    unit: 'KB/s',
    enabled: true,
    priority: 5,
  },
];
