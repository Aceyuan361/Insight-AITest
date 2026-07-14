import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, Upload } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useKnowledgeStore, type Document } from '../store/knowledgeStore';
import { useProjectStore } from '../../../shared/store/projectStore';
import { DocumentRow } from './DocumentRow';
import { DocumentViewer } from './DocumentViewer';
import { DocumentMetaEditor } from './DocumentMetaEditor';
import { TagFilter } from './TagFilter';
import { EmptyState } from '../../../shared/components/EmptyState';

export function KnowledgeBase() {
  const { t } = useTranslation();
  const {
    documents, uploading, loadDocuments, uploadDocument, deleteDocument, stopPolling, exportZipUrl,
  } = useKnowledgeStore();
  const { currentProjectId } = useProjectStore();
  const inputRef = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState('');
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set());
  const [selectedType, setSelectedType] = useState('');
  const [previewDoc, setPreviewDoc] = useState<Document | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [metaDoc, setMetaDoc] = useState<Document | null>(null);
  const [metaOpen, setMetaOpen] = useState(false);

  useEffect(() => {
    loadDocuments();
    return () => stopPolling();
  }, [currentProjectId]); // 项目切换时重新加载

  const onPick = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      await uploadDocument(f);
      e.target.value = '';
    }
  };

  const onDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) await uploadDocument(f);
  };

  // 过滤：文件名搜索 + 标签筛选 + 类型筛选
  const filtered = documents.filter((d) => {
    if (search && !d.filename.toLowerCase().includes(search.toLowerCase())) return false;
    if (selectedType && d.doc_type !== selectedType) return false;
    if (selectedTags.size > 0) {
      const docTags = new Set(d.tags || []);
      // 选中的标签必须至少有一个在文档标签里（OR 语义）
      const hasAny = [...selectedTags].some((t) => docTags.has(t));
      if (!hasAny) return false;
    }
    return true;
  });

  const toggleTag = (tag: string) => {
    const next = new Set(selectedTags);
    if (next.has(tag)) next.delete(tag);
    else next.add(tag);
    setSelectedTags(next);
  };

  const handlePreview = (doc: Document) => {
    setPreviewDoc(doc);
    setPreviewOpen(true);
  };

  const handleEditMeta = (doc: Document) => {
    setMetaDoc(doc);
    setMetaOpen(true);
  };

  const handleShowVersions = (doc: Document) => {
    setPreviewDoc(doc);
    setPreviewOpen(true);
    // 版本面板在 DocumentViewer 内部，打开后自动可点
  };

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
      {/* 上传区 */}
      <div
        onDrop={onDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => inputRef.current?.click()}
        style={{
          border: '2px dashed var(--bg-elevated)', borderRadius: 8, padding: 24,
          textAlign: 'center', color: "var(--text-muted)", cursor: 'pointer', marginBottom: 16,
        }}
      >
        <p>{uploading ? t('kb.uploading') : t('kb.uploadClickHint')}</p>
        <p style={{ fontSize: 11 }}>{t('kb.supportedFormats')}</p>
        <input ref={inputRef} type="file"
          accept=".md,.markdown,.txt,.pdf,.docx,.xlsx,.xls,.pptx,.html,.htm,.png,.jpg,.jpeg"
          onChange={onPick} hidden />
      </div>

      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, display: 'flex', alignItems: 'flex-start', gap: 4 }}>
        <AlertTriangle size={12} strokeWidth={1.5} style={{ flexShrink: 0, marginTop: 1 }} />
        <span>{t('kb.docStorageHint')}</span>
      </p>

      {/* 工具栏：搜索 + 导出全部 */}
      {documents.length > 0 && (
        <>
          <TagFilter
            selectedTags={selectedTags}
            onToggleTag={toggleTag}
            onClearTags={() => setSelectedTags(new Set())}
            selectedType={selectedType}
            onSelectType={setSelectedType}
          />
          <div style={{ marginBottom: 12, display: 'flex', gap: 8 }}>
            <input
              type="text"
              placeholder={t('kb.searchFilenamePlaceholder')}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                flex: 1, background: "var(--bg-card)", border: '1px solid var(--bg-elevated)',
                borderRadius: 4, color: "var(--text-primary)", padding: '6px 8px', fontSize: 13,
              }}
            />
            <a
              href={exportZipUrl()}
              title={t('kb.exportAllZip')}
              style={{
                background: 'var(--bg-card)', border: '1px solid var(--bg-elevated)',
                color: 'var(--text-secondary)', borderRadius: 4, padding: '6px 12px',
                cursor: 'pointer', fontSize: 13, display: 'inline-flex', alignItems: 'center',
                gap: 4, textDecoration: 'none', flexShrink: 0,
              }}
            >
              <Upload size={14} /> {t('kb.exportAll')}
            </a>
          </div>
        </>
      )}

      {filtered.length === 0 ? (
        <EmptyState message={documents.length === 0 ? t('kb.noDocumentsHint') : t('kb.noMatchingDocuments')} />
      ) : (
        <div style={{ border: '1px solid var(--bg-card)', borderRadius: 8 }}>
          {filtered.map((d) => (
            <DocumentRow
              key={d.id}
              doc={d}
              onDelete={deleteDocument}
              onPreview={handlePreview}
              onEditMeta={handleEditMeta}
              onShowVersions={handleShowVersions}
            />
          ))}
        </div>
      )}

      {/* 全屏预览/编辑弹窗 */}
      <DocumentViewer doc={previewDoc} open={previewOpen} onOpenChange={setPreviewOpen} />

      {/* 元数据编辑弹窗 */}
      <DocumentMetaEditor doc={metaDoc} open={metaOpen} onOpenChange={setMetaOpen} />
    </div>
  );
}
