import { FileText, Eye, Download, Tag as TagIcon, History } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { Document } from '../store/knowledgeStore';
import { useConfirmStore } from '../../../shared/store/confirmStore';

const STATUS_KEY: Record<string, string> = {
  pending: 'kb.statusWaiting',
  parsing: 'kb.statusParsing',
  chunking: 'kb.statusChunking',
  embedding: 'kb.statusEmbedding',
  ready: 'kb.statusReady',
  parse_failed: 'kb.statusParseFailed',
  embed_failed: 'kb.statusEmbedFailed',
  embed_partial: 'kb.statusEmbedPartial',
};

const STATUS_COLOR: Record<string, string> = {
  pending: "var(--text-secondary)",
  parsing: "var(--accent)",
  chunking: "var(--accent)",
  embedding: "var(--accent)",
  ready: 'var(--chart-4)',
  parse_failed: 'var(--error)',
  embed_failed: 'var(--error)',
  embed_partial: 'var(--chart-3)',
};

const DOC_TYPE_KEY: Record<string, string> = {
  requirement: 'kb.typeRequirement',
  design: 'kb.typeDesign',
  interface: 'kb.typeInterface',
  test: 'kb.typeTest',
  other: 'kb.typeOther',
};

interface DocumentRowProps {
  doc: Document;
  onDelete: (id: number) => void;
  onPreview: (doc: Document) => void;
  onEditMeta: (doc: Document) => void;
  onShowVersions: (doc: Document) => void;
}

export function DocumentRow({ doc, onDelete, onPreview, onEditMeta, onShowVersions }: DocumentRowProps) {
  const { t } = useTranslation();
  const statusKey = STATUS_KEY[doc.status];
  const statusColor = STATUS_COLOR[doc.status] ?? "var(--text-secondary)";
  const st = { text: statusKey ? t(statusKey) : doc.status, color: statusColor };
  const { confirm } = useConfirmStore();
  const typeLabel = doc.doc_type && DOC_TYPE_KEY[doc.doc_type] ? t(DOC_TYPE_KEY[doc.doc_type]) : '';

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px',
      borderBottom: '1px solid var(--bg-card)',
    }}>
      <span style={{ color: "var(--text-secondary)", display: 'inline-flex', alignItems: 'center', cursor: 'pointer' }} onClick={() => onPreview(doc)}>
        <FileText size={16} strokeWidth={1.5} />
      </span>
      <div style={{ flex: 1, minWidth: 0, cursor: 'pointer' }} onClick={() => onPreview(doc)}>
        <div style={{ fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-primary)' }}>
          {doc.filename}
        </div>
        <div style={{ fontSize: 11, color: "var(--text-muted)", display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          {doc.status === 'ready' && <span>{t('kb.chunkCharCount', { chunks: doc.chunk_count, chars: doc.char_count })}</span>}
          {typeLabel && <span style={{ background: 'var(--bg-card)', padding: '0 5px', borderRadius: 3 }}>{typeLabel}</span>}
          {doc.tags?.length > 0 && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
              <TagIcon size={10} /> {doc.tags.join(', ')}
            </span>
          )}
          {doc.error_message ? ` · ${doc.error_message}` : ''}
          {doc.description ? ` · ${doc.description}` : ''}
        </div>
      </div>
      <span style={{ color: st.color, fontSize: 12, flexShrink: 0 }}>{st.text}</span>

      {/* 操作按钮 */}
      <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
        <button onClick={() => onPreview(doc)} title={t('kb.preview')} style={iconBtnStyle}>
          <Eye size={14} />
        </button>
        <a href={`/api/modules/kb/documents/${doc.id}/raw`} download title={t('kb.download')} style={{ ...iconBtnStyle, textDecoration: 'none', display: 'inline-flex' }}>
          <Download size={14} />
        </a>
        <button onClick={() => onEditMeta(doc)} title={t('kb.metaInfo')} style={iconBtnStyle}>
          <TagIcon size={14} />
        </button>
        <button onClick={() => onShowVersions(doc)} title={t('kb.versionHistory')} style={iconBtnStyle}>
          <History size={14} />
        </button>
        <button
          onClick={() => confirm({
            title: t('kb.confirmDeleteTitle'),
            message: t('kb.confirmDeleteName', { name: doc.filename }),
            variant: 'danger',
            onConfirm: () => onDelete(doc.id),
          })}
          style={{ background: 'none', border: '1px solid var(--border-strong)', color: "var(--text-secondary)", padding: '2px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}
        >{t('kb.delete')}</button>
      </div>
    </div>
  );
}

const iconBtnStyle: React.CSSProperties = {
  background: 'none',
  border: '1px solid var(--bg-elevated)',
  color: 'var(--text-secondary)',
  padding: 3,
  borderRadius: 4,
  cursor: 'pointer',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
};
