import { useMemo, useState, useEffect, useRef } from 'react';
import type { MetricCardConfig } from '@/shared/types';
import RealTimeChart from './RealTimeChart';

interface NeonChartCardProps {
  config: MetricCardConfig;
  data: number[];
  timestamps: string[];
  note?: string;
}

export default function NeonChartCard({ config, data, timestamps, note }: NeonChartCardProps) {
  // 动画状态
  const [animatedValue, setAnimatedValue] = useState(0);
  const [animatedMax, setAnimatedMax] = useState(0);
  const [animatedMin, setAnimatedMin] = useState(0);
  const [animatedAvg, setAnimatedAvg] = useState(0);

  // 保存上一次的值，用于动画过渡
  const prevValueRef = useRef(0);
  const prevMaxRef = useRef(0);
  const prevMinRef = useRef(0);
  const prevAvgRef = useRef(0);

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

  // 数值平滑过渡动画
  useEffect(() => {
    const duration = 300; // 300ms 平滑过渡
    const startTime = performance.now();

    function animate(currentTime: number) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      // easeOutCubic 缓动函数
      const easeProgress = 1 - Math.pow(1 - progress, 3);

      // 当前值动画
      setAnimatedValue(
        prevValueRef.current + (currentValue - prevValueRef.current) * easeProgress
      );

      // 统计值动画
      setAnimatedMax(
        prevMaxRef.current + (maxValue - prevMaxRef.current) * easeProgress
      );
      setAnimatedMin(
        prevMinRef.current + (minValue - prevMinRef.current) * easeProgress
      );
      setAnimatedAvg(
        prevAvgRef.current + (avgValue - prevAvgRef.current) * easeProgress
      );

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        // 动画完成，更新引用值
        prevValueRef.current = currentValue;
        prevMaxRef.current = maxValue;
        prevMinRef.current = minValue;
        prevAvgRef.current = avgValue;
      }
    }

    requestAnimationFrame(animate);
  }, [currentValue, maxValue, minValue, avgValue]);

  return (
    <div
      className="min-h-[180px] flex flex-col"
      style={{
        backgroundColor: "var(--bg-card)",
        borderRadius: '12px',
        border: '1px solid var(--hairline-soft)',
        borderTop: `2px solid ${config.color}`,
        padding: '15px',
      }}
    >
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-2 flex-shrink-0" style={{ gap: '8px' }}>
        <h3 style={{
          fontSize: '1.1rem',
          fontWeight: '500',
          color: "var(--text-primary)",
          flexShrink: 0,
        }}>
          {config.title}
        </h3>
        <div style={{
          fontSize: '0.75rem',
          fontFamily: "\"'Roboto Mono', 'Consolas', 'Monaco', monospace\"",
          color: config.color,
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          flex: 1,
          minWidth: 0,
          textAlign: 'right',
        }}>
          <span>Max: <strong>{animatedMax.toFixed(config.decimals)}</strong>{config.unit}</span>
          <span style={{ margin: '0 4px' }}>|</span>
          <span>Min: <strong>{animatedMin.toFixed(config.decimals)}</strong>{config.unit}</span>
          <span style={{ margin: '0 4px' }}>|</span>
          <span>Avg: <strong>{animatedAvg.toFixed(config.decimals)}</strong>{config.unit}</span>
        </div>
      </div>

      {/* 图表区域 - 占据主要空间 */}
      <div className="flex-1 min-h-0" style={{ minHeight: '180px' }}>
        <RealTimeChart data={data} timestamps={timestamps} config={config} />
      </div>

      {/* 当前值 - 带平滑动画 */}
      <div className="mt-2 flex-shrink-0 flex items-baseline">
        <span
          style={{
            fontSize: '1.1rem',
            fontWeight: 'bold',
            color: config.color,
            transition: 'color 0.2s ease',
          }}
        >
          {animatedValue.toFixed(config.decimals)}
        </span>
        <span style={{
          marginLeft: '4px',
          fontSize: '0.7rem',
          color: "var(--text-secondary)",
        }}>
          {config.unit}
        </span>
        {note && (
          <span style={{
            marginLeft: '8px',
            fontSize: '0.65rem',
            color: "var(--text-muted)",
          }}>
            {note}
          </span>
        )}
      </div>
    </div>
  );
}
