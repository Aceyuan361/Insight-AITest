import { useState, useEffect, useRef } from 'react';
import { useMonitoringStore } from '@/store/monitoringStore';
import AlarmRecords from '@/components/widgets/AlarmRecords';
import { configManager } from '@/utils/configManager';

export default function ConfigPanel() {
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
    { key: 'cpu', label: 'CPU', color: '#00f2ff', enabled: true },
    { key: 'memory', label: '内存', color: '#9370DB', enabled: true },
    { key: 'fps', label: 'FPS', color: '#ffb400', enabled: true },
    { key: 'network_up', label: '网络上行', color: '#00ff87', enabled: true },
    { key: 'network_down', label: '网络下行', color: '#00BFFF', enabled: true },
    { key: 'gpu', label: 'GPU', color: '#ff006e', enabled: false },
  ]);

  // 告警阈值配置 - 匹配桌面版
  const [thresholds, setThresholds] = useState({
    fps: 30,
    memory: 500,
    cpu: 80,
    temperature: 45.0,
  });

  // 检测是否为iOS设备（匹配桌面版逻辑）
  const isIOSDevice = () => {
    if (!selectedDevice) return false;
    const device = devices.find(d => d.device_id === selectedDevice);
    return device?.type === 'ios';
  };

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

  // 导出配置
  const handleExportConfig = () => {
    const config = {
      samplingInterval,
      enabledMetrics: metrics.filter(m => m.enabled).map(m => m.key),
      thresholds,
    };

    const configJson = JSON.stringify(config, null, 2);
    const blob = new Blob([configJson], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `insight-eye-config-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // 导入配置
  const handleImportConfig = () => {
    fileInputRef.current?.click();
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

        alert('配置导入成功！');
      } catch (error) {
        alert('配置导入失败：无效的配置文件');
        console.error('Import config error:', error);
      }
    };
    reader.readAsText(file);

    // 重置文件输入，以便可以重复选择同一文件
    e.target.value = '';
  };

  // 重置配置
  const handleResetConfig = () => {
    if (!confirm('确定要重置为默认配置吗？')) {
      return;
    }

    // 重置为默认值
    const defaultInterval = '1s';
    const defaultMetrics = metrics.map(m => ({
      ...m,
      enabled: ['cpu', 'memory', 'fps', 'network_up', 'network_down'].includes(m.key),
    }));
    const defaultThresholds = {
      fps: 30,
      memory: 500,
      cpu: 80,
      temperature: 45.0,
    };

    setSamplingInterval(defaultInterval);
    setStoreSamplingInterval(intervalToMs(defaultInterval));
    setMetrics(defaultMetrics);
    setThresholds(defaultThresholds);

    // 清除localStorage
    localStorage.removeItem('samplingInterval');
    localStorage.removeItem('enabledMetrics');

    // 更新store
    setEnabledMetrics(defaultMetrics.filter(m => m.enabled).map(m => m.key));

    alert('配置已重置为默认值');
  };

  // 打开配置目录（Web版本不支持，提供说明）
  const handleOpenConfigDir = () => {
    alert('配置存储在浏览器 localStorage 中。\n\n如需完全清除配置，请清除浏览器缓存。');
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
        color: '#00d4ff',
        padding: '4px 0px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span>采集配置</span>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={handleExportConfig}
            style={{
              backgroundColor: '#121824',
              color: '#e0e6ed',
              border: '1px solid #1a1f2e',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '10pt',
              cursor: 'pointer',
            }}
            title="导出配置到JSON文件"
          >
            导出配置
          </button>
          <button
            onClick={handleImportConfig}
            style={{
              backgroundColor: '#121824',
              color: '#e0e6ed',
              border: '1px solid #1a1f2e',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '10pt',
              cursor: 'pointer',
            }}
            title="从JSON文件导入配置"
          >
            导入配置
          </button>
          <button
            onClick={handleResetConfig}
            style={{
              backgroundColor: '#ef4444',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '10pt',
              cursor: 'pointer',
            }}
            title="重置为默认配置"
          >
            重置配置
          </button>
          <button
            onClick={handleOpenConfigDir}
            style={{
              backgroundColor: '#121824',
              color: '#e0e6ed',
              border: '1px solid #1a1f2e',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '10pt',
              cursor: 'pointer',
            }}
            title="查看配置存储位置"
          >
            配置说明
          </button>
        </div>
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

        {/* 采样频率 - 下拉选择（匹配桌面版） */}
        <div style={{
          fontSize: '10pt',
          color: '#94a3b8',
          padding: '4px 8px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <span>采样频率</span>
          <select
            value={samplingInterval}
            onChange={(e) => handleSamplingIntervalChange(e.target.value)}
            disabled={isMonitoring}
            style={{
              backgroundColor: '#121824',
              color: '#e0e6ed',
              border: '1px solid #1a1f2e',
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

        {/* 复选框样式 - 匹配桌面版 */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
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
                  color: metric.enabled ? metric.color : '#64748b',
                  fontSize: '10pt',
                  fontWeight: '500',
                }}>
                  {metric.label}
                  {isGpuOnIOS && (
                    <span style={{ fontSize: '9pt', color: '#94a3b8', marginLeft: '4px' }}>
                      (iOS不支持)
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

        {/* 阈值输入 - 匹配桌面版 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {/* FPS */}
          <div style={{
            fontSize: '10pt',
            color: '#94a3b8',
            padding: '4px 8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span>FPS低于</span>
            <input
              type="number"
              value={thresholds.fps}
              onChange={(e) => setThresholds({ ...thresholds, fps: parseInt(e.target.value) })}
              disabled={isMonitoring}
              min={10}
              max={60}
              style={{
                backgroundColor: '#121824',
                color: '#e0e6ed',
                border: '1px solid #1a1f2e',
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
            color: '#94a3b8',
            padding: '4px 8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span>内存超过</span>
            <input
              type="number"
              value={thresholds.memory}
              onChange={(e) => setThresholds({ ...thresholds, memory: parseInt(e.target.value) })}
              disabled={isMonitoring}
              min={100}
              max={2000}
              style={{
                backgroundColor: '#121824',
                color: '#e0e6ed',
                border: '1px solid #1a1f2e',
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
            color: '#94a3b8',
            padding: '4px 8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span>CPU超过</span>
            <input
              type="number"
              value={thresholds.cpu}
              onChange={(e) => setThresholds({ ...thresholds, cpu: parseInt(e.target.value) })}
              disabled={isMonitoring}
              min={50}
              max={100}
              style={{
                backgroundColor: '#121824',
                color: '#e0e6ed',
                border: '1px solid #1a1f2e',
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
            color: '#94a3b8',
            padding: '4px 8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span>温度超过</span>
            <input
              type="number"
              value={thresholds.temperature}
              onChange={(e) => setThresholds({ ...thresholds, temperature: parseFloat(e.target.value) })}
              disabled={isMonitoring}
              min={30}
              max={60}
              step={0.01}
              style={{
                backgroundColor: '#121824',
                color: '#e0e6ed',
                border: '1px solid #1a1f2e',
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
            backgroundColor: '#121824',
            border: '2px solid #ff006e',
            borderRadius: '12px',
            padding: '24px',
            maxWidth: '500px',
            boxShadow: '0 8px 32px rgba(255, 0, 110, 0.3)',
          }}>
            <h3 style={{
              color: '#ff006e',
              fontSize: '16pt',
              fontWeight: '700',
              marginBottom: '16px',
              marginTop: 0,
            }}>
              iOS GPU 监控限制
            </h3>
            <p style={{
              color: '#e0e6ed',
              fontSize: '11pt',
              lineHeight: '1.6',
              marginBottom: '16px',
            }}>
              抱歉，iOS 设备暂不支持 GPU 监控。
            </p>
            <div style={{
              backgroundColor: '#0a0e17',
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '16px',
            }}>
              <div style={{ color: '#94a3b8', fontSize: '10pt', marginBottom: '8px' }}>
                <strong>原因：</strong>
              </div>
              <ul style={{
                color: '#e0e6ed',
                fontSize: '10pt',
                paddingLeft: '20px',
                margin: 0,
              }}>
                <li>iOS 系统 DVT 通道无法获取 GPU 能耗数据</li>
                <li>CLI 能耗命令超时（20+ 秒），不适合实时监控</li>
              </ul>
            </div>
            <div style={{ color: '#94a3b8', fontSize: '10pt', marginBottom: '8px' }}>
              <strong>已启用指标：</strong>
            </div>
            <ul style={{
              color: '#22c55e',
              fontSize: '10pt',
              paddingLeft: '20px',
              margin: 0,
            }}>
              <li>CPU 使用率 ✓</li>
              <li>内存使用 ✓</li>
              <li>FPS（系统刷新率参考）✓</li>
              <li>网络流量（系统级）✓</li>
              <li>电池状态 ✓</li>
            </ul>
            <button
              onClick={() => setShowGpuWarning(false)}
              style={{
                backgroundColor: '#ff006e',
                color: '#ffffff',
                border: 'none',
                borderRadius: '6px',
                padding: '10px 24px',
                fontSize: '11pt',
                fontWeight: '600',
                cursor: 'pointer',
                width: '100%',
              }}
            >
              我知道了
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
