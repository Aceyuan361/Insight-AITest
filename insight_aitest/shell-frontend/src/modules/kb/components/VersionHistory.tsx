import { useState, useEffect } from 'react';
import { RotateCcw, GitCompare } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useKnowledgeStore, type Document, type DocVersion } from '../store/knowledgeStore';
import { useConfirmStore } from '../../../shared/store/confirmStore';

interface VersionHistoryProps {
  doc: Document;
  onClose: () => void;
}

/** 版本历史面板：列出版本、对比当前、回滚。 */
export function VersionHistory({ doc }: VersionHistoryProps) {
  const { t } = useTranslation();
  const { listVersions, getVersionContent, rollbackVersion, fetchContent } = useKnowledgeStore();
  const { confirm } = useConfirmStore();
  const [versions, setVersions] = useState<DocVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState<{ current: string; version: string; versionNo: number } | null>(null);

  const reload = () => {
    setLoading(true);
    listVersions(doc.id)
      .then(setVersions)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    reload();
  }, [doc.id]);

  const handleCompare = async (v: DocVersion) => {
    try {
      const [versionText, currentData] = await Promise.all([
        getVersionContent(doc.id, v.version_no),
        fetchContent(doc.id),
      ]);
      setComparing({ current: currentData.text, version: versionText, versionNo: v.version_no });
    } catch {
      /* 静默 */
    }
  };

  const handleRollback = (v: DocVersion) => {
    confirm({
      title: t('kb.confirmRollback'),
      message: t('kb.confirmRollbackMessage', { version: v.version_no }),
      variant: 'danger',
      onConfirm: async () => {
        await rollbackVersion(doc.id, v.version_no);
        reload();
      },
    });
  };

  return (
    <div style={{ width: 280, borderRight: '1px solid var(--bg-card)', display: 'flex', flexDirection: 'column', overflow: 'hidden', flexShrink: 0 }}>
      <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--bg-card)', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>
        {t('kb.versionHistory')}
      </div>

      {/* 对比视图 */}
      {comparing && (
        <div style={{ position: 'fixed', inset: '8vh 8vw', background: 'var(--bg-base)', border: '1px solid var(--bg-elevated)', borderRadius: 8, zIndex: 3000, display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--bg-card)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>{t('kb.versionCompareTitle', { version: comparing.versionNo })}</span>
            <button onClick={() => setComparing(null)} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 18 }}>×</button>
          </div>
          <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
            <div style={{ flex: 1, borderRight: '1px solid var(--bg-card)' }}>
              <div style={{ padding: '6px 12px', fontSize: 11, color: 'var(--text-muted)', background: 'var(--bg-card)' }}>{t('kb.currentVersion')}</div>
              <pre style={{ margin: 0, padding: 12, fontSize: 12, lineHeight: 1.5, overflow: 'auto', height: 'calc(100% - 32px)', whiteSpace: 'pre-wrap', color: 'var(--text-primary)' }}>{comparing.current}</pre>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ padding: '6px 12px', fontSize: 11, color: 'var(--text-muted)', background: 'var(--bg-card)' }}>v{comparing.versionNo}</div>
              <pre style={{ margin: 0, padding: 12, fontSize: 12, lineHeight: 1.5, overflow: 'auto', height: 'calc(100% - 32px)', whiteSpace: 'pre-wrap', color: 'var(--text-primary)' }}>{comparing.version}</pre>
            </div>
          </div>
        </div>
      )}

      <div style={{ flex: 1, overflow: 'auto' }}>
        {loading ? (
          <div style={{ padding: 16, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>{t('kb.loading')}</div>
        ) : versions.length === 0 ? (
          <div style={{ padding: 16, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>{t('kb.noHistoryVersions')}</div>
        ) : (
          versions.map((v) => (
            <div key={v.id} style={{ padding: '10px 12px', borderBottom: '1px solid var(--bg-card)', display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>v{v.version_no}</span>
                <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{new Date(v.created_at).toLocaleString()}</span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('kb.versionNote', { chars: v.char_count, note: v.note || t('kb.noNote') })}</div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button onClick={() => handleCompare(v)} title={t('kb.compareCurrent')} style={{ background: 'none', border: '1px solid var(--border-strong)', color: 'var(--text-secondary)', borderRadius: 4, padding: '2px 6px', cursor: 'pointer', fontSize: 11, display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                  <GitCompare size={12} /> {t('kb.compare')}
                </button>
                <button onClick={() => handleRollback(v)} title={t('kb.rollbackToVersion')} style={{ background: 'none', border: '1px solid var(--border-strong)', color: 'var(--text-secondary)', borderRadius: 4, padding: '2px 6px', cursor: 'pointer', fontSize: 11, display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                  <RotateCcw size={12} /> {t('kb.rollback')}
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
