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
  const { currentValue, avgValue, maxValue, minValue } = useMemo(() => {
    const currentValue = data.length > 0 ? data[data.length - 1] : 0;
    const avgValue = data.length > 0
      ? data.reduce((sum, val) => sum + val, 0) / data.length
      : 0;
    const maxValue = data.length > 0 ? Math.max(...data) : 0;
    const minValue = data.length > 0 ? Math.min(...data) : 0;

    return { currentValue, avgValue, maxValue, minValue };
  }, [data]);

  return (
    <div
      className="min-h-[180px] flex flex-col"
      style={{
        backgroundColor: '#141414',
        borderRadius: '12px',
        border: '1px solid rgba(255,255,255,0.05)',
        borderTop: `2px solid ${config.color}`,
        padding: '15px',
      }}
    >
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-2 flex-shrink-0">
        <h3 style={{
          fontSize: '1.1rem',
          fontWeight: '500',
          color: '#ffffff',
        }}>
          {config.title}
        </h3>
        <div style={{
          fontSize: '0.85rem',
          fontFamily: "'Roboto Mono', 'Consolas', 'Monaco', monospace",
          color: config.color,
        }}>
          Max: {maxValue.toFixed(config.decimals)}
          {config.unit}
          <span> | </span>
          Min: {minValue.toFixed(config.decimals)}
          {config.unit}
          <span> | </span>
          Avg: {avgValue.toFixed(config.decimals)}
          {config.unit}
        </div>
      </div>

      {/* 图表区域 - 占据主要空间 */}
      <div className="flex-1 min-h-0" style={{ minHeight: '180px' }}>
        <RealTimeChart data={data} timestamps={timestamps} config={config} />
      </div>

      {/* 当前值 - 移到底部，字体减小 */}
      <div className="mt-2 flex-shrink-0 flex items-baseline">
        <span
          style={{
            fontSize: '1.1rem',
            fontWeight: 'bold',
            color: config.color,
          }}
        >
          {currentValue.toFixed(config.decimals)}
        </span>
        <span style={{
          marginLeft: '4px',
          fontSize: '0.7rem',
          color: '#888888',
        }}>
          {config.unit}
        </span>
      </div>
    </div>
  );
}
