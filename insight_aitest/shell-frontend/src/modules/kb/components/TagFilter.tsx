import { useState, useEffect } from 'react';
import { Tag, Folder } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useKnowledgeStore } from '../store/knowledgeStore';

const DOC_TYPES = [
  { value: '', labelKey: 'kb.allTypes' },
  { value: 'requirement', labelKey: 'kb.typeRequirementDoc' },
  { value: 'design', labelKey: 'kb.typeDesignDoc' },
  { value: 'interface', labelKey: 'kb.typeInterfaceDoc' },
  { value: 'test', labelKey: 'kb.typeTestDoc' },
  { value: 'other', labelKey: 'kb.typeOther' },
];

interface TagFilterProps {
  /** 选中的标签集合 */
  selectedTags: Set<string>;
  onToggleTag: (tag: string) => void;
  onClearTags: () => void;
  /** 选中的文档类型 */
  selectedType: string;
  onSelectType: (type: string) => void;
}

/** 标签云 + 文档类型筛选器。 */
export function TagFilter({ selectedTags, onToggleTag, onClearTags, selectedType, onSelectType }: TagFilterProps) {
  const { t } = useTranslation();
  const { tags, loadTags } = useKnowledgeStore();
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    loadTags();
  }, []);

  if (tags.length === 0) return null;

  return (
    <div style={{ marginBottom: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
      {/* 文档类型筛选 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text-muted)' }}>
          <Folder size={12} /> {t('kb.typeLabel')}
        </span>
        {DOC_TYPES.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onSelectType(opt.value)}
            style={{
              background: selectedType === opt.value ? 'var(--accent)' : 'var(--bg-card)',
              color: selectedType === opt.value ? '#fff' : 'var(--text-secondary)',
              border: '1px solid var(--bg-elevated)',
              borderRadius: 4,
              padding: '2px 8px',
              cursor: 'pointer',
              fontSize: 11,
            }}
          >
            {t(opt.labelKey)}
          </button>
        ))}
      </div>

      {/* 标签云 */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 6, flexWrap: 'wrap' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
          <Tag size={12} /> {t('kb.tagsLabel')}
        </span>
        {selectedTags.size > 0 && (
          <button
            onClick={onClearTags}
            style={{ background: 'none', border: '1px solid var(--border-strong)', color: 'var(--text-muted)', borderRadius: 4, padding: '2px 8px', cursor: 'pointer', fontSize: 11 }}
          >
            {t('kb.clear')}
          </button>
        )}
        {(expanded ? tags : tags.slice(0, 8)).map((tagItem) => {
          const active = selectedTags.has(tagItem.tag);
          return (
            <button
              key={tagItem.tag}
              onClick={() => onToggleTag(tagItem.tag)}
              style={{
                background: active ? 'var(--accent)' : 'var(--bg-card)',
                color: active ? '#fff' : 'var(--text-secondary)',
                border: '1px solid var(--bg-elevated)',
                borderRadius: 12,
                padding: '2px 10px',
                cursor: 'pointer',
                fontSize: 11,
              }}
            >
              {tagItem.tag} <span style={{ opacity: 0.6 }}>{tagItem.count}</span>
            </button>
          );
        })}
        {tags.length > 8 && (
          <button
            onClick={() => setExpanded(!expanded)}
            style={{ background: 'none', border: '1px solid var(--border-strong)', color: 'var(--text-muted)', borderRadius: 4, padding: '2px 8px', cursor: 'pointer', fontSize: 11 }}
          >
            {expanded ? t('kb.collapse') : `+${tags.length - 8}`}
          </button>
        )}
      </div>
    </div>
  );
}
