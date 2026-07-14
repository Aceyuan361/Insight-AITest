import { useState, useEffect, lazy, Suspense } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X, Eye, Pencil, History, Download, AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useKnowledgeStore, type Document } from '../store/knowledgeStore';
import { TextEditor } from './editors/TextEditor';
import { VersionHistory } from './VersionHistory';

// 重型编辑器懒加载（避免撑大首屏 bundle）
const PdfViewer = lazy(() => import('./editors/PdfViewer').then((m) => ({ default: m.PdfViewer })));
const DocxEditor = lazy(() => import('./editors/DocxEditor').then((m) => ({ default: m.DocxEditor })));
const XlsxEditor = lazy(() => import('./editors/XlsxEditor').then((m) => ({ default: m.XlsxEditor })));
// 兼容旧只读查看器（docx mammoth 预览降级）
const DocxViewer = lazy(() => import('./editors/DocxViewer').then((m) => ({ default: m.DocxViewer })));

type Mode = 'view' | 'edit';

/** 判断文件格式类别 */
function fileKind(filename: string): 'text' | 'markdown' | 'pdf' | 'docx' | 'xlsx' | 'image' | 'unknown' {
  const f = filename.toLowerCase();
  if (/\.(md|markdown)$/.test(f)) return 'markdown';
  if (/\.(txt|log|csv|json|yaml|yml|xml|conf|ini|sh|bat|py|js|ts|sql)$/.test(f)) return 'text';
  if (/\.html?$/.test(f)) return 'text';
  if (/\.pdf$/.test(f)) return 'pdf';
  if (/\.docx$/.test(f)) return 'docx';
  if (/\.(xlsx|xls)$/.test(f)) return 'xlsx';
  if (/\.(png|jpg|jpeg|gif|webp|svg)$/.test(f)) return 'image';
  return 'unknown';
}

const TEXT_KINDS = new Set(['text', 'markdown']);

interface DocumentViewerProps {
  doc: Document | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** 文档预览/编辑全屏弹窗。
 * 按 MIME 类型分发到对应编辑器/查看器；纯文本可编辑，二进制只读预览。
 * 含版本历史面板。
 */
export function DocumentViewer({ doc, open, onOpenChange }: DocumentViewerProps) {
  const { t } = useTranslation();
  const { fetchContent, saving, rawUrl } = useKnowledgeStore();
  const [mode, setMode] = useState<Mode>('view');
  const [content, setContent] = useState('');
  const [loadingContent, setLoadingContent] = useState(false);
  const [showVersions, setShowVersions] = useState(false);

  const kind = doc ? fileKind(doc.filename) : 'unknown';
  const canEdit = TEXT_KINDS.has(kind) || kind === 'docx' || kind === 'xlsx';

  useEffect(() => {
    if (open && doc && TEXT_KINDS.has(kind)) {
      setLoadingContent(true);
      fetchContent(doc.id)
        .then((data) => setContent(data.text))
        .catch(() => setContent(''))
        .finally(() => setLoadingContent(false));
    } else {
      setContent('');
    }
    setMode('view');
    setShowVersions(false);
  }, [open, doc?.id]);

  if (!doc) return null;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 2000 }} />
        <Dialog.Content
          style={{
            position: 'fixed', inset: '3vh 3vw', background: 'var(--bg-base)',
            border: '1px solid var(--bg-elevated)', borderRadius: 10,
            boxShadow: '0 8px 32px rgba(0,0,0,0.5)', zIndex: 2001,
            display: 'flex', flexDirection: 'column', overflow: 'hidden', outline: 'none',
          }}
        >
          {/* 标题栏 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px', borderBottom: '1px solid var(--bg-card)' }}>
            <Dialog.Title style={{ flex: 1, fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {doc.filename}
            </Dialog.Title>

            {/* 工具按钮 */}
            <button
              onClick={() => setMode('view')}
              disabled={mode === 'view'}
              title={t('kb.preview')}
              style={toolBtnStyle(mode === 'view')}
            >
              <Eye size={16} />
            </button>
            {canEdit && (
              <button
                onClick={() => setMode('edit')}
                disabled={mode === 'edit'}
                title={t('kb.edit')}
                style={toolBtnStyle(mode === 'edit')}
              >
                <Pencil size={16} />
              </button>
            )}
            <button onClick={() => setShowVersions(!showVersions)} title={t('kb.versionHistory')} style={toolBtnStyle(showVersions)}>
              <History size={16} />
            </button>
            <a href={rawUrl(doc.id)} download title={t('kb.download')} style={{ ...toolBtnStyle(false), textDecoration: 'none', display: 'inline-flex' }}>
              <Download size={16} />
            </a>
            <Dialog.Close asChild>
              <button title={t('kb.close')} style={toolBtnStyle(false)}>
                <X size={16} />
              </button>
            </Dialog.Close>
          </div>

          {/* 主体：版本面板 + 内容区 */}
          <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
            {showVersions && (
              <VersionHistory doc={doc} onClose={() => setShowVersions(false)} />
            )}
            <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              {mode === 'edit' && canEdit ? (
                <EditMode kind={kind} doc={doc} content={content} loadingContent={loadingContent} saving={saving} />
              ) : (
                <Viewer kind={kind} doc={doc} content={content} loadingContent={loadingContent} />
              )}
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function toolBtnStyle(active: boolean): React.CSSProperties {
  return {
    background: active ? 'var(--accent)' : 'none',
    color: active ? '#fff' : 'var(--text-secondary)',
    border: '1px solid var(--border-strong)',
    borderRadius: 4,
    padding: 4,
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  };
}

