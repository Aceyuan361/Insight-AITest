import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import type { Attachment } from '../store/conversationStore';
import { X } from 'lucide-react';

const BASE = '/api/modules/ai';

export function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (text: string, attachments?: Attachment[]) => void;
  disabled: boolean;
}) {
  const [text, setText] = useState('');
  const [pending, setPending] = useState<File[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);
  const { t } = useTranslation();

  const submit = async () => {
    if ((!text.trim() && pending.length === 0) || disabled) return;

    // 上传待发文件
    let attachments: Attachment[] | undefined;
    if (pending.length > 0) {
      const fd = new FormData();
      pending.forEach((f) => fd.append('files', f));
      try {
        const r = await fetch(`${BASE}/chat/attachments`, { method: 'POST', body: fd });
        attachments = (await r.json()).attachments;
      } catch {
        toast.error(t('ai.attachUploadFailed'));
        return;
      }
    }

    onSend(text.trim(), attachments);
    setText('');
    setPending([]);
  };

  const onPaste = (e: React.ClipboardEvent) => {
    const files = Array.from(e.clipboardData.files).filter((f) =>
      f.type.startsWith('image/')
    );
    if (files.length) {
      e.preventDefault();
      setPending((p) => [...p, ...files]);
    }
  };

  return (
    <div style={{ padding: 12, borderTop: '1px solid var(--bg-card)' }}>
      {pending.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
          {pending.map((f, i) => (
            <span
              key={i}
              style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--bg-elevated)',
                borderRadius: 4,
                padding: '2px 8px',
                fontSize: 11,
                color: "var(--accent-hover)",
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
              }}
              onClick={() => setPending((p) => p.filter((_, idx) => idx !== i))}
            >
              {f.name} <X size={11} strokeWidth={1.5} />
            </span>
          ))}
        </div>
      )}
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept="image/*,.md,.txt,.pdf,.docx,.xlsx,.pptx,.html"
          style={{ display: 'none' }}
          onChange={(e) => {
            const files = Array.from(e.target.files ?? []);
            setPending((p) => [...p, ...files]);
            if (fileRef.current) fileRef.current.value = '';
          }}
        />
        <button
          onClick={() => fileRef.current?.click()}
          disabled={disabled}
          style={{
            background: "var(--bg-card)",
            border: '1px solid var(--bg-elevated)',
            borderRadius: 6,
            color: "var(--text-secondary)",
            padding: '0 12px',
            cursor: 'pointer',
            fontSize: 18,
          }}
          title={t('ai.addAttachment')}
        >
          ＋
        </button>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onPaste={onPaste}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder={t('ai.inputHint')}
          rows={2}
          style={{
            flex: 1,
            background: "var(--bg-card)",
            border: '1px solid var(--bg-elevated)',
            borderRadius: 6,
            color: "var(--text-primary)",
            padding: 8,
            resize: 'none',
            fontFamily: 'inherit',
          }}
        />
        <button
          onClick={submit}
          disabled={disabled || (!text.trim() && pending.length === 0)}
          style={{
            background: "var(--accent)",
            color: "var(--bg-base)",
            border: 'none',
            borderRadius: 6,
            padding: '0 16px',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          {t('ai.send')}
        </button>
      </div>
    </div>
  );
}
