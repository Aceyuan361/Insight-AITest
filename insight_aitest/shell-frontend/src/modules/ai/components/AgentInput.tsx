import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTaskStore } from '../store/taskStore';
import { glassTextarea, primaryButton, ghostButton, text as agentText, SPRING } from './agentStyles';
import { X, Square } from 'lucide-react';

export function AgentInput() {
  const { sendIntent, addPendingFiles, removePendingFile, pendingFileNames, phase, stopStreaming } = useTaskStore();
  const [text, setText] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const busy = phase === 'uploading' || phase === 'understanding' || phase === 'strategizing' || phase === 'executing';
  const { t } = useTranslation();

  const submit = () => {
    if (busy) return;
    if (!text.trim() && pendingFileNames.length === 0) return;
    sendIntent(text.trim());
    setText('');
  };

  const onPickFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    addPendingFiles(Array.from(files));
    if (fileRef.current) fileRef.current.value = '';
  };

  const onPaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    const imageFiles: File[] = [];
    for (const item of items) {
      if (item.type.startsWith('image/')) {
        const f = item.getAsFile();
        if (f) imageFiles.push(f);
      }
    }
    if (imageFiles.length > 0) {
      e.preventDefault();
      addPendingFiles(imageFiles);
    }
  };

  const disabled = busy || (!text.trim() && pendingFileNames.length === 0);

  return (
    <div>
      {/* 待发送文件标签 */}
      {pendingFileNames.length > 0 && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
          {pendingFileNames.map((f, i) => (
            <span
              key={i}
              onClick={() => removePendingFile(i)}
              style={{
                fontSize: 11,
                color: agentText.accent,
                background: 'var(--bg-elevated)',
                border: '1px solid rgba(16,185,129,0.2)',
                padding: '3px 10px',
                borderRadius: 999,
                cursor: 'pointer',
                transition: `all 0.2s ${SPRING}`,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(16,185,129,0.14)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(16,185,129,0.08)'; }}
            >
              {f}
              <span style={{ opacity: 0.6, fontSize: 10, display: 'inline-flex', alignItems: 'center' }}><X size={12} strokeWidth={1.5} /></span>
            </span>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".md,.markdown,.txt,.pdf,.doc,.docx,.png,.jpg,.jpeg,.gif,.webp"
          onChange={(e) => onPickFiles(e.target.files)}
          hidden
        />
        <button
          onClick={() => fileRef.current?.click()}
          style={{
            ...ghostButton,
            padding: '8px 12px',
            borderRadius: 10,
            fontSize: 16,
            flexShrink: 0,
            opacity: busy ? 0.4 : 1,
          }}
          disabled={busy}
          title={t('ai.addFile')}
        >
          +
        </button>
        <textarea
          style={glassTextarea}
          placeholder={
            pendingFileNames.length > 0
              ? t('ai.placeholderWithFiles')
              : t('ai.placeholderDefault')
          }
          value={text}
          onChange={(e) => setText(e.target.value)}
          onPaste={onPaste}
          onKeyDown={(e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') submit();
          }}
          rows={1}
          disabled={busy}
        />
        <button
          onClick={busy ? stopStreaming : submit}
          disabled={!busy && disabled}
          style={{
            ...primaryButton,
            flexShrink: 0,
            opacity: busy ? 1 : (disabled ? 0.35 : 1),
            transform: 'none',
            transition: `all 0.15s ${SPRING}`,
            ...(busy ? { background: 'var(--error)', color: '#fff' } : {}),
          }}
          title={busy ? t('ai.stopGen') : t('ai.send')}
        >
          {busy ? <Square size={14} strokeWidth={2.5} fill="currentColor" /> : t('ai.send')}
        </button>
      </div>
    </div>
  );
}