function LoadingText() {
  const { t } = useTranslation();
  return <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>{t('kb.loadingContent')}</div>;
}

/** 编辑模式分发：纯文本用 TextEditor，二进制用 SuperDoc/Univer 在线编辑器 */
function EditMode({ kind, doc, content, loadingContent, saving }: {
  kind: string;
  doc: Document;
  content: string;
  loadingContent: boolean;
  saving: boolean;
}) {
  const { rawUrl, saveContent, saveBinaryFile } = useKnowledgeStore();
  const url = rawUrl(doc.id);

  if (kind === 'docx') {
    return (
      <Suspense fallback={<LoadingText />}>
        <DocxEditor
          url={url}
          filename={doc.filename}
          onSave={(blob, filename) => saveBinaryFile(doc.id, blob, filename)}
          saving={saving}
        />
      </Suspense>
    );
  }
  if (kind === 'xlsx') {
    return (
      <Suspense fallback={<LoadingText />}>
        <XlsxEditor
          url={url}
          filename={doc.filename}
          onSave={(blob, filename) => saveBinaryFile(doc.id, blob, filename)}
          saving={saving}
        />
      </Suspense>
    );
  }
  // 纯文本
  if (loadingContent) return <LoadingText />;
  return (
    <TextEditor
      initialText={content}
      filename={doc.filename}
      onSave={(text) => saveContent(doc.id, text)}
      saving={saving}
    />
  );
}

/** 只读查看器分发 */
function Viewer({ kind, doc, content, loadingContent }: {
  kind: string;
  doc: Document;
  content: string;
  loadingContent: boolean;
}) {
  const { t } = useTranslation();
  const { rawUrl } = useKnowledgeStore();
  const url = rawUrl(doc.id);

  if (kind === 'pdf') {
    return (
      <Suspense fallback={<LoadingText />}>
        <PdfViewer url={url} />
      </Suspense>
    );
  }
  if (kind === 'docx') {
    return (
      <Suspense fallback={<LoadingText />}>
        <DocxViewer url={url} />
      </Suspense>
    );
  }
  if (kind === 'xlsx') {
    return (
      <Suspense fallback={<LoadingText />}>
        <XlsxEditorLazyReadOnly url={url} filename={doc.filename} />
      </Suspense>
    );
  }
  if (kind === 'image') {
    return (
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', justifyContent: 'center', alignItems: 'center', padding: 16, background: 'var(--bg-base)' }}>
        <img src={url} alt={doc.filename} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', borderRadius: 4 }} />
      </div>
    );
  }
  if (TEXT_KINDS.has(kind)) {
    if (loadingContent) return <LoadingText />;
    return (
      <TextEditor initialText={content} filename={doc.filename} onSave={async () => {}} saving={false} readOnly />
    );
  }
  // 未知格式
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: 12, color: 'var(--text-muted)', fontSize: 13 }}>
      <AlertCircle size={32} strokeWidth={1.5} />
      <span>{t('kb.unsupportedFormatHint')}</span>
      <a href={url} download style={{ color: 'var(--accent)', fontSize: 12 }}>{t('kb.downloadOriginal')}</a>
    </div>
  );
}

/** 只读模式的 XlsxEditor 包装（View 模式下复用 Univer 渲染） */
function XlsxEditorLazyReadOnly({ url, filename }: { url: string; filename: string }) {
  return (
    <XlsxEditor url={url} filename={filename} onSave={async () => {}} saving={false} readOnly />
  );
}
