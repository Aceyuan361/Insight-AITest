import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { FileText, X } from 'lucide-react';
import { useIsMobile } from '../../../shared/hooks/useIsMobile';

export function DocPreviewDrawer({
  filename,
  previewText,
  onClose,
}: {
  filename: string;
  previewText: string | null;
  onClose: () => void;
}) {
  const isMobile = useIsMobile();
  const { t } = useTranslation();
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.5)',
        zIndex: 9998,
        display: 'flex',
        justifyContent: 'flex-end',
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: isMobile ? '100%' : 480,
          maxWidth: isMobile ? '100vw' : '90vw',
          height: '100dvh',
          background: 'var(--bg-base)',
          borderLeft: '1px solid var(--bg-card)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '12px 16px',
            borderBottom: '1px solid var(--bg-card)',
          }}
        >
          <span style={{ fontSize: 13, color: "var(--text-secondary)", display: 'inline-flex', alignItems: 'center', gap: 4 }}><FileText size={13} strokeWidth={1.5} />{filename}</span>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: "var(--text-secondary)", cursor: 'pointer', display: 'inline-flex', alignItems: 'center' }}
          >
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>
        <div
          className="markdown-body"
          style={{ flex: 1, overflow: 'auto', padding: 16, color: "var(--text-secondary)", fontSize: 13, whiteSpace: 'pre-wrap' }}
        >
          {previewText || t('ai.noPreview')}
        </div>
      </div>
    </div>
  );
}
