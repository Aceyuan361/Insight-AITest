import { useState, useEffect } from 'react';
import { useMonitoringStore } from '@/store/monitoringStore';
import { deviceApi } from '@/services/api';
import { getMockAppsForDevice, getAppName } from '@/services/mockApps';
import type { AppInfo } from '@/types';

export default function DeviceSelectionPanel() {
  const { devices, selectedDevice, selectDevice, isMonitoring, currentSession, batteryInfo, setDevices } = useMonitoringStore();
  const [apps, setApps] = useState<AppInfo[]>([]);
  const [selectedAppPackage, setSelectedAppPackage] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 加载设备列表
  const loadDevices = async () => {
    setLoading(true);
    setError(null);
    try {
      const deviceList = await deviceApi.getDevices();
      setDevices(deviceList);
    } catch (err) {
      console.error('Failed to load devices:', err);
      setError('无法加载设备列表，请检查后端服务是否正常运行');
    } finally {
      setLoading(false);
    }
  };

  // 当选择的设备改变时，加载应用列表
  useEffect(() => {
    if (selectedDevice) {
      const deviceApps = getMockAppsForDevice(selectedDevice);
      setApps(deviceApps);
    }
  }, [selectedDevice]);

  // 从会话中获取应用名称
  const currentAppName = currentSession?.app_name ||
    (selectedAppPackage ? getAppName(selectedAppPackage) : '');
  const currentDevice = devices.find(d => d.device_id === selectedDevice);
  const currentDeviceName = currentDevice?.name || currentSession && devices.find(d => d.device_id === currentSession.device_id)?.name || '';

  const handleRefresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const deviceList = await deviceApi.refreshDevices();
      setDevices(deviceList);
      // 刷新后重新加载应用列表
      if (selectedDevice) {
        const deviceApps = getMockAppsForDevice(selectedDevice);
        setApps(deviceApps);
      }
    } catch (err) {
      console.error('Failed to refresh devices:', err);
      setError('刷新设备列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 初始加载
  useEffect(() => {
    loadDevices();
  }, []);

  const handleDeviceChange = (deviceId: string) => {
    selectDevice(deviceId);
    setSelectedAppPackage('');
  };

  const handleAppChange = (appPackage: string) => {
    setSelectedAppPackage(appPackage);
  };

  const handleStartStopMonitoring = async () => {
    if (isMonitoring) {
      await useMonitoringStore.getState().stopMonitoring();
    } else {
      if (selectedDevice && selectedAppPackage) {
        const device = devices.find(d => d.device_id === selectedDevice);
        const platform = device?.type || 'android';
        const appName = getAppName(selectedAppPackage);
        await useMonitoringStore.getState().startMonitoring(
          selectedDevice,
          selectedAppPackage,
          platform
        );
        // 更新会话中的应用名称
        if (useMonitoringStore.getState().currentSession) {
          useMonitoringStore.getState().currentSession!.app_name = appName;
        }
      }
    }
  };

  const getPlatformIcon = (type: string) => {
    return type === 'android' ? '🤖' : type === 'ios' ? '🍎' : '📱';
  };

  const getStatusText = (status: string) => {
    const statusMap: Record<string, string> = {
      'online': '在线',
      'offline': '离线',
      'unauthorized': '未授权',
    };
    return statusMap[status] || status;
  };

  const canStart = selectedDevice && selectedAppPackage && !isMonitoring;

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
        监控目标
      </div>

      {/* 错误提示 */}
      {error && (
        <div style={{
          padding: '8px 12px',
          backgroundColor: 'rgba(127, 29, 29, 0.3)',
          border: '1px solid #dc2626',
          borderRadius: '6px',
          color: '#fca5a5',
          fontSize: '10pt',
        }}>
          {error}
        </div>
      )}

      {/* === 设备选择 === */}
      <div>
        <label style={{
          fontSize: '11pt',
          fontWeight: '600',
          color: '#94a3b8',
          display: 'block',
          marginBottom: '8px',
        }}>
          设备
        </label>
        {isMonitoring && currentDevice ? (
          // 监控中显示设备信息
          <div style={{
            width: '100%',
            backgroundColor: '#121824',
            color: '#e0e6ed',
            border: '1px solid #1a1f2e',
            borderRadius: '6px',
            padding: '10px 12px',
            fontSize: '10pt',
          }}>
            {getPlatformIcon(currentDevice.type)} {currentDevice.name} ({getStatusText(currentDevice.status)})
          </div>
        ) : (
          // 未监控显示下拉框
          <select
            value={selectedDevice || ''}
            onChange={(e) => handleDeviceChange(e.target.value)}
            style={{
              width: '100%',
              backgroundColor: '#121824',
              color: '#e0e6ed',
              border: '1px solid #1a1f2e',
              borderRadius: '6px',
              padding: '10px 12px',
              fontSize: '10pt',
            }}
          >
            <option value="">选择设备...</option>
            {devices.map((device) => (
              <option key={device.device_id} value={device.device_id}>
                {getPlatformIcon(device.type)} {device.name} ({getStatusText(device.status)})
              </option>
            ))}
          </select>
        )}
      </div>

      {/* === 应用选择 === */}
      <div>
        <label style={{
          fontSize: '11pt',
          fontWeight: '600',
          color: '#94a3b8',
          display: 'block',
          marginBottom: '8px',
        }}>
          应用
        </label>
        {isMonitoring && currentAppName ? (
          // 监控中显示应用名称
          <div style={{
            width: '100%',
            backgroundColor: '#121824',
            color: '#e0e6ed',
            border: '1px solid #1a1f2e',
            borderRadius: '6px',
            padding: '10px 12px',
            fontSize: '10pt',
          }}>
            {currentAppName}
          </div>
        ) : (
          // 未监控显示下拉框
          <select
            value={selectedAppPackage}
            onChange={(e) => handleAppChange(e.target.value)}
            disabled={!selectedDevice}
            style={{
              width: '100%',
              backgroundColor: !selectedDevice ? '#1a1f2e' : '#121824',
              color: '#e0e6ed',
              border: '1px solid #1a1f2e',
              borderRadius: '6px',
              padding: '10px 12px',
              fontSize: '10pt',
              opacity: !selectedDevice ? 0.6 : 1,
            }}
          >
            <option value="">选择应用...</option>
            {apps.map((app) => (
              <option key={app.package_name} value={app.package_name}>
                {app.app_name}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* === 当前目标显示 === */}
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
          当前目标
        </div>
        <div style={{
          fontSize: '10pt',
          color: currentDeviceName ? '#e0e6ed' : '#94a3b8',
          padding: '4px 8px',
        }}>
          设备: {currentDeviceName || '未选择'}
        </div>
        <div style={{
          fontSize: '10pt',
          color: currentAppName ? '#e0e6ed' : '#94a3b8',
          padding: '4px 8px',
        }}>
          应用: {currentAppName || '未选择'}
        </div>
      </div>

      {/* === 控制按钮 === */}
      <div style={{ display: 'flex', gap: '12px' }}>
        <button
          onClick={handleStartStopMonitoring}
          disabled={!canStart && !isMonitoring}
          style={{
            flex: 1,
            backgroundColor: isMonitoring ? '#00BFFF' : canStart ? '#00d4ff' : '#1a1f2e',
            color: isMonitoring ? '#0a0e17' : canStart ? '#0a0e17' : '#64748b',
            border: 'none',
            borderRadius: '6px',
            padding: '12px 24px',
            fontSize: '11pt',
            fontWeight: '600',
            cursor: canStart || isMonitoring ? 'pointer' : 'not-allowed',
          }}
        >
          {isMonitoring ? '停止监控' : '开始监控'}
        </button>
        <button
          onClick={handleRefresh}
          disabled={loading}
          style={{
            flex: 1,
            backgroundColor: '#1a1f2e',
            color: '#e0e6ed',
            border: '1px solid #2d3748',
            borderRadius: '6px',
            padding: '12px 24px',
            fontSize: '11pt',
            fontWeight: '600',
            opacity: loading ? 0.5 : 1,
          }}
        >
          {loading ? '刷新中...' : '刷新设备'}
        </button>
      </div>

      {/* === 状态显示 === */}
      <div style={{
        fontSize: '10pt',
        color: isMonitoring ? '#22c55e' : '#64748b',
        padding: '8px',
        backgroundColor: '#0a0e17',
        borderRadius: '6px',
        textAlign: 'center',
      }}>
        {isMonitoring ? '● 监控中' : '● 未监控'}
      </div>

      {/* === 电池信息 === */}
      <div style={{
        backgroundColor: '#0a0e17',
        border: '1px solid #1a1f2e',
        borderRadius: '8px',
        padding: '12px',
      }}>
        <div style={{
          fontSize: '11pt',
          fontWeight: '600',
          color: '#00ff87',
          marginBottom: '8px',
        }}>
          电池信息
        </div>
        <div style={{
          fontSize: '10pt',
          color: '#94a3b8',
          padding: '4px 8px',
        }}>
          电量: {batteryInfo.level}%
        </div>
        <div style={{
          fontSize: '10pt',
          color: '#94a3b8',
          padding: '4px 8px',
        }}>
          温度: {batteryInfo.temperature}°C
        </div>
        <div style={{
          fontSize: '10pt',
          color: '#94a3b8',
          padding: '4px 8px',
        }}>
          容量: {batteryInfo.capacity}
        </div>
      </div>
    </div>
  );
}
