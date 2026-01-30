import { useMonitoringStore } from '@/store/monitoringStore';
import AlarmRecords from '@/components/widgets/AlarmRecords';

export default function ConfigPanel() {
  const { isMonitoring } = useMonitoringStore();

  // 监控指标配置 - 匹配桌面版颜色和顺序
  const metrics = [
    { key: 'cpu', label: 'CPU', color: '#00f2ff' },      // 青色
    { key: 'memory', label: '内存', color: '#9370DB' },  // 紫色
    { key: 'fps', label: 'FPS', color: '#ffb400' },      // 橙色
    { key: 'network_up', label: '网络上行', color: '#00ff87' }, // 绿色
    { key: 'network_down', label: '网络下行', color: '#00BFFF' }, // 蓝色
  ];

  // 告警阈值配置 - 匹配桌面版格式
  const thresholds = [
    { label: 'FPS低于', value: '30', unit: 'fps' },
    { label: '内存超过', value: '500', unit: 'MB' },
    { label: 'CPU超过', value: '80', unit: '%' },
    { label: '温度超过', value: '45.00', unit: '°C' },
  ];

  return (
    <div style={{
      padding: '12px',
      display: 'flex',
      flexDirection: 'column',
      gap: '16px',
    }}>
      {/* === 标题 === */}
      <div style={{
        fontSize: '16pt',
        fontWeight: '700',
        color: '#00d4ff',
        padding: '4px 0px',
      }}>
        采集配置
      </div>

      {/* === 采集配置 === */}
      <div style={{
        backgroundColor: '#0a0e17',
        border: '1px solid #1a1f2e',
        borderRadius: '8px',
        padding: '12px',
      }}>
        <div style={{
          fontSize: '11pt',
          fontWeight: '600',
          color: '#7dd3fc',
          marginBottom: '8px',
        }}>
          采集配置
        </div>

        {/* 采样频率 - 静态文本 */}
        <div style={{
          fontSize: '10pt',
          color: '#94a3b8',
          padding: '4px 8px',
          display: 'flex',
          justifyContent: 'space-between',
        }}>
          <span>采样频率</span>
          <span style={{ color: '#e0e6ed' }}>1s</span>
        </div>
      </div>

      {/* === 监控指标 === */}
      <div style={{
        backgroundColor: '#0a0e17',
        border: '1px solid #1a1f2e',
        borderRadius: '8px',
        padding: '12px',
      }}>
        <div style={{
          fontSize: '11pt',
          fontWeight: '600',
          color: '#7dd3fc',
          marginBottom: '8px',
        }}>
          监控指标
        </div>

        {/* 色块显示 - 匹配桌面版 */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
          {metrics.map((metric) => (
            <div
              key={metric.key}
              style={{
                backgroundColor: 'transparent',
                color: metric.color,
                padding: '6px 8px',
                borderRadius: '4px',
                fontSize: '10pt',
                fontWeight: '600',
                textAlign: 'center',
                border: `1px solid ${metric.color}`,
              }}
            >
              {metric.label}
            </div>
          ))}
        </div>
      </div>

      {/* === 告警阈值 === */}
      <div style={{
        backgroundColor: '#0a0e17',
        border: '1px solid #1a1f2e',
        borderRadius: '8px',
        padding: '12px',
      }}>
        <div style={{
          fontSize: '11pt',
          fontWeight: '600',
          color: '#7dd3fc',
          marginBottom: '8px',
        }}>
          告警阈值
        </div>

        {/* 静态文本显示 - 匹配桌面版 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {thresholds.map((threshold) => (
            <div
              key={threshold.label}
              style={{
                fontSize: '10pt',
                color: '#94a3b8',
                padding: '4px 8px',
                display: 'flex',
                justifyContent: 'space-between',
              }}
            >
              <span>{threshold.label}</span>
              <span style={{ color: '#e0e6ed' }}>
                {threshold.value} {threshold.unit}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* === 告警记录 === */}
      <div style={{
        backgroundColor: '#0a0e17',
        border: '1px solid #1a1f2e',
        borderRadius: '8px',
        padding: '12px',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
      }}>
        <AlarmRecords />
      </div>
    </div>
  );
}
