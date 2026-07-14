import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { Attachment } from '../store/conversationStore';
import { ImageLightbox } from './ImageLightbox';
import { DocPreviewDrawer } from './DocPreviewDrawer';
import { Image, FileText } from 'lucide-react';

const BASE = '/api/modules/ai';

export function AttachmentChips({ attachments }: { attachments: Attachment[] }) {
  const [preview, setPreview] = useState<Attachment | null>(null);
  const { t } = useTranslation();

  return (
    <>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
        {attachments.map((att) => (
          <div
            key={att.id}
            onClick={() => setPreview(att)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              background: "var(--bg-card)",
              border: '1px solid var(--bg-elevated)',
              borderRadius: 4,
              padding: '3px 8px',
              fontSize: 11,
              color: "var(--accent-hover)",
              cursor: 'pointer',
            }}
            title={t('ai.clickToPreview')}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center' }}>{att.kind === 'image' ? <Image size={12} strokeWidth={1.5} /> : <FileText size={12} strokeWidth={1.5} />}</span>
            <span>{att.filename}</span>
          </div>
        ))}
      </div>
      {preview && preview.kind === 'image' && (
        <ImageLightbox
          url={`${BASE}/chat/attachments/${preview.id}`}
          filename={preview.filename}
          onClose={() => setPreview(null)}
        />
      )}
      {preview && preview.kind === 'document' && (
        <DocPreviewDrawer
          filename={preview.filename}
          previewText={preview.preview_text ?? null}
          onClose={() => setPreview(null)}
        />
      )}
    </>
  );
}
