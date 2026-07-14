import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { useMonitoringStore } from '@/modules/performance/store/monitoringStore';
import AlarmRecords from '@/modules/performance/components/widgets/AlarmRecords';
import { configManager } from '@/shared/utils/configManager';
import { useIsMobile } from '@/shared/hooks/useIsMobile';

export default function ConfigPanel() {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const { isMonitoring, selectedDevice, setEnabledMetrics, devices, setSamplingInterval: setStoreSamplingInterval, samplingInterval: storeSamplingInterval } = useMonitoringStore();
  const [samplingInterval, setSamplingInterval] = useState('1s');
  const [showGpuWarning, setShowGpuWarning] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 采样频率字符串到毫秒的映射
  const intervalToMs = (interval: string): number => {
    const mapping: Record<string, number> = {
      '1s': 1000,
      '3s': 3000,
      '5s': 5000,
      '10s': 10000,
    };
    return mapping[interval] || 1000;
  };

  // 毫秒到采样频率字符串的映射
  const msToInterval = (ms: number): string => {
    if (ms === 1000) return '1s';
    if (ms === 3000) return '3s';
    if (ms === 5000) return '5s';
    if (ms === 10000) return '10s';
    return '1s';
  };

  // 初始化采样频率
  useEffect(() => {
    setSamplingInterval(msToInterval(storeSamplingInterval));
  }, [storeSamplingInterval]);

  // 处理采样频率变化
  const handleSamplingIntervalChange = (value: string) => {
    setSamplingInterval(value);
    setStoreSamplingInterval(intervalToMs(value));
    // 保存到localStorage
    configManager.saveSamplingInterval(value);
  };

  // 监控指标配置 - 匹配桌面版
  const [metrics, setMetrics] = useState([
    { key: 'cpu', label: t('config.metrics.cpu'), color: "var(--accent)", enabled: true },
    { key: 'memory', label: t('config.metrics.memory'), color: 'var(--chart-2)', enabled: true },
    { key: 'fps', label: t('config.metrics.fps'), color: "var(--chart-3)", enabled: true },
    { key: 'network_up', label: t('config.metrics.networkUp'), color: "var(--chart-4)", enabled: true },
    { key: 'network_down', label: t('config.metrics.networkDown'), color: 'var(--chart-5)', enabled: true },
    { key: 'gpu', label: t('config.metrics.gpu'), color: "var(--chart-6)", enabled: false },
  ]);

  // 告警阈值配置 - 匹配桌面版
  const [thresholds, setThresholds] = useState(() => {
    // 从 localStorage 加载保存的阈值
    return configManager.getAlertThresholds();
  });

  // 处理阈值变化
  const handleThresholdChange = (key: string, value: number) => {
    const newThresholds = { ...thresholds, [key]: value };
    setThresholds(newThresholds);
    // 保存到 localStorage
    configManager.saveAlertThresholds(newThresholds);
  };

  // 检测是否为iOS设备（匹配桌面版逻辑）
  const isIOSDevice = () => {
    if (!selectedDevice) return false;
    const device = devices.find(d => d.device_id === selectedDevice);
    return device?.type === 'ios';
  };

  // 当切换设备时，动态更新 GPU 选项的状态
  // 如果切换到 iOS 设备且 GPU 已启用，则自动禁用
  // 如果切换到 Android 设备且 GPU 被禁用，则自动启用（恢复之前的状态）
  useEffect(() => {
    if (!selectedDevice) return;

    const isIOS = isIOSDevice();
    const gpuMetric = metrics.find(m => m.key === 'gpu');

    if (isIOS && gpuMetric?.enabled) {
      // 切换到 iOS 设备，禁用 GPU
      const updatedMetrics = metrics.map(m =>
        m.key === 'gpu' ? { ...m, enabled: false } : m
      );
      setMetrics(updatedMetrics);
      const enabledIds = updatedMetrics.filter(m => m.enabled).map(m => m.key);
      setEnabledMetrics(enabledIds);
      configManager.saveEnabledMetrics(enabledIds);
    } else if (!isIOS && gpuMetric && !gpuMetric.enabled) {
      // 切换到 Android 设备，如果 GPU 之前被禁用，则恢复启用（可选）
      // 这里我们保持用户的配置，只移除 iOS 的限制
      const updatedMetrics = metrics.map(m =>
        m.key === 'gpu' ? { ...m, enabled: true } : m
      );
      setMetrics(updatedMetrics);
      const enabledIds = updatedMetrics.filter(m => m.enabled).map(m => m.key);
      setEnabledMetrics(enabledIds);
      configManager.saveEnabledMetrics(enabledIds);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDevice]); // 监听设备切换

  // 初始化：从localStorage加载保存的配置
  useEffect(() => {
    // 只在组件首次挂载时加载
    const savedInterval = configManager.getSamplingInterval();
    const savedMetrics = configManager.getEnabledMetrics();

    // 恢复采样频率
    if (savedInterval) {
      setSamplingInterval(savedInterval);
      setStoreSamplingInterval(intervalToMs(savedInterval));
    }

    // 恢复启用的指标
    if (savedMetrics && savedMetrics.length > 0) {
      setMetrics(prevMetrics =>
        prevMetrics.map(m => ({
          ...m,
          enabled: savedMetrics.includes(m.key),
        }))
      );
      setEnabledMetrics(savedMetrics);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);  // 空依赖数组，仅在挂载时执行

  const handleMetricToggle = (key: string) => {
    // iOS GPU限制检查（匹配桌面版第803-830行）
    if (key === 'gpu' && isIOSDevice()) {
      // 显示iOS GPU限制警告
      setShowGpuWarning(true);
      return;  // 阻止启用GPU
    }

    const updatedMetrics = metrics.map(m =>
      m.key === key ? { ...m, enabled: !m.enabled } : m
    );
    setMetrics(updatedMetrics);

    // 关键联动：更新store中的启用指标列表
    const enabledIds = updatedMetrics.filter(m => m.enabled).map(m => m.key);
    setEnabledMetrics(enabledIds);

    // 保存到localStorage
    configManager.saveEnabledMetrics(enabledIds);
  };

  // 处理文件选择
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const config = JSON.parse(event.target?.result as string);

        // 应用配置
        if (config.samplingInterval) {
          setSamplingInterval(config.samplingInterval);
          setStoreSamplingInterval(intervalToMs(config.samplingInterval));
          configManager.saveSamplingInterval(config.samplingInterval);
        }

        if (config.enabledMetrics && Array.isArray(config.enabledMetrics)) {
          const updatedMetrics = metrics.map(m => ({
            ...m,
            enabled: config.enabledMetrics.includes(m.key),
          }));
          setMetrics(updatedMetrics);
          setEnabledMetrics(config.enabledMetrics);
          configManager.saveEnabledMetrics(config.enabledMetrics);
        }

        if (config.thresholds) {
          setThresholds(config.thresholds);
        }

        toast.success(t('dialogs.operationSuccess'));
      } catch (error) {
        toast.error(t('dialogs.operationFailed'));
        console.error('Import config error:', error);
      }
    };
    reader.readAsText(file);

    // 重置文件输入，以便可以重复选择同一文件
    e.target.value = '';
  };

  return (
    <div style={{
      padding: '12px',
      display: 'flex',
      flexDirection: 'column',
      gap: '16px',
    }}>
      {/* 隐藏的文件输入 */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />

      {/* === 标题 === */}
      <div style={{
        fontSize: '16pt',
        fontWeight: '700',
        color: "var(--accent)",
        padding: '4px 0px',
      }}>
        {t('config.title')}
      </div>

      {/* === 采集配置 === */}
      <div style={{
        backgroundColor: "var(--bg-base)",
        border: '1px solid var(--bg-card)',
        borderRadius: '8px',
        padding: '12px',
      }}>
        <div style={{
          fontSize: '11pt',
          fontWeight: '600',
          color: 'var(--accent)',
          marginBottom: '8px',
        }}>
          {t('config.title')}
        </div>

        {/* 采样频率 - 下拉选择（匹配桌面版） */}
        <div style={{
          fontSize: '10pt',
          color: "var(--text-secondary)",
          padding: '4px 8px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <span>{t('config.samplingRate')}</span>
          <select
            value={samplingInterval}
            onChange={(e) => handleSamplingIntervalChange(e.target.value)}
            disabled={isMonitoring}
            style={{
              backgroundColor: "var(--bg-card)",
              color: "var(--text-primary)",
              border: '1px solid var(--bg-card)',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '10pt',
              cursor: isMonitoring ? 'not-allowed' : 'pointer',
              opacity: isMonitoring ? 0.5 : 1,
            }}
          >
            <option value="1s">1s</option>
            <option value="3s">3s</option>
            <option value="5s">5s</option>
            <option value="10s">10s</option>
          </select>
        </div>
      </div>

      {/* === 监控指标 === */}
      <div style={{
        backgroundColor: "var(--bg-base)",
        border: '1px solid var(--bg-card)',
        borderRadius: '8px',
        padding: '12px',
      }}>
        <div style={{
          fontSize: '11pt',
          fontWeight: '600',
          color: 'var(--accent)',
          marginBottom: '8px',
        }}>
          {t('config.monitoringMetrics')}
        </div>

        {/* 复选框样式 - 匹配桌面版 */}
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: '8px' }}>
          {metrics.map((metric) => {
            const isIOS = isIOSDevice();
            const isGpuOnIOS = metric.key === 'gpu' && isIOS;

            return (
              <label
                key={metric.key}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  cursor: (isMonitoring || isGpuOnIOS) ? 'not-allowed' : 'pointer',
                  opacity: (isMonitoring || isGpuOnIOS) ? 0.6 : 1,
                  padding: '4px',
                }}
              >
                <input
                  type="checkbox"
                  checked={metric.enabled}
                  onChange={() => !isMonitoring && handleMetricToggle(metric.key)}
                  disabled={isMonitoring || isGpuOnIOS}
                  style={{
                    width: '18px',
                    height: '18px',
                    marginRight: '8px',
                    cursor: (isMonitoring || isGpuOnIOS) ? 'not-allowed' : 'pointer',
                    accentColor: metric.color,
                  }}
                />
                <span style={{
                  color: metric.enabled ? metric.color : "var(--text-muted)",
                  fontSize: '10pt',
                  fontWeight: '500',
                }}>
                  {metric.label}
                  {isGpuOnIOS && (
                    <span style={{ fontSize: '9pt', color: "var(--text-secondary)", marginLeft: '4px' }}>
                      ({t('device.iosNotSupported')})
                    </span>
                  )}
                </span>
              </label>
            );
          })}
        </div>
      </div>

      {/* === 告警阈值 === */}
      <div style={{
        backgroundColor: "var(--bg-base)",
        border: '1px solid var(--bg-card)',
        borderRadius: '8px',
        padding: '12px',
      }}>
        <div style={{
          fontSize: '11pt',
          fontWeight: '600',
          color: 'var(--accent)',
          marginBottom: '8px',
        }}>
          {t('config.alertThresholds')}
        </div>

        {/* 阈值输入 - 匹配桌面版 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {/* FPS */}
          <div style={{
            fontSize: '10pt',
            color: "var(--text-secondary)",
            padding: '4px 8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span>{t('config.alerts.fpsBelow')}</span>
            <input
              type="number"
              value={thresholds.fps}
              onChange={(e) => handleThresholdChange('fps', parseInt(e.target.value))}
              disabled={isMonitoring}
              min={10}
              max={60}
              style={{
                backgroundColor: "var(--bg-card)",
                color: "var(--text-primary)",
                border: '1px solid var(--bg-card)',
                borderRadius: '6px',
                padding: '4px 8px',
                width: '80px',
                fontSize: '10pt',
              }}
            />
            <span>fps</span>
          </div>

          {/* 内存 */}
          <div style={{
            fontSize: '10pt',
            color: "var(--text-secondary)",
            padding: '4px 8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span>{t('config.alerts.memoryAbove')}</span>
            <input
              type="number"
              value={thresholds.memory}
              onChange={(e) => handleThresholdChange('memory', parseInt(e.target.value))}
              disabled={isMonitoring}
              min={100}
              max={2000}
              style={{
                backgroundColor: "var(--bg-card)",
                color: "var(--text-primary)",
                border: '1px solid var(--bg-card)',
                borderRadius: '6px',
                padding: '4px 8px',
                width: '80px',
                fontSize: '10pt',
              }}
            />
            <span>MB</span>
          </div>

          {/* CPU */}
          <div style={{
            fontSize: '10pt',
            color: "var(--text-secondary)",
            padding: '4px 8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span>{t('config.alerts.cpuAbove')}</span>
            <input
              type="number"
              value={thresholds.cpu}
              onChange={(e) => handleThresholdChange('cpu', parseInt(e.target.value))}
              disabled={isMonitoring}
              min={50}
              max={100}
              style={{
                backgroundColor: "var(--bg-card)",
                color: "var(--text-primary)",
                border: '1px solid var(--bg-card)',
                borderRadius: '6px',
                padding: '4px 8px',
                width: '80px',
                fontSize: '10pt',
              }}
            />
            <span>%</span>
          </div>

          {/* 温度 */}
          <div style={{
            fontSize: '10pt',
            color: "var(--text-secondary)",
            padding: '4px 8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span>{t('config.alerts.temperatureAbove')}</span>
            <input
              type="number"
              value={thresholds.temperature}
              onChange={(e) => handleThresholdChange('temperature', parseFloat(e.target.value))}
              disabled={isMonitoring}
              min={30}
              max={60}
              step={0.01}
              style={{
                backgroundColor: "var(--bg-card)",
                color: "var(--text-primary)",
                border: '1px solid var(--bg-card)',
                borderRadius: '6px',
                padding: '4px 8px',
                width: '80px',
                fontSize: '10pt',
              }}
            />
            <span>°C</span>
          </div>
        </div>
      </div>

      {/* === 告警记录 === */}
      <div style={{
        backgroundColor: "var(--bg-base)",
        border: '1px solid var(--bg-card)',
        borderRadius: '8px',
        padding: '12px',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
      }}>
        <AlarmRecords />
      </div>

      {/* iOS GPU限制警告对话框 */}
      {showGpuWarning && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
        }}>
          <div style={{
            backgroundColor: "var(--bg-card)",
            border: '2px solid var(--chart-6)',
            borderRadius: '12px',
            padding: '24px',
            maxWidth: '500px',
            boxShadow: '0 8px 32px rgba(255, 0, 110, 0.3)',
          }}>
            <h3 style={{
              color: "var(--chart-6)",
              fontSize: '16pt',
              fontWeight: '700',
              marginBottom: '16px',
              marginTop: 0,
            }}>
              {t('device.iosGpuWarningTitle')}
            </h3>
            <p style={{
              color: "var(--text-primary)",
              fontSize: '11pt',
              lineHeight: '1.6',
              marginBottom: '16px',
            }}>
              {t('device.iosGpuWarningMessage')}
            </p>
            <div style={{
              backgroundColor: "var(--bg-base)",
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '16px',
            }}>
              <div style={{ color: "var(--text-secondary)", fontSize: '10pt', marginBottom: '8px' }}>
                <strong>{t('device.iosGpuWarningReason')}</strong>
              </div>
              <ul style={{
                color: "var(--text-primary)",
                fontSize: '10pt',
                paddingLeft: '20px',
                margin: 0,
              }}>
                <li>{t('device.iosGpuWarningReason1')}</li>
                <li>{t('device.iosGpuWarningReason2')}</li>
              </ul>
            </div>
            <div style={{ color: "var(--text-secondary)", fontSize: '10pt', marginBottom: '8px' }}>
              <strong>{t('device.iosGpuWarningAvailable')}</strong>
            </div>
            <ul style={{
              color: "var(--success)",
              fontSize: '10pt',
              paddingLeft: '20px',
              margin: 0,
            }}>
              <li>{t('device.iosGpuWarningFeature1')}</li>
              <li>{t('device.iosGpuWarningFeature2')}</li>
              <li>{t('device.iosGpuWarningFeature3')}</li>
              <li>{t('device.iosGpuWarningFeature4')}</li>
            </ul>
            <button
              onClick={() => setShowGpuWarning(false)}
              style={{
                backgroundColor: "var(--chart-6)",
                color: "var(--text-primary)",
                border: 'none',
                borderRadius: '6px',
                padding: '10px 24px',
                fontSize: '11pt',
                fontWeight: '600',
                cursor: 'pointer',
                width: '100%',
              }}
            >
              {t('device.iosGpuWarningButton')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
