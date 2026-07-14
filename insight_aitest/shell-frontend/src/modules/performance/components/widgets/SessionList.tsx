/**
 * 会话列表组件 - 重构版
 * 完全复刻桌面版会话列表表格格式
 *
 * 格式: 2列表格 (时间, 会话ID)
 * 最大宽度: 300px
 * 支持多选和批量删除
 */
import { useEffect, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { api } from '@/shared/api/api';
import { useConfirmStore } from '@/shared/store/confirmStore';
import { useIsMobile } from '@/shared/hooks/useIsMobile';
import type { Session, Device } from '@/shared/types';

interface SessionListProps {
  onSelectSession?: (sessionId: number | null) => void;
  selectedSessionId?: number | null;
  platformFilter?: 'all' | 'android' | 'ios';
  searchText?: string;
}

export default function SessionList({
  onSelectSession,
  selectedSessionId,
  platformFilter = 'all',
  searchText = '',
}: SessionListProps) {
  const { t } = useTranslation();
  const { confirm } = useConfirmStore();
  const isMobile = useIsMobile();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [devices, setDevices] = useState<Record<string, Device>>({});
  const [loading, setLoading] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // 加载会话列表
  const loadSessions = async () => {
    setLoading(true);
    // 清空之前的数据，防止重复
    setSessions([]);
    setSelectedIds(new Set());

    try {
      const data = await api.getSessions(100);
      setSessions(data);

      // 性能优化：延迟加载设备信息，优先显示会话列表
      // 只在有筛选需求时才加载设备信息
      if (platformFilter !== 'all') {
        const deviceIds = [...new Set(data.map(s => s.device_id))];
        const deviceMap: Record<string, Device> = {};
        await Promise.all(
          deviceIds.map(async (deviceId) => {
            try {
              const device = await api.getDevice(deviceId);
              deviceMap[deviceId] = device;
            } catch {
              // 设备可能已断开连接，忽略错误
            }
          })
        );
        setDevices(deviceMap);
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 当平台筛选改变且需要设备信息时，加载设备数据
  useEffect(() => {
    const loadDeviceDataIfNeeded = async () => {
      if (platformFilter !== 'all' && sessions.length > 0) {
        const deviceIds = [...new Set(sessions.map(s => s.device_id))];
        const deviceMap: Record<string, Device> = {};
        await Promise.all(
          deviceIds.map(async (deviceId) => {
            try {
              const device = await api.getDevice(deviceId);
              deviceMap[deviceId] = device;
            } catch {
              // 设备可能已断开连接，忽略错误
            }
          })
        );
        setDevices(deviceMap);
      }
    };

    loadDeviceDataIfNeeded();
  }, [platformFilter, sessions]);

  // 格式化时间显示 (YYYY-MM-DD HH:mm:ss)
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).replace(/\//g, '-');
  };

  // 应用筛选
  const filteredSessions = useMemo(() => {
    return sessions.filter((session) => {
      // 平台筛选 - 优先使用 session.platform（避免查询设备）
      if (platformFilter !== 'all') {
        const sessionPlatform = session.platform?.toLowerCase();
        if (sessionPlatform && sessionPlatform !== platformFilter) {
          // 如果 session 有明确的 platform 且不匹配，直接过滤掉
          return false;
        }
        // 如果 session.platform 不存在或为空，再尝试从设备信息获取
        if (!sessionPlatform) {
          const device = devices[session.device_id];
          const devicePlatform = device?.type;
          if (!devicePlatform || devicePlatform !== platformFilter) {
            return false;
          }
        }
      }

      // 搜索筛选
      if (searchText && searchText.trim()) {
        const searchLower = searchText.toLowerCase().trim();
        const packageName = session.app_package.toLowerCase();
        const appName = (session.app_name || '').toLowerCase();
        if (!packageName.includes(searchLower) && !appName.includes(searchLower)) {
          return false;
        }
      }

      return true;
    });
  }, [sessions, devices, platformFilter, searchText]);

  // 切换选中状态
  const toggleSelectSession = (sessionId: number, e?: React.MouseEvent | React.ChangeEvent) => {
    if (e && 'stopPropagation' in e) {
      e.stopPropagation();
    }
    const newSelectedIds = new Set(selectedIds);
    if (newSelectedIds.has(sessionId)) {
      newSelectedIds.delete(sessionId);
    } else {
      newSelectedIds.add(sessionId);
    }
    setSelectedIds(newSelectedIds);
  };

  // 全选/取消全选
  const toggleSelectAll = () => {
    const isAllSelected = selectedIds.size > 0 && filteredSessions.length > 0 &&
      filteredSessions.every(session => selectedIds.has(session.id));

    if (isAllSelected) {
      // 取消全选
      setSelectedIds(new Set());
    } else {
      // 全选
      setSelectedIds(new Set(filteredSessions.map(s => s.id)));
    }
  };

  // 批量删除
  const handleBatchDelete = () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) {
      toast.warning(t('sessionList.selectSessionsFirst'));
      return;
    }

    confirm({
      title: t('dialogs.confirmDelete'),
      message: t('sessionList.confirmBatchDelete', { count: ids.length }),
      confirmText: t('dialogs.confirmDelete'),
      cancelText: t('dialogs.cancel'),
      variant: 'danger',
      onConfirm: async () => {
        try {
          const result = await api.batchDeleteSessions(ids);

          const { success, failed, failed_ids } = result;

          // 如果当前选中的会话被删除了，清空选中状态
          if (selectedSessionId && selectedIds.has(selectedSessionId)) {
            onSelectSession?.(null);
          }

          // 清空选中状态
          setSelectedIds(new Set());

          // 刷新会话列表
          await loadSessions();

          // 显示结果
          if (failed === 0) {
            toast.success(t('sessionList.deleteSuccess', { count: success }));
          } else {
            toast.warning(
              t('sessionList.deletePartialSuccess', { success, failed, ids: failed_ids.join(', ') })
            );
          }
        } catch (error) {
          console.error('Failed to batch delete sessions:', error);
          toast.error(`${t('sessionList.deleteFailed')}: ${(error as Error).message}`);
        }
      },
    });
  };

  // 选择行
  const handleRowClick = (sessionId: number) => {
    onSelectSession?.(sessionId);
  };

  // 处理全选复选框变化
  const handleSelectAllChange = () => {
    toggleSelectAll();
  };

  return (
    <div
      className="flex flex-col h-full rounded-lg overflow-hidden"
      style={{
        backgroundColor: "var(--bg-card)",
        border: '1px solid var(--bg-card)',
        maxWidth: '300px',
        overflowX: isMobile ? 'auto' : 'hidden',
      }}
    >
      {/* 表头 */}
      <div
        className="grid grid-cols-12 gap-2 px-3 py-2 border-b font-semibold text-xs"
        style={{
          backgroundColor: "var(--bg-card)",
          borderColor: "var(--bg-card)",
          color: 'var(--accent)',
          fontSize: '11px',
        }}
      >
        <div className="col-span-1 flex items-center">
          <input
            type="checkbox"
            checked={selectedIds.size === filteredSessions.length && filteredSessions.length > 0}
            onChange={handleSelectAllChange}
            className="w-3 h-3 rounded"
            style={{
              border: '1px solid var(--border-strong)',
              backgroundColor: 'var(--bg-elevated)',
              accentColor: "var(--accent)",
            }}
          />
        </div>
        <div className="col-span-1">{t('report.table.index')}</div>
        <div className="col-span-5">{t('report.table.time')}</div>
        <div className="col-span-5">{t('report.table.appName')}</div>
      </div>

      {/* 批量操作栏 */}
      {selectedIds.size > 0 && (
        <div
          className="px-3 py-2 border-b flex items-center justify-between"
          style={{ borderColor: "var(--bg-card)" }}
        >
          <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
            {t('report.selectedCount', { count: selectedIds.size })}
          </span>
          <button
            onClick={handleBatchDelete}
            className="px-2 py-1 text-xs rounded font-medium transition-colors"
            style={{
              backgroundColor: "var(--error)",
              color: "var(--text-primary)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--error)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "var(--error)";
            }}
          >
            {t('report.batchDelete')}
          </button>
        </div>
      )}

      {/* 表格内容 */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <span style={{ color: "var(--text-muted)", fontSize: '12px' }}>{t('common.loading')}</span>
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <span style={{ color: "var(--text-muted)", fontSize: '12px' }}>{t('report.noSessions')}</span>
          </div>
        ) : (
          <div>
            {filteredSessions.map((session) => {
              const isSelected = selectedSessionId === session.id;
              const isRowSelected = selectedIds.has(session.id);

              return (
                <div
                  key={session.id}
                  onClick={() => handleRowClick(session.id)}
                  className="grid grid-cols-12 gap-2 px-3 py-2 border-b cursor-pointer transition-colors"
                  style={{
                    borderColor: "var(--bg-card)",
                    backgroundColor: isSelected
                      ? "var(--accent)"
                      : isRowSelected
                      ? "var(--bg-card)"
                      : 'transparent',
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected && !isRowSelected) {
                      e.currentTarget.style.backgroundColor = "var(--bg-card)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected && !isRowSelected) {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  {/* 复选框 */}
                  <div className="col-span-1 flex items-center">
                    <input
                      type="checkbox"
                      checked={isRowSelected}
                      onChange={(e) => toggleSelectSession(session.id, e)}
                      onClick={(e) => e.stopPropagation()}
                      className="w-3 h-3 rounded"
                      style={{
                        border: '1px solid var(--border-strong)',
                        backgroundColor: 'var(--bg-elevated)',
                        accentColor: "var(--accent)",
                      }}
                    />
                  </div>

                  {/* 会话ID */}
                  <div
                    className="col-span-1 flex items-center text-xs"
                    style={{
                      color: isSelected ? "var(--bg-base)" : "var(--text-secondary)",
                      fontSize: '11px',
                    }}
                  >
                    {session.id}
                  </div>

                  {/* 时间 */}
                  <div
                    className="col-span-5 flex items-center text-xs truncate"
                    style={{
                      color: isSelected ? "var(--bg-base)" : "var(--text-primary)",
                      fontSize: '11px',
                    }}
                  >
                    {formatDate(session.start_time)}
                  </div>

                  {/* 会话ID */}
                  <div
                    className="col-span-5 flex items-center text-xs truncate"
                    style={{ fontSize: '11px' }}
                  >
                    <span
                      className="truncate"
                      style={{
                        color: isSelected ? "var(--bg-base)" : "var(--text-primary)",
                      }}
                    >
                      {session.app_name || session.app_package || 'Unknown'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
