import { useEffect, useRef, useMemo } from 'react';
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
  const formatTime = (date: Date): string => {
    return date.toLocaleTimeString('zh-CN', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // 解析ISO时间字符串
  const parseTimestamp = (ts: string): Date => {
    return new Date(ts);
  };

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
  }, [timestamps, data.length, xAxisInterval]);

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

  useEffect(() => {
    if (!chartInstance.current) return;

    const option: echarts.EChartsOption = {
      // 网格布局（完全复刻桌面版）
      grid: {
        top: 35,
        left: 55,
        right: 20,
        bottom: 30,
      },

      // X轴时间刻度（完全复刻桌面版）
      xAxis: {
        type: 'category',
        data: xAxisData,
        axisLabel: {
          color: '#888888',
          fontSize: 11,
          fontFamily: 'Arial, sans-serif',
          interval: xAxisInterval - 1, // 动态间隔
        },
        axisLine: {
          lineStyle: { color: '#444' }
        },
        axisTick: {
          lineStyle: { color: '#444' }
        },
      },

      // Y轴配置
      yAxis: {
        type: 'value',
        min: config.yMin,
        max: config.yMax,
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

      // 系列配置（添加数据点高亮效果）
      series: [
        {
          type: 'line',
          data: data,
          smooth: true,
          smoothMonotone: 'x',
          symbol: 'none', // 默认不显示数据点
          sampling: 'lttb', // 降采样优化性能
          showSymbol: false, // 不显示普通数据点

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

      animation: false,
    };

    chartInstance.current.setOption(option, true);

    // ECharts 的 emphasis 和 tooltip 会自动处理悬停效果
    // 不需要额外的事件监听
  }, [data, xAxisData, timestamps, config, xAxisInterval]);

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

      {/* 统计信息（可选显示） */}
      {statistics && (
        <div style={{
          position: 'absolute',
          top: 8,
          right: 8,
          fontSize: '11px',
          color: config.color,
          fontFamily: "'Roboto Mono', monospace",
          opacity: 0.8,
        }}>
          Max: {statistics.max.toFixed(config.decimals)}{config.unit} | Min: {statistics.min.toFixed(config.decimals)}{config.unit} | Avg: {statistics.avg.toFixed(config.decimals)}{config.unit}
        </div>
      )}
    </div>
  );
}
