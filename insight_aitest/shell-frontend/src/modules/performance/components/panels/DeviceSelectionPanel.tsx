import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Bot, Apple, Smartphone, Circle } from 'lucide-react';
import { useMonitoringStore } from '@/modules/performance/store/monitoringStore';
import { useProjectStore } from '@/shared/store/projectStore';
import { deviceApi } from '@/shared/api/api';
import type { AppInfo } from '@/shared/types';

// 从应用列表中获取应用友好名称的辅助函数
function getAppNameFromList(apps: AppInfo[], packageName: string): string {
  if (!packageName) return '';
  const app = apps.find(a => a.package_name === packageName);
  return app?.name || packageName;
}

export default function DeviceSelectionPanel() {
  const { t } = useTranslation();
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
  const [appSearchQuery, setAppSearchQuery] = useState<string>('');

  // 初始加载设备列表
  useEffect(() => {
    const loadDevices = async () => {
      setLoading(true);
      setError(null);
      try {
        const deviceList = await deviceApi.getDevices();
        // 按 device_id 去重，保留第一次出现的设备
        const uniqueDevices = deviceList.filter((device, index, self) =>
          index === self.findIndex((d) => d.device_id === device.device_id)
        );
        setDevices(uniqueDevices);
      } catch (err) {
        console.error('Failed to load devices:', err);
        setError(t('device.selectDeviceFirst'));
      } finally {
        setLoading(false);
      }
    };

    loadDevices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  // 从会话中获取应用名称（优先使用应用列表中的友好名称）
  const currentAppName = currentSession?.app_name ||
    (selectedAppPackage ? getAppNameFromList(apps, selectedAppPackage) : '');
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
      setError(t('device.refreshDevices'));
    } finally {
      setLoading(false);
    }
  };

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
          const appName = getAppNameFromList(latestApps, selectedAppPackage);
          await useMonitoringStore.getState().startMonitoring(
            selectedDevice,
            selectedAppPackage,
            platform,
            undefined,
            useProjectStore.getState().currentProjectId
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
          const appName = getAppNameFromList(apps, selectedAppPackage);
          await useMonitoringStore.getState().startMonitoring(
            selectedDevice,
            selectedAppPackage,
            platform,
            undefined,
            useProjectStore.getState().currentProjectId
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
          platform,
          undefined,
          useProjectStore.getState().currentProjectId
        );
        if (useMonitoringStore.getState().currentSession) {
          useMonitoringStore.getState().currentSession!.app_name = pendingAppName;
        }
      } catch (error) {
        console.error(t('dialogs.operationFailed'), error);
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
    const Icon = type === 'android' ? Bot : type === 'ios' ? Apple : Smartphone;
    return <Icon size={13} strokeWidth={1.5} />;
  };

  const getStatusText = (status: string) => {
    const statusMap: Record<string, string> = {
      'online': t('device.deviceOnline'),
      'offline': t('device.deviceOffline'),
      'unauthorized': t('device.deviceUnauthorized'),
    };
    return statusMap[status] || status;
  };

  const canStart = selectedDevice && selectedAppPackage && !isMonitoring;

  // 过滤应用列表（模糊搜索）
  const filteredApps = apps.filter(app => {
    if (!appSearchQuery) return true;
    const query = appSearchQuery.toLowerCase();
    return (
      app.name.toLowerCase().includes(query) ||
      app.package_name.toLowerCase().includes(query)
    );
  });

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
        color: "var(--accent)",
        padding: '4px 0px',
      }}>
        {t('device.currentTarget')}
      </div>

      {/* 错误提示 */}
      {error && (
        <div style={{
          padding: '8px 12px',
          backgroundColor: 'rgba(127, 29, 29, 0.3)',
          border: '1px solid var(--error)',
          borderRadius: '6px',
          color: 'var(--error)',
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
          color: "var(--text-secondary)",
          display: 'block',
          marginBottom: '8px',
        }}>
          {t('device.title')}
        </label>
        {isMonitoring && currentDevice ? (
          // 监控中显示设备信息
          <div style={{
            width: '100%',
            backgroundColor: "var(--bg-card)",
            color: "var(--text-primary)",
            border: '1px solid var(--bg-card)',
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
              backgroundColor: "var(--bg-card)",
              color: "var(--text-primary)",
              border: '1px solid var(--bg-card)',
              borderRadius: '6px',
              padding: '10px 12px',
              fontSize: '10pt',
            }}
          >
            <option value="">{t('device.selectDeviceFirst')}</option>
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
          color: "var(--text-secondary)",
          display: 'block',
          marginBottom: '8px',
        }}>
          {t('device.app')}
        </label>
        {isMonitoring && currentAppName ? (
          // 监控中显示应用名称
          <div style={{
            width: '100%',
            backgroundColor: "var(--bg-card)",
            color: "var(--text-primary)",
            border: '1px solid var(--bg-card)',
            borderRadius: '6px',
            padding: '10px 12px',
            fontSize: '10pt',
          }}>
            {currentAppName}
          </div>
        ) : (
          // 未监控显示搜索框和下拉框
          <>
            {/* 应用搜索框 */}
            <input
              type="text"
              placeholder={t('report.searchPlaceholder')}
              value={appSearchQuery}
              onChange={(e) => setAppSearchQuery(e.target.value)}
              disabled={!selectedDevice}
              style={{
                width: '100%',
                backgroundColor: !selectedDevice ? "var(--bg-card)" : "var(--bg-card)",
                color: "var(--text-primary)",
                border: '1px solid var(--bg-card)',
                borderRadius: '6px',
                padding: '8px 12px',
                fontSize: '10pt',
                marginBottom: '8px',
                opacity: !selectedDevice ? 0.6 : 1,
              }}
            />
            {/* 应用下拉框 */}
            <select
              value={selectedAppPackage}
              onChange={(e) => handleAppChange(e.target.value)}
              disabled={!selectedDevice}
              style={{
                width: '100%',
                backgroundColor: !selectedDevice ? "var(--bg-card)" : "var(--bg-card)",
                color: "var(--text-primary)",
                border: '1px solid var(--bg-card)',
                borderRadius: '6px',
                padding: '10px 12px',
                fontSize: '10pt',
                opacity: !selectedDevice ? 0.6 : 1,
              }}
            >
              <option value="">{t('device.selectAppFirst')}</option>
              {filteredApps.map((app) => (
                <option key={app.package_name} value={app.package_name}>
                  {app.name}
                </option>
              ))}
            </select>
            {/* 显示搜索结果数量 */}
            {appSearchQuery && (
              <div style={{
                fontSize: '9pt',
                color: "var(--text-muted)",
                marginTop: '4px',
                textAlign: 'right',
              }}>
                {t('stats.total')} {filteredApps.length} {t('stats.items')}
              </div>
            )}
          </>
        )}
      </div>

      {/* === 当前目标显示 === */}
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
          {t('device.currentTarget')}
        </div>
        <div style={{
          fontSize: '10pt',
          color: currentDeviceName ? "var(--text-primary)" : "var(--text-secondary)",
          padding: '4px 8px',
        }}>
          {t('device.title')}: {currentDeviceName || t('device.selectDeviceFirst')}
        </div>
        <div style={{
          fontSize: '10pt',
          color: currentAppName ? "var(--text-primary)" : "var(--text-secondary)",
          padding: '4px 8px',
        }}>
          {t('device.app')}: {currentAppName || t('device.selectAppFirst')}
        </div>
      </div>

      {/* === 控制按钮 === */}
      <div style={{ display: 'flex', gap: '12px' }}>
        <button
          onClick={handleStartStopMonitoring}
          disabled={!canStart && !isMonitoring}
          style={{
            flex: 1,
            backgroundColor: isMonitoring ? 'var(--chart-5)' : canStart ? "var(--accent)" : "var(--bg-card)",
            color: isMonitoring ? "var(--bg-base)" : canStart ? "var(--bg-base)" : "var(--text-muted)",
            border: 'none',
            borderRadius: '6px',
            padding: '12px 24px',
            fontSize: '11pt',
            fontWeight: '600',
            cursor: canStart || isMonitoring ? 'pointer' : 'not-allowed',
          }}
        >
          {isMonitoring ? t('device.stopMonitor') : t('device.startMonitor')}
        </button>
        <button
          onClick={handleRefresh}
          disabled={loading}
          style={{
            flex: 1,
            backgroundColor: "var(--bg-card)",
            color: "var(--text-primary)",
            border: '1px solid var(--border-strong)',
            borderRadius: '6px',
            padding: '12px 24px',
            fontSize: '11pt',
            fontWeight: '600',
            opacity: loading ? 0.5 : 1,
          }}
        >
          {loading ? t('common.loading') : t('device.refreshDevices')}
        </button>
      </div>

      {/* === 状态显示 === */}
      <div style={{
        fontSize: '10pt',
        color: isMonitoring ? "var(--success)" : "var(--text-muted)",
        padding: '8px',
        backgroundColor: "var(--bg-base)",
        borderRadius: '6px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 4,
      }}>
        <Circle size={12} strokeWidth={1.5} fill={isMonitoring ? 'var(--success)' : 'var(--text-muted)'} style={{ flexShrink: 0 }} />
        {isMonitoring ? t('menu.monitoring') : t('menu.notMonitoring')}
      </div>

      {/* === 电池信息 === */}
      <div style={{
        backgroundColor: "var(--bg-base)",
        border: '1px solid var(--bg-card)',
        borderRadius: '8px',
        padding: '12px',
      }}>
        <div style={{
          fontSize: '11pt',
          fontWeight: '600',
          color: "var(--chart-4)",
          marginBottom: '8px',
        }}>
          {t('device.battery')}
        </div>
        <div style={{
          fontSize: '10pt',
          color: "var(--text-secondary)",
          padding: '4px 8px',
        }}>
          {t('device.batteryLevel')}: {batteryInfo.level}%
        </div>
        <div style={{
          fontSize: '10pt',
          color: "var(--text-secondary)",
          padding: '4px 8px',
        }}>
          {t('device.temperature')}: {batteryInfo.temperature}°C
        </div>
        <div style={{
          fontSize: '10pt',
          color: "var(--text-secondary)",
          padding: '4px 8px',
        }}>
          {t('device.capacity')}: {batteryInfo.capacity}
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
            backgroundColor: "var(--bg-card)",
            border: '2px solid var(--chart-3)',
            borderRadius: '12px',
            padding: '24px',
            maxWidth: '500px',
            boxShadow: '0 8px 32px rgba(255, 180, 0, 0.3)',
          }}>
            <h3 style={{
              color: "var(--chart-3)",
              fontSize: '16pt',
              fontWeight: '700',
              marginBottom: '16px',
              marginTop: 0,
            }}>
              {t('device.appNotRunning')}
            </h3>
            <p style={{
              color: "var(--text-primary)",
              fontSize: '11pt',
              lineHeight: '1.6',
              marginBottom: '16px',
            }}>
              {t('device.appNotRunningMessage')}
            </p>
            <div style={{
              backgroundColor: "var(--bg-base)",
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '16px',
            }}>
              <div style={{ color: "var(--text-secondary)", fontSize: '10pt', marginBottom: '4px' }}>
                {t('dialogs.confirmDelete')}:
              </div>
              <div style={{ color: "var(--text-primary)", fontSize: '10pt', fontWeight: '500', wordBreak: 'break-all' }}>
                {pendingAppPackage}
              </div>
            </div>
            <div style={{
              color: "var(--chart-3)",
              fontSize: '10pt',
              marginBottom: '16px',
              padding: '12px',
              backgroundColor: 'rgba(255, 180, 0, 0.1)',
              borderRadius: '6px',
            }}>
              <strong>{t('dialogs.confirmDelete')}：</strong>{t('device.appNotRunningMessage')}
            </div>
            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <button
                onClick={handleCancelStartNotRunning}
                style={{
                  backgroundColor: 'var(--info)',
                  color: "var(--text-primary)",
                  border: 'none',
                  borderRadius: '6px',
                  padding: '10px 32px',
                  fontSize: '11pt',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                {t('common.ok')}
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
            backgroundColor: "var(--bg-card)",
            border: '2px solid var(--chart-2)',
            borderRadius: '12px',
            padding: '24px',
            maxWidth: '500px',
            boxShadow: '0 8px 32px rgba(147, 112, 219, 0.3)',
          }}>
            <h3 style={{
              color: 'var(--chart-2)',
              fontSize: '16pt',
              fontWeight: '700',
              marginBottom: '16px',
              marginTop: 0,
            }}>
              {t('device.appInBackground')}
            </h3>
            <p style={{
              color: "var(--text-primary)",
              fontSize: '11pt',
              lineHeight: '1.6',
              marginBottom: '16px',
            }}>
              {t('device.appInBackgroundMessage')}
            </p>
            <div style={{
              backgroundColor: "var(--bg-base)",
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '16px',
            }}>
              <div style={{ color: "var(--text-secondary)", fontSize: '10pt', marginBottom: '4px' }}>
                {t('device.app')}:
              </div>
              <div style={{ color: "var(--text-primary)", fontSize: '10pt', fontWeight: '500' }}>
                {pendingAppName}
              </div>
              <div style={{ color: "var(--text-secondary)", fontSize: '10pt', marginBottom: '4px', marginTop: '8px' }}>
                PID:
              </div>
              <div style={{ color: "var(--text-primary)", fontSize: '10pt', fontWeight: '500' }}>
                {pendingAppPid}
              </div>
            </div>
            <div style={{
              color: 'var(--chart-2)',
              fontSize: '10pt',
              marginBottom: '16px',
              padding: '12px',
              backgroundColor: 'rgba(147, 112, 219, 0.1)',
              borderRadius: '6px',
            }}>
              <strong>{t('dialogs.confirmDelete')}：</strong>{t('device.appInBackgroundMessage')}
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={handleCancelStartBackground}
                style={{
                  flex: 1,
                  backgroundColor: 'var(--bg-elevated)',
                  color: "var(--text-primary)",
                  border: 'none',
                  borderRadius: '6px',
                  padding: '10px 24px',
                  fontSize: '11pt',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleConfirmStartBackground}
                style={{
                  flex: 1,
                  backgroundColor: 'var(--chart-2)',
                  color: "var(--text-primary)",
                  border: 'none',
                  borderRadius: '6px',
                  padding: '10px 24px',
                  fontSize: '11pt',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                {t('dialogs.confirm')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
