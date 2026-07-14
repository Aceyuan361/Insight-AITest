import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ChevronRight, BrainCircuit } from 'lucide-react';

export function ThinkingPanel({
  thinking,
  streaming,
}: {
  thinking: string;
  streaming?: boolean;
}) {
  const [expanded, setExpanded] = useState(streaming ?? false);
  const charCount = thinking.length;
  const { t } = useTranslation();

  return (
    <div
      style={{
        marginBottom: 8,
        border: '1px solid var(--bg-card)',
        borderRadius: 6,
        background: 'var(--bg-elevated)',
        overflow: 'hidden',
      }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          width: '100%',
          textAlign: 'left',
          background: 'none',
          border: 'none',
          color: "var(--accent-hover)",
          padding: '6px 10px',
          cursor: 'pointer',
          fontSize: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}
      >
        <span>{expanded ? <ChevronDown size={12} strokeWidth={1.5} /> : <ChevronRight size={12} strokeWidth={1.5} />}</span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>{streaming ? <><BrainCircuit size={12} strokeWidth={1.5} />{t('ai.thinking')}</> : <><BrainCircuit size={12} strokeWidth={1.5} />{t('ai.thinkingProcess')}（{charCount}）</>}</span>
      </button>
      {expanded && (
        <div
          style={{
            padding: '8px 12px',
            color: "var(--text-secondary)",
            fontSize: 12,
            lineHeight: 1.6,
            maxHeight: 240,
            overflow: 'auto',
            whiteSpace: 'pre-wrap',
            borderTop: '1px solid var(--bg-card)',
          }}
        >
          {thinking}
        </div>
      )}
    </div>
  );
}
