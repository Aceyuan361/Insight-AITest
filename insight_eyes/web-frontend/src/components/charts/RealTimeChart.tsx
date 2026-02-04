import { useEffect, useRef, useMemo, useCallback, useState } from 'react';
import * as echarts from 'echarts';
import type { MetricCardConfig } from '@/types';

interface RealTimeChartProps {
  data: number[];
  timestamps: string[];
  config: MetricCardConfig;
}

export default function RealTimeChart({ data, timestamps, config }: RealTimeChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const prevDataLengthRef = useRef(0);
  const updateTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 新增：用于平滑动画的插值数据状态
  const [interpolatedData, setInterpolatedData] = useState<number[]>(data);
  const animationFrameRef = useRef<number | null>(null);

  // 清理函数
  useEffect(() => {
    if (!chartRef.current) return;

    // 初始化图表
    chartInstance.current = echarts.init(chartRef.current);

    // 添加窗口resize监听器
    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (updateTimerRef.current) {
        clearTimeout(updateTimerRef.current);
      }
      chartInstance.current?.dispose();
    };
  }, []);

  // 计算X轴刻度间隔（完全复刻桌面版逻辑）
  const xAxisInterval = useMemo(() => {
    const len = data.length;
    if (len <= 20) return 5;
    if (len <= 40) return 10;
    return 15;
  }, [data.length]);

  // 格式化时间戳（HH:mm:ss）
  const formatTime = useCallback((date: Date): string => {
    return date.toLocaleTimeString('zh-CN', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }, []);

  // 解析ISO时间字符串
  const parseTimestamp = useCallback((ts: string): Date => {
    return new Date(ts);
  }, []);

  // 生成X轴刻度数据（动态间隔）
  const xAxisData = useMemo(() => {
    const result: string[] = [];
    for (let i = 0; i < data.length; i += xAxisInterval) {
      if (i < timestamps.length) {
        result.push(formatTime(parseTimestamp(timestamps[i])));
      }
    }
    // 确保最后一个时间点总是显示
    if (timestamps.length > 0 && (result.length === 0 || xAxisInterval * (result.length - 1) < data.length - 1)) {
      const lastIndex = timestamps.length - 1;
      const lastTime = formatTime(parseTimestamp(timestamps[lastIndex]));
      if (result.length === 0 || result[result.length - 1] !== lastTime) {
        result.push(lastTime);
      }
    }
    return result;
  }, [timestamps, data.length, xAxisInterval, formatTime, parseTimestamp]);

  // 计算Y轴自适应范围（根据实际数据范围调整，便于观察小波动）
  const yAxisRange = useMemo(() => {
    if (data.length === 0) {
      return { min: 0, max: 100 };
    }

    const valid = data.filter(v => v != null && !isNaN(v));
    if (valid.length === 0) {
      return { min: 0, max: 100 };
    }

    const min = Math.min(...valid);
    const max = Math.max(...valid);

    // 如果配置了固定范围，使用配置值
    if (config.yMin !== undefined && config.yMax !== undefined) {
      // 对于固定范围（如CPU 0-100），检查是否需要自适应
      // 如果数据范围小于配置范围的20%，启用自适应模式以便观察小波动
      const range = config.yMax - config.yMin;
      const dataRange = max - min;

      if (dataRange < range * 0.2) {
        // 数据范围太小，启用自适应（保留10%的边距）
        const padding = dataRange * 0.1 || (max * 0.1);
        return {
          min: Math.max(0, Math.floor((min - padding) / 10) * 10), // 向下取整到10的倍数
          max: Math.ceil((max + padding) / 10) * 10,  // 向上取整到10的倍数
        };
      }
    }

    // 没有固定范围，完全自适应（保留10%的边距）
    const padding = (max - min) * 0.1 || 1;
    return {
      min: Math.floor((min - padding) / 10) * 10,
      max: Math.ceil((max + padding) / 10) * 10,
    };
  }, [data, config.yMin, config.yMax]);

  // 计算统计数据（Max | Min | Avg）
  const statistics = useMemo(() => {
    if (data.length === 0) return null;
    const valid = data.filter(v => v != null && !isNaN(v));
    if (valid.length === 0) return null;

    const max = Math.max(...valid);
    const min = Math.min(...valid);
    const avg = valid.reduce((a, b) => a + b, 0) / valid.length;

    return { max, min, avg };
  }, [data]);

  // 优化：使用 throttle 避免频繁更新
  useEffect(() => {
    // 清除之前的定时器
    if (updateTimerRef.current) {
      clearTimeout(updateTimerRef.current);
    }

    // 使用 throttle 控制更新频率（最多每50ms更新一次）
    updateTimerRef.current = setTimeout(() => {
      if (!chartInstance.current) return;

      // 将所有时间戳格式化为X轴数据（完整数据，不稀疏）
      const xAxisFullData = timestamps.map(ts => formatTime(parseTimestamp(ts)));

      const option: echarts.EChartsOption = {
      // 网格布局（完全复刻桌面版）
      grid: {
        top: 35,
        left: 55,
        right: 20,
        bottom: 30,
      },

      // X轴时间刻度（完整数据）
      xAxis: {
        type: 'category',
        data: xAxisFullData,
        axisLabel: {
          color: '#888888',
          fontSize: 11,
          fontFamily: 'Arial, sans-serif',
          interval: xAxisInterval - 1, // 动态间隔控制显示密度
        },
        axisLine: {
          lineStyle: { color: '#444' }
        },
        axisTick: {
          lineStyle: { color: '#444' }
        },
      },

      // Y轴配置（支持自适应范围，便于观察小波动）
      yAxis: {
        type: 'value',
        min: yAxisRange.min,
        max: yAxisRange.max,
        splitLine: {
          show: true,
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.08)',
          },
        },
        axisLabel: {
          color: '#888888',
          fontSize: 11,
          fontFamily: 'Arial, sans-serif',
          formatter: (value: number) => value.toFixed(config.decimals) + config.unit,
        },
        axisLine: {
          lineStyle: { color: '#444' }
        },
        axisTick: {
          lineStyle: { color: '#444' }
        },
      },

      // Tooltip配置（完全复刻桌面版交互体验）
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'line',
          lineStyle: {
            color: '#444',
            type: 'dashed',
            width: 1,
          },
        },
        backgroundColor: 'rgba(18, 24, 36, 0.95)',
        borderColor: '#1a1f2e',
        borderWidth: 1,
        textStyle: {
          color: '#e0e6ed',
        },
        padding: [12, 16],
        formatter: (params: any) => {
          if (!params || params.length === 0) return '';
          const point = params[0];
          const dataIndex = point.dataIndex;

          // 获取准确的时间戳
          let timeStr = '';
          if (dataIndex >= 0 && dataIndex < timestamps.length) {
            timeStr = formatTime(parseTimestamp(timestamps[dataIndex]));
          }

          const value = point.value as number;
          const unit = config.unit;

          return `
            <div style="padding: 4px 0;">
              <div style="color: #94a3b8; font-size: 12px; margin-bottom: 6px;">${config.title}</div>
              <div style="margin: 4px 0;">
                <span style="color: #64748b;">时间:</span>
                <span style="color: #e0e6ed; margin-left: 8px; font-family: 'Roboto Mono', monospace;">${timeStr}</span>
              </div>
              <div>
                <span style="color: #64748b;">数值:</span>
                <span style="color: ${config.color}; margin-left: 8px; font-family: 'Roboto Mono', monospace; font-weight: 500;">${value.toFixed(config.decimals)}${unit}</span>
              </div>
            </div>
          `;
        },
      },

      // 系列配置（添加数据点高亮效果和流畅动画）
      series: [
        {
          type: 'line',
          data: data,
          smooth: true,
          smoothMonotone: 'x',
          symbol: 'none', // 默认不显示数据点
          sampling: 'lttb', // 降采样优化性能
          showSymbol: false, // 不显示普通数据点
          animation: true, // 启用动画
          animationDuration: 300, // 动画时长300ms
          animationEasing: 'cubicOut', // 使用平滑的缓动函数
          animationEasingUpdate: 'quarticInOut', // 更新动画缓动
          animationDurationUpdate: 200, // 更新动画时长

          // 线条样式（完全复刻桌面版）
          lineStyle: {
            color: config.color,
            width: 2.5,
          },

          // 渐变填充（完全复刻桌面版）
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: hexToRgba(config.color, 0.35) },
              { offset: 1, color: hexToRgba(config.color, 0) },
            ]),
          },

          // 数据点高亮效果（完全复刻桌面版悬停体验）
          emphasis: {
            focus: 'series',
            scale: true,
            itemStyle: {
              color: config.color,
              borderColor: config.color,
              borderWidth: 2,
              shadowColor: config.color,
              shadowBlur: 8,
            },
          },

          // 默认不显示 markPoint（由 tooltip 控制悬停点显示）
          markPoint: {
            data: [],
            symbol: 'circle',
            symbolSize: 10,
            itemStyle: {
              color: config.color,
              borderColor: '#fff',
              borderWidth: 2,
              shadowColor: config.color,
              shadowBlur: 10,
            },
            label: { show: false },
            silent: false, // 允许响应鼠标事件
          },

          z: 1,
        },
      ],

      // 全局动画配置（流畅过渡效果）
      animation: true,
      animationThreshold: 8, // 超过8个数据点才启用动画优化
      animationDuration: 300,
      animationEasing: 'cubicOut',
      animationEasingUpdate: 'quarticInOut',
      animationDurationUpdate: 200,

      // 渐进式渲染（让大数据集更流畅）
      progressive: 200,
      progressiveThreshold: 1000,
      };

      // 使用 notMerge 模式更新配置
      chartInstance.current.setOption(option, { notMerge: false, lazyUpdate: true });
    }, 50); // 50ms throttle，避免过于频繁的更新
  }, [data, timestamps, xAxisInterval, config, formatTime, parseTimestamp]);

  // 辅助函数：十六进制颜色转rgba
  function hexToRgba(hex: string, alpha: number): string {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <div ref={chartRef} style={{ width: '100%', height: '100%', minHeight: '80px' }} />
    </div>
  );
}
