import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useTranslation } from 'react-i18next';

interface TextEditorProps {
  initialText: string;
  filename: string;
  onSave: (text: string) => Promise<void>;
  saving: boolean;
  readOnly?: boolean;
}

/** 纯文本/markdown/html 编辑器：左侧编辑（textarea），md 文件右侧实时预览。 */
export function TextEditor({ initialText, filename, onSave, saving, readOnly = false }: TextEditorProps) {
  const { t } = useTranslation();
  const [text, setText] = useState(initialText);
  const [dirty, setDirty] = useState(false);
  const [showPreview, setShowPreview] = useState(true);

  useEffect(() => {
    setText(initialText);
    setDirty(false);
  }, [initialText]);

  const isMarkdown = /\.(md|markdown)$/i.test(filename);

  const handleChange = (v: string) => {
    setText(v);
    setDirty(v !== initialText);
  };

  const handleSave = async () => {
    await onSave(text);
    setDirty(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', borderBottom: '1px solid var(--bg-card)' }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {isMarkdown && !readOnly && (
            <button
              onClick={() => setShowPreview(!showPreview)}
              style={{ background: 'none', border: '1px solid var(--border-strong)', color: 'var(--text-secondary)', padding: '2px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}
            >
              {showPreview ? t('kb.hidePreview') : t('kb.showPreview')}
            </button>
          )}
          {dirty && <span style={{ fontSize: 11, color: 'var(--accent)' }}>{t('kb.unsaved')}</span>}
        </div>
        {!readOnly && (
          <button
            onClick={handleSave}
            disabled={!dirty || saving}
            style={{
              background: dirty && !saving ? 'var(--accent)' : 'var(--bg-elevated)',
              color: dirty && !saving ? '#fff' : 'var(--text-muted)',
              border: 'none', padding: '4px 16px', borderRadius: 4, cursor: dirty && !saving ? 'pointer' : 'not-allowed', fontSize: 12,
            }}
          >
            {saving ? t('kb.saving') : t('kb.save')}
          </button>
        )}
      </div>
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <textarea
          value={text}
          onChange={(e) => handleChange(e.target.value)}
          readOnly={readOnly}
          spellCheck={false}
          style={{
            flex: isMarkdown && showPreview ? 1 : 2,
            width: '100%',
            background: 'var(--bg-card)',
            border: 'none',
            color: 'var(--text-primary)',
            padding: 12,
            fontFamily: 'ui-monospace, "Cascadia Code", "Source Code Pro", monospace',
            fontSize: 13,
            lineHeight: 1.6,
            resize: 'none',
            outline: 'none',
          }}
        />
        {isMarkdown && showPreview && (
          <div
            className="markdown-body"
            style={{
              flex: 1,
              padding: 16,
              overflow: 'auto',
              borderLeft: '1px solid var(--bg-card)',
              fontSize: 13,
              lineHeight: 1.7,
            }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
