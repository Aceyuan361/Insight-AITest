import { useEffect, useRef, useState, useCallback } from 'react';
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

  // 悬停提示状态
  const [tooltipData, setTooltipData] = useState<{
    title: string;
    time: string;
    value: string;
    unit: string;
  } | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<{ x: number; y: number } | null>(null);
  const hideTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 清除自动隐藏定时器
  const clearHideTimer = useCallback(() => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
  }, []);

  // 设置自动隐藏
  const scheduleHide = useCallback(() => {
    clearHideTimer();
    hideTimerRef.current = setTimeout(() => {
      setTooltipData(null);
      setTooltipPosition(null);
    }, 2000);
  }, [clearHideTimer]);

  useEffect(() => {
    if (!chartRef.current) return;

    // 初始化图表
    chartInstance.current = echarts.init(chartRef.current);

    // 添加鼠标移动事件监听
    const handleMouseMove = (params: any) => {
      if (!params.dataIndex && params.dataIndex !== 0) return;

      const dataIndex = params.dataIndex;
      if (dataIndex < 0 || dataIndex >= data.length) return;

      // 格式化时间
      const date = new Date(timestamps[dataIndex]);
      const timeStr = `${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;

      // 设置提示数据
      setTooltipData({
        title: config.title,
        time: timeStr,
        value: data[dataIndex].toFixed(config.decimals),
        unit: config.unit,
      });

      // 设置提示位置（鼠标位置）
      setTooltipPosition({
        x: params.event.event.clientX,
        y: params.event.event.clientY,
      });

      // 重新安排自动隐藏
      scheduleHide();
    };

    // 鼠标离开图表时隐藏提示
    const handleMouseLeave = () => {
      scheduleHide();
    };

    chartInstance.current.on('mousemove', handleMouseMove);
    chartInstance.current.on('globalout', handleMouseLeave);

    // 添加窗口resize监听器
    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chartInstance.current?.dispose();
      clearHideTimer();
    };
  }, [config, scheduleHide, clearHideTimer]);

  useEffect(() => {
    if (!chartInstance.current) return;

    // 预处理时间戳数据
    const formattedTimestamps = timestamps.map(t => {
      const date = new Date(t);
      return `${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
    });

    const option: echarts.EChartsOption = {
      grid: {
        top: 35,    // 桌面版网格顶部边距
        left: 55,   // 桌面版网格左侧边距
        right: 20,  // 桌面版网格右侧边距
        bottom: 30, // 桌面版网格底部边距
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
            color: 'rgba(255, 255, 255, 0.08)', // 桌面版网格线透明度
          },
        },
        axisLabel: {
          color: '#888888', // 桌面版Y轴标签颜色
          fontSize: 11,     // 桌面版Y轴字体大小
          fontFamily: 'Arial, sans-serif',
        },
      },
      series: [
        {
          type: 'line',
          data: data,
          smooth: true,
          smoothMonotone: 'x', // 抗锯齿优化
          symbol: 'none',
          lineStyle: {
            color: config.color,
            width: 3,  // 增加线条宽度以更突出
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: config.color + '38' }, // 35% 透明度
              { offset: 1, color: config.color + '00' },
            ]),
          },
          z: 1, // 确保线条在下层
        },
      ],
      animation: false,
      // 禁用默认tooltip
      tooltip: {
        show: false,
      },
    };

    chartInstance.current.setOption(option);
  }, [data, timestamps, config.yMin, config.yMax, config.color]);

  // 动态导入ChartTooltip（避免循环依赖）
  const [ChartTooltip, setChartTooltip] = useState<any>(null);
  useEffect(() => {
    import('@/components/widgets/ChartTooltip').then((mod) => {
      setChartTooltip(() => mod.default);
    });
  }, []);

  return (
    <>
      <div ref={chartRef} style={{ width: '100%', height: '100%', minHeight: '80px' }} />
      {ChartTooltip && tooltipData && tooltipPosition && (
        <ChartTooltip
          data={tooltipData}
          position={tooltipPosition}
        />
      )}
    </>
  );
}
