import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { Citation } from '../store/conversationStore';

export function CitationCard({
  citation,
  index,
  highlight,
}: {
  citation: Citation;
  index: number;
  /** 触发高亮闪烁 + 自动展开。每次从 false→true 重触发。 */
  highlight?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const { t } = useTranslation();

  // highlight 变化时：自动展开 + 重启闪烁动画
  useEffect(() => {
    if (highlight) setExpanded(true);
  }, [highlight]);

  return (
    <div
      data-cite-index={index}
      className={highlight ? 'cite-card cite-flash' : 'cite-card'}
      style={{
        background: highlight ? "var(--accent-deep)" : "var(--bg-card)",
        border: highlight ? '1px solid var(--accent)' : '1px solid var(--bg-card)',
        borderRadius: 6,
        padding: 8,
        marginTop: 6,
        fontSize: 12,
        transition: 'background 0.3s, border-color 0.3s',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', color: "var(--text-secondary)" }}>
        <span>
          [{index}] {citation.document_name} · {t('ai.citationSnippet', { index: citation.chunk_index })}
        </span>
        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            background: 'none',
            border: 'none',
            color: "var(--accent)",
            cursor: 'pointer',
            fontSize: 11,
          }}
        >
          {expanded ? t('ai.citationCollapse') : t('ai.citationExpand')}
        </button>
      </div>
      {expanded && (
        <div style={{ marginTop: 6, color: "var(--text-secondary)", maxHeight: 120, overflow: 'auto' }}>
          {citation.snippet}
        </div>
      )}
    </div>
  );
}
