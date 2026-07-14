import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';

interface TooltipData {
  title: string;
  time: string;
  value: string;
  unit: string;
}

interface ChartTooltipProps {
  data: TooltipData | null;
  position: { x: number; y: number } | null;
}

export default function ChartTooltip({ data, position }: ChartTooltipProps) {
  const { t } = useTranslation();
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!position || !data) return;

    // 2秒后自动隐藏
    const timer = setTimeout(() => {
      // 父组件会通过设置data为null来隐藏
    }, 2000);

    return () => clearTimeout(timer);
  }, [position, data]);

  if (!data || !position) return null;

  return (
    <div
      ref={tooltipRef}
      style={{
        position: 'fixed',
        left: position.x + 15,
        top: position.y + 15,
        backgroundColor: 'rgba(20, 20, 20, 0.9)',
        border: '1px solid rgba(0, 212, 255, 0.5)',
        borderRadius: '8px',
        color: "var(--text-primary)",
        padding: '8px 12px',
        fontSize: '12px',
        fontFamily: "'Consolas', 'Monaco', monospace",
        zIndex: 1000,
        pointerEvents: 'none',
      }}
    >
      <div style={{ lineHeight: '1.5' }}>
        <div style={{ color: "var(--accent)", fontWeight: 'bold', marginBottom: '4px' }}>
          {data.title}
        </div>
        <div>{t('stats.time')}: {data.time}</div>
        <div>
          {t('stats.value')}:{' '}
          <span style={{ color: "var(--chart-4)", fontWeight: 'bold' }}>
            {data.value}{data.unit}
          </span>
        </div>
      </div>
    </div>
  );
}
