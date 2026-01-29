import { useMemo } from 'react';
import type { MetricCardConfig } from '@/types';
import RealTimeChart from './RealTimeChart';

interface NeonChartCardProps {
  config: MetricCardConfig;
  data: number[];
  timestamps: string[];
}

export default function NeonChartCard({ config, data, timestamps }: NeonChartCardProps) {
  // 使用 useMemo 优化统计计算，避免不必要的重渲染
  const { currentValue, avgValue, maxValue } = useMemo(() => {
    const currentValue = data.length > 0 ? data[data.length - 1] : 0;
    const avgValue = data.length > 0
      ? data.reduce((sum, val) => sum + val, 0) / data.length
      : 0;
    const maxValue = data.length > 0 ? Math.max(...data) : 0;

    return { currentValue, avgValue, maxValue };
  }, [data]);

  return (
    <div
      className="relative bg-dark-card rounded-lg p-4 border-t-2 min-h-[180px]"
      style={{ borderColor: config.color }}
    >
      {/* 标题 */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-text-secondary">{config.title}</h3>
        <div className="flex items-center space-x-2 text-xs text-text-secondary">
          <span>最大: {maxValue.toFixed(config.decimals)}</span>
          <span>平均: {avgValue.toFixed(config.decimals)}</span>
        </div>
      </div>

      {/* 当前值 */}
      <div className="mb-2">
        <span
          className="text-4xl font-bold neon-glow"
          style={{ color: config.color }}
        >
          {currentValue.toFixed(config.decimals)}
        </span>
        <span className="ml-1 text-sm text-text-secondary">{config.unit}</span>
      </div>

      {/* 图表 */}
      <div className="absolute bottom-4 left-4 right-4 top-20">
        <RealTimeChart data={data} timestamps={timestamps} config={config} />
      </div>
    </div>
  );
}
