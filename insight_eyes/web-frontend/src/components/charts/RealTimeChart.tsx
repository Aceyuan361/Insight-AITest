import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { MetricCardConfig } from '@/types';

interface RealTimeChartProps {
  data: number[];
  timestamps: string[];
  config: MetricCardConfig;
}

export default function RealTimeChart({ data, timestamps, config }: RealTimeChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

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

  useEffect(() => {
    if (!chartInstance.current) return;

    // 预处理时间戳数据
    const formattedTimestamps = timestamps.map(t => {
      const date = new Date(t);
      return `${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
    });

    const option: echarts.EChartsOption = {
      grid: {
        top: 10,
        left: 10,
        right: 10,
        bottom: 20,
      },
      xAxis: {
        type: 'category',
        data: formattedTimestamps,
        show: false,
      },
      yAxis: {
        type: 'value',
        min: config.yMin,
        max: config.yMax,
        splitLine: {
          show: true,
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.05)',
          },
        },
        axisLabel: {
          color: '#aaaaaa',
          fontSize: 10,
        },
      },
      series: [
        {
          type: 'line',
          data: data,
          smooth: true,
          symbol: 'none',
          lineStyle: {
            color: config.color,
            width: 2,
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: config.color + '40' },
              { offset: 1, color: config.color + '00' },
            ]),
          },
        },
      ],
      animation: false,
    };

    chartInstance.current.setOption(option);
  }, [data, timestamps, config.yMin, config.yMax, config.color]);

  return <div ref={chartRef} className="w-full h-full" />;
}
