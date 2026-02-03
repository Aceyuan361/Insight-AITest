import { useState, useEffect } from 'react';
import { useMonitoringStore } from '@/store/monitoringStore';
import { deviceApi } from '@/services/api';
import type { AppInfo } from '@/types';

// 从包名获取应用名称的辅助函数
function getAppName(packageName: string): string {
  if (!packageName) return '';
  const parts = packageName.split('.');
  // 返回最后一部分作为应用名
  return parts[parts.length - 1] || packageName;
}

export default function DeviceSelectionPanel() {
  const { devices, selectedDevice, selectDevice, isMonitoring, currentSession, batteryInfo, setDevices } = useMonitoringStore();
  const [apps, setApps] = useState<AppInfo[]>([]);
  const [selectedAppPackage, setSelectedAppPackage] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAppNotRunningWarning, setShowAppNotRunningWarning] = useState(false);
  const [showBackgroundAppWarning, setShowBackgroundAppWarning] = useState(false);
  const [pendingAppPackage, setPendingAppPackage] = useState<string | null>(null);
  const [pendingAppName, setPendingAppName] = useState<string>('');
  const [pendingAppPid, setPendingAppPid] = useState<number | undefined>(undefined);

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
    const loadApps = async () => {
      if (selectedDevice) {
        setLoading(true);
        try {
          const deviceApps = await deviceApi.getDeviceApps(selectedDevice);
          setApps(deviceApps);
        } catch (err) {
          console.error('Failed to load apps:', err);
          setApps([]);
        } finally {
          setLoading(false);
        }
      }
    };

    loadApps();
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
        try {
          const deviceApps = await deviceApi.getDeviceApps(selectedDevice);
          setApps(deviceApps);
        } catch (err) {
          console.error('Failed to reload apps:', err);
        }
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
        try {
          // ===== 启动前自动刷新应用列表以获取最新状态 =====
          setLoading(true);
          const latestApps = await deviceApi.getDeviceApps(selectedDevice);
          setApps(latestApps);

          // 检查应用是否在运行（匹配桌面版逻辑）
          const targetApp = latestApps.find(app => app.package_name === selectedAppPackage);
          const device = devices.find(d => d.device_id === selectedDevice);

          // 检查应用是否在运行（iOS 和 Android 统一处理）
          // 注意：iOS 进程检测需要开发者模式，如果未启用，is_running 会是 false
          if (!targetApp || !targetApp.is_running) {
            // 应用未运行，显示警告对话框
            setPendingAppPackage(selectedAppPackage);
            setShowAppNotRunningWarning(true);
            return;
          }

          // ===== 新增：检查应用是否在后台运行（匹配桌面版第1070-1087行）=====
          if (targetApp.status === 'background') {
            // 应用在后台运行，显示警告对话框
            setPendingAppPackage(selectedAppPackage);
            setPendingAppName(targetApp.name);
            setPendingAppPid(targetApp.pid);
            setShowBackgroundAppWarning(true);
            return;
          }

          // 应用正在前台运行，正常启动监控
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
        } catch (error) {
          console.error('刷新应用列表失败:', error);
          // 如果刷新失败，使用现有数据继续检查
          const targetApp = apps.find(app => app.package_name === selectedAppPackage);

          if (!targetApp || !targetApp.is_running) {
            setPendingAppPackage(selectedAppPackage);
            setShowAppNotRunningWarning(true);
            return;
          }

          // 检查后台应用
          if (targetApp.status === 'background') {
            setPendingAppPackage(selectedAppPackage);
            setPendingAppName(targetApp.name);
            setPendingAppPid(targetApp.pid);
            setShowBackgroundAppWarning(true);
            return;
          }

          const device = devices.find(d => d.device_id === selectedDevice);
          const platform = device?.type || 'android';
          const appName = getAppName(selectedAppPackage);
          await useMonitoringStore.getState().startMonitoring(
            selectedDevice,
            selectedAppPackage,
            platform
          );
          if (useMonitoringStore.getState().currentSession) {
            useMonitoringStore.getState().currentSession!.app_name = appName;
          }
        } finally {
          setLoading(false);
        }
      }
    }
  };

  // 取消启动
  const handleCancelStartNotRunning = () => {
    setShowAppNotRunningWarning(false);
    setPendingAppPackage(null);
  };

  // 确认启动后台应用
  const handleConfirmStartBackground = async () => {
    setShowBackgroundAppWarning(false);
    if (selectedDevice && pendingAppPackage) {
      const device = devices.find(d => d.device_id === selectedDevice);
      const platform = device?.type || 'android';
      try {
        await useMonitoringStore.getState().startMonitoring(
          selectedDevice,
          pendingAppPackage,
          platform
        );
        if (useMonitoringStore.getState().currentSession) {
          useMonitoringStore.getState().currentSession!.app_name = pendingAppName;
        }
      } catch (error) {
        console.error('启动监控失败:', error);
      } finally {
        setPendingAppPackage(null);
        setPendingAppName('');
        setPendingAppPid(undefined);
      }
    }
  };

  // 取消启动后台应用
  const handleCancelStartBackground = () => {
    setShowBackgroundAppWarning(false);
    setPendingAppPackage(null);
    setPendingAppName('');
    setPendingAppPid(undefined);
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
                {app.name}
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

      {/* 应用未运行警告对话框 */}
      {showAppNotRunningWarning && (
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
            border: '2px solid #ffb400',
            borderRadius: '12px',
            padding: '24px',
            maxWidth: '500px',
            boxShadow: '0 8px 32px rgba(255, 180, 0, 0.3)',
          }}>
            <h3 style={{
              color: '#ffb400',
              fontSize: '16pt',
              fontWeight: '700',
              marginBottom: '16px',
              marginTop: 0,
            }}>
              应用未运行
            </h3>
            <p style={{
              color: '#e0e6ed',
              fontSize: '11pt',
              lineHeight: '1.6',
              marginBottom: '16px',
            }}>
              没有找到应用正在运行的进程
            </p>
            <div style={{
              backgroundColor: '#0a0e17',
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '16px',
            }}>
              <div style={{ color: '#94a3b8', fontSize: '10pt', marginBottom: '4px' }}>
                应用包名:
              </div>
              <div style={{ color: '#e0e6ed', fontSize: '10pt', fontWeight: '500', wordBreak: 'break-all' }}>
                {pendingAppPackage}
              </div>
            </div>
            <div style={{
              color: '#ffb400',
              fontSize: '10pt',
              marginBottom: '16px',
              padding: '12px',
              backgroundColor: 'rgba(255, 180, 0, 0.1)',
              borderRadius: '6px',
            }}>
              <strong>提示：</strong>请检查应用是否在运行中，然后重试。
            </div>
            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <button
                onClick={handleCancelStartNotRunning}
                style={{
                  backgroundColor: '#3b82f6',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '10px 32px',
                  fontSize: '11pt',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                我知道了
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 后台应用警告对话框 */}
      {showBackgroundAppWarning && (
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
            border: '2px solid #9370DB',  // 紫色边框（区别于未运行警告）
            borderRadius: '12px',
            padding: '24px',
            maxWidth: '500px',
            boxShadow: '0 8px 32px rgba(147, 112, 219, 0.3)',
          }}>
            <h3 style={{
              color: '#9370DB',  // 紫色标题
              fontSize: '16pt',
              fontWeight: '700',
              marginBottom: '16px',
              marginTop: 0,
            }}>
              应用在后台运行
            </h3>
            <p style={{
              color: '#e0e6ed',
              fontSize: '11pt',
              lineHeight: '1.6',
              marginBottom: '16px',
            }}>
              应用正在后台运行（非前台）
            </p>
            <div style={{
              backgroundColor: '#0a0e17',
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '16px',
            }}>
              <div style={{ color: '#94a3b8', fontSize: '10pt', marginBottom: '4px' }}>
                应用名称:
              </div>
              <div style={{ color: '#e0e6ed', fontSize: '10pt', fontWeight: '500' }}>
                {pendingAppName}
              </div>
              <div style={{ color: '#94a3b8', fontSize: '10pt', marginBottom: '4px', marginTop: '8px' }}>
                PID:
              </div>
              <div style={{ color: '#e0e6ed', fontSize: '10pt', fontWeight: '500' }}>
                {pendingAppPid}
              </div>
            </div>
            <div style={{
              color: '#9370DB',
              fontSize: '10pt',
              marginBottom: '16px',
              padding: '12px',
              backgroundColor: 'rgba(147, 112, 219, 0.1)',
              borderRadius: '6px',
            }}>
              <strong>提示：</strong>后台运行时可能无法采集到完整的性能数据。
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={handleCancelStartBackground}
                style={{
                  flex: 1,
                  backgroundColor: '#475569',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '10px 24px',
                  fontSize: '11pt',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                取消
              </button>
              <button
                onClick={handleConfirmStartBackground}
                style={{
                  flex: 1,
                  backgroundColor: '#9370DB',  // 紫色按钮
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '10px 24px',
                  fontSize: '11pt',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                继续监控
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
