/**
 * 紧凑会话信息栏组件
 * 单行显示: 设备 | 应用 | 时间 | 时长
 * 完全复刻桌面版样式
 */
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '@/shared/api/api';
import type { Session, Device } from '@/shared/types';

interface SessionInfoBarProps {
  sessionId: number | null;
}

export default function SessionInfoBar({ sessionId }: SessionInfoBarProps) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language === 'zh-CN' ? 'zh-CN' : 'en-US';
  const [session, setSession] = useState<Session | null>(null);
  const [device, setDevice] = useState<Device | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!sessionId) {
      setSession(null);
      setDevice(null);
      return;
    }

    const loadSessionInfo = async () => {
      setLoading(true);
      try {
        const [sessionData] = await Promise.all([
          api.getSession(sessionId),
        ]);

        setSession(sessionData);

        // 获取设备信息
        try {
          const deviceData = await api.getDevice(sessionData.device_id);
          setDevice(deviceData);
        } catch {
          setDevice(null);
        }
      } catch (error) {
        console.error('Failed to load session info:', error);
      } finally {
        setLoading(false);
      }
    };

    loadSessionInfo();
  }, [sessionId]);

  // 计算时长
  const calculateDuration = (): string => {
    if (!session) return '';

    const start = new Date(session.start_time);
    const end = session.end_time ? new Date(session.end_time) : new Date();
    const diff = end.getTime() - start.getTime();

    if (diff < 0) return '';

    const totalSeconds = Math.floor(diff / 1000);

    if (totalSeconds < 60) {
      return t('sessionList.durationSeconds', { count: totalSeconds });
    }

    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;

    if (minutes < 60) {
      return t('sessionList.durationMinutesSeconds', { minutes, seconds });
    }

    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return t('sessionList.durationHoursMinutes', { hours, minutes: mins });
  };

  // 格式化时间显示
  const formatTimeDisplay = (): string => {
    if (!session) return '';

    const start = new Date(session.start_time);
    const startTimeStr = start.toLocaleString(locale, {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).replace(/\//g, '-');

    if (session.end_time) {
      const end = new Date(session.end_time);
      const endTimeStr = end.toLocaleTimeString(locale, {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      });
      return `${startTimeStr}-${endTimeStr}`;
    }

    return startTimeStr;
  };

  if (!sessionId || loading || !session) {
    return (
      <div
        className="px-4 py-3 text-sm"
        style={{
          backgroundColor: "var(--bg-base)",
          borderBottom: '1px solid var(--bg-card)',
          color: "var(--text-secondary)",
        }}
      >
        {t('common.loading')}
      </div>
    );
  }

  const deviceName = device?.name || t('sessionList.deviceId', { id: session.device_id.slice(0, 8) });
  const appName = session.app_name || session.app_package;
  const timeDisplay = formatTimeDisplay();
  const duration = calculateDuration();

  return (
    <div
      className="px-4 py-3 text-sm"
      style={{
        backgroundColor: "var(--bg-base)",
        borderBottom: '1px solid var(--bg-card)',
        color: "var(--text-secondary)",
        fontSize: '10pt',
      }}
    >
      {t('sessionList.device')}: {deviceName} | {t('sessionList.app')}: {appName} | {t('sessionList.time')}: {timeDisplay} | {t('sessionList.duration')}: {duration}
    </div>
  );
}
