import { useState, useEffect } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X, Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useKnowledgeStore, type Document } from '../store/knowledgeStore';

const DOC_TYPE_OPTIONS = [
  { value: '', labelKey: 'kb.typeUncategorized' },
  { value: 'requirement', labelKey: 'kb.typeRequirementDoc' },
  { value: 'design', labelKey: 'kb.typeDesignDoc' },
  { value: 'interface', labelKey: 'kb.typeInterfaceDoc' },
  { value: 'test', labelKey: 'kb.typeTestDoc' },
  { value: 'other', labelKey: 'kb.typeOther' },
];

interface DocumentMetaEditorProps {
  doc: Document | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** 文档元数据编辑弹窗：标签、类型、描述。 */
export function DocumentMetaEditor({ doc, open, onOpenChange }: DocumentMetaEditorProps) {
  const { t } = useTranslation();
  const { updateMeta } = useKnowledgeStore();
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [docType, setDocType] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (doc) {
      setTags(doc.tags || []);
      setDocType(doc.doc_type || '');
      setDescription(doc.description || '');
      setTagInput('');
    }
  }, [doc?.id, open]);

  if (!doc) return null;

  const addTag = () => {
    const t = tagInput.trim();
    if (t && !tags.includes(t)) {
      setTags([...tags, t]);
    }
    setTagInput('');
  };

  const removeTag = (t: string) => setTags(tags.filter((x) => x !== t));

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateMeta(doc.id, { tags, doc_type: docType, description });
      onOpenChange(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 2000 }} />
        <Dialog.Content
          style={{
            position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
            width: 'min(480px, 90vw)', background: 'var(--bg-base)',
            border: '1px solid var(--bg-elevated)', borderRadius: 10, zIndex: 2001, outline: 'none',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--bg-card)' }}>
            <Dialog.Title style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
              {t('kb.editDocInfo')}
            </Dialog.Title>
            <Dialog.Close asChild>
              <button style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                <X size={16} />
              </button>
            </Dialog.Close>
          </div>

          <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* 文件名（只读） */}
            <div>
              <label style={labelStyle}>{t('kb.fileName')}</label>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{doc.filename}</div>
            </div>

            {/* 文档类型 */}
            <div>
              <label style={labelStyle}>{t('kb.docType')}</label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                style={inputStyle}
              >
                {DOC_TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{t(o.labelKey)}</option>
                ))}
              </select>
            </div>

            {/* 标签 */}
            <div>
              <label style={labelStyle}>{t('kb.tags')}</label>
              <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTag(); } }}
                  placeholder={t('kb.tagInputPlaceholder')}
                  style={{ ...inputStyle, flex: 1 }}
                />
                <button onClick={addTag} style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-strong)', color: 'var(--text-secondary)', borderRadius: 4, padding: '0 10px', cursor: 'pointer' }}>
                  <Plus size={14} />
                </button>
              </div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {tags.map((t) => (
                  <span key={t} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, background: 'var(--bg-card)', border: '1px solid var(--bg-elevated)', borderRadius: 12, padding: '2px 10px', fontSize: 12, color: 'var(--text-primary)' }}>
                    {t}
                    <button onClick={() => removeTag(t)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 0, display: 'inline-flex' }}>
                      <X size={12} />
                    </button>
                  </span>
                ))}
              </div>
            </div>

            {/* 描述 */}
            <div>
              <label style={labelStyle}>{t('kb.description')}</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={t('kb.descriptionPlaceholder')}
                rows={3}
                style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, padding: '0 20px 16px' }}>
            <button
              onClick={() => onOpenChange(false)}
              style={{ background: 'none', border: '1px solid var(--bg-elevated)', color: 'var(--text-secondary)', borderRadius: 6, padding: '6px 16px', cursor: 'pointer', fontSize: 13 }}
            >
              {t('kb.cancel')}
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              style={{ background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: 6, padding: '6px 16px', cursor: 'pointer', fontSize: 13, fontWeight: 600, opacity: saving ? 0.6 : 1 }}
            >
              {saving ? t('kb.saving') : t('kb.save')}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: 12,
  color: 'var(--text-muted)',
  marginBottom: 4,
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  background: 'var(--bg-card)',
  border: '1px solid var(--bg-elevated)',
  borderRadius: 4,
  color: 'var(--text-primary)',
  padding: '6px 8px',
  fontSize: 13,
  outline: 'none',
};
