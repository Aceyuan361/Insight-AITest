import { useState, useEffect, useRef } from 'react';
import { Download, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface DocxEditorProps {
  /** docx 原始文件 URL（GET /raw） */
  url: string;
  filename: string;
  /** 保存回调：接收导出的 docx Blob */
  onSave: (blob: Blob, filename: string) => Promise<void>;
  saving: boolean;
  readOnly?: boolean;
}

/**
 * docx 在线 WYSIWYG 编辑器（基于 SuperDoc）。
 *
 * 加载 .docx → 浏览器内可视化编辑 → 导出回 .docx Blob 上传后端。
 * SuperDoc 完全在浏览器主线程运行，无 worker/CDN 依赖。
 *
 * 注意：SuperDoc 是 AGPL-3.0 许可证（开源/自托管场景免费）。
 */
export function DocxEditor({ url, filename, onSave, saving, readOnly = false }: DocxEditorProps) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [superDocInstance, setSuperDocInstance] = useState<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<any>(null);

  useEffect(() => {
    let destroyed = false;
    setLoading(true);
    setError(null);

    // 动态导入 SuperDoc 核心包（懒加载，避免撑大首屏）
    import('superdoc').then(({ SuperDoc }) => {
      if (destroyed || !containerRef.current) return;
      // 引入样式
      import('superdoc/style.css').catch(() => {});

      // 从 URL 加载 docx → File
      fetch(url)
        .then((r) => r.arrayBuffer())
        .then((buf) => {
          if (destroyed) return;
          const file = new File([buf], filename, {
            type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          });
          const sd = new SuperDoc({
            selector: containerRef.current!,
            document: file,
            documentMode: readOnly ? 'viewing' : 'editing',
            role: readOnly ? 'viewer' : 'editor',
            onReady: () => {
              if (!destroyed) {
                setSuperDocInstance(sd);
                setLoading(false);
              }
            },
          });
          instanceRef.current = sd;
        })
        .catch((e) => {
          if (!destroyed) {
            setError(e.message || t('kb.docxLoadFailed'));
            setLoading(false);
          }
        });
    }).catch((e) => {
      if (!destroyed) {
        setError(t('kb.superDocLoadFailed', { message: e.message || String(e) }));
        setLoading(false);
      }
    });

    return () => {
      destroyed = true;
      // 清理 SuperDoc 实例，避免泄漏
      if (instanceRef.current?.destroy) {
        try { instanceRef.current.destroy(); } catch { /* 静默 */ }
      }
      instanceRef.current = null;
    };
  }, [url, filename, readOnly]);

  const handleExport = async () => {
    if (!superDocInstance) return;
    try {
      // triggerDownload:false 返回 Blob，不弹下载框
      const blob = await superDocInstance.export({ triggerDownload: false });
      await onSave(blob as Blob, filename);
    } catch (e: any) {
      setError(t('kb.exportFailed', { message: e.message || String(e) }));
    }
  };

  const handleDownload = async () => {
    if (!superDocInstance) return;
    try {
      await superDocInstance.export({ triggerDownload: true });
    } catch (e: any) {
      setError(t('kb.downloadFailed', { message: e.message || String(e) }));
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
        <Loader2 size={16} className="animate-spin" /> {t('kb.loadDocxEditor')}
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24, textAlign: 'center', color: 'var(--error)', fontSize: 13 }}>
        {error}
        <br />
        <a href={url} download style={{ color: 'var(--accent)', fontSize: 12, marginTop: 8, display: 'inline-block' }}>
          {t('kb.downloadOriginalLocal')}
        </a>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '6px 12px', borderBottom: '1px solid var(--bg-card)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          {readOnly ? t('kb.docxReadOnlyHint') : t('kb.docxEditHint')}
        </span>
        <div style={{ display: 'flex', gap: 6 }}>
          {!readOnly && (
            <button
              onClick={handleExport}
              disabled={saving}
              style={btnStyle(saving)}
            >
              {saving ? t('kb.saving') : t('kb.save')}
            </button>
          )}
          <a href={url} download onClick={(e) => { e.preventDefault(); handleDownload(); }} style={{ ...btnStyle(false), textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <Download size={13} /> {t('kb.download')}
          </a>
        </div>
      </div>
      {/* SuperDoc 挂载容器 */}
      <div ref={containerRef} style={{ flex: 1, overflow: 'auto' }} />
    </div>
  );
}

function btnStyle(disabled: boolean): React.CSSProperties {
  return {
    background: disabled ? 'var(--bg-elevated)' : 'var(--accent)',
    color: disabled ? 'var(--text-muted)' : '#fff',
    border: 'none',
    padding: '4px 12px',
    borderRadius: 4,
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontSize: 12,
  };
}
