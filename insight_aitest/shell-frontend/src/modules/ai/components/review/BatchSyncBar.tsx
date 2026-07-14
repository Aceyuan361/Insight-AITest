import { useState } from 'react';
import { useTranslation, Trans } from 'react-i18next';
import { Check } from 'lucide-react';
import { Modal } from '../../../../components/ui/modal';
import { primaryButton, ghostButton, text } from '../agentStyles';

/** 用例审阅底部同步栏：选中计数 + 目标版本 + 同步按钮（带确认弹窗）。
 *
 *  版本数据来源：当前用一个数字输入接收 version_id。
 *  TODO: 从 /api/modules/<project>/versions 加载真实版本列表填充下拉框（单独集成项）。
 */
export function BatchSyncBar({
  selectedCount,
  totalCount,
  syncStatus,
  onSync,
}: {
  selectedCount: number;
  totalCount: number;
  syncStatus: 'idle' | 'confirming' | 'syncing' | 'done';
  onSync: (versionId: number, deleteUnselected: boolean) => void;
}) {
  const [versionId, setVersionId] = useState<string>('');
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleteUnselected, setDeleteUnselected] = useState(false);
  const { t } = useTranslation();

  const syncing = syncStatus === 'syncing';
  const deleteCount = Math.max(0, totalCount - selectedCount);
  const validVersion = versionId.trim() !== '' && !Number.isNaN(Number(versionId));

  const startSync = () => {
    if (!validVersion || syncing) return;
    setConfirmOpen(true);
  };

  const confirmSync = () => {
    setConfirmOpen(false);
    onSync(parseInt(versionId, 10), deleteUnselected);  // 确保传整数，防止 1.1 引发 422
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        flexWrap: 'wrap',
        padding: '10px 12px',
        borderTop: '1px solid var(--border)',
        background: 'var(--bg-card)',
        borderRadius: '0 0 12px 12px',
      }}
    >
      <span style={{ fontSize: 12, color: text.secondary }}>
        <Trans
          t={t}
          i18nKey="ai.selectedCountLabel"
          components={{ b: <b style={{ color: text.primary }} /> }}
          values={{ selected: selectedCount, total: totalCount }}
        />
      </span>

      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <label style={{ fontSize: 12, color: text.muted }}>{t('ai.targetVersion')}</label>
        {/* TODO: 替换为从 /api/modules/<project>/versions 加载的版本下拉框 */}
        <input
          type="number"
          placeholder="version_id"
          value={versionId}
          onChange={(e) => setVersionId(e.target.value)}
          style={{
            width: 110,
            background: 'var(--bg-base)',
            border: '1px solid var(--border)',
            borderRadius: 6,
            color: 'var(--text-primary)',
            padding: '4px 8px',
            fontSize: 12,
          }}
        />
      </div>

      <label
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          fontSize: 12,
          color: text.secondary,
          cursor: 'pointer',
        }}
      >
        <input
          type="checkbox"
          checked={deleteUnselected}
          onChange={(e) => setDeleteUnselected(e.target.checked)}
          style={{ accentColor: 'var(--accent)', cursor: 'pointer' }}
        />
        {t('ai.deleteUnselected')}
      </label>

      <div style={{ flex: 1 }} />

      {syncStatus === 'done' ? (
        <span style={{ fontSize: 12, color: text.success, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <Check size={14} strokeWidth={2} /> {t('ai.syncDone')}
        </span>
      ) : (
        <button
          onClick={startSync}
          disabled={!validVersion || syncing || selectedCount === 0}
          style={{
            ...primaryButton,
            opacity: !validVersion || syncing || selectedCount === 0 ? 0.4 : 1,
            padding: '6px 16px',
            fontSize: 12,
          }}
        >
          {syncing ? t('ai.syncing') : t('ai.syncToVersion')}
        </button>
      )}

      <Modal open={confirmOpen} onOpenChange={setConfirmOpen} title={t('ai.confirmSyncTitle')}>
        <div style={{ padding: '0 20px 16px' }}>
          <p style={{ margin: 0, color: text.secondary, fontSize: 13, lineHeight: 1.7 }}>
            <Trans
              t={t}
              i18nKey="ai.confirmSyncMsg"
              components={{ b: <b style={{ color: text.primary }} /> }}
              values={{ selected: selectedCount, version: versionId }}
            />
            {deleteUnselected && (
              <>
                <br />
                <Trans
                  t={t}
                  i18nKey="ai.confirmSyncDelete"
                  components={{ b: <b style={{ color: text.danger }} /> }}
                  values={{ count: deleteCount }}
                />
              </>
            )}
          </p>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, padding: '0 20px 16px' }}>
          <button onClick={() => setConfirmOpen(false)} style={{ ...ghostButton, padding: '6px 16px', fontSize: 13 }}>
            {t('common.cancel')}
          </button>
          <button
            onClick={confirmSync}
            style={{
              background: deleteUnselected ? 'var(--error)' : 'var(--accent)',
              color: deleteUnselected ? 'var(--text-primary)' : 'var(--bg-base)',
              border: 'none',
              borderRadius: 6,
              padding: '6px 16px',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            {t('ai.confirmSyncBtn')}
          </button>
        </div>
      </Modal>
    </div>
  );
}
