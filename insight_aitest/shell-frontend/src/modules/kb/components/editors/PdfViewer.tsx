import { useState } from 'react';
import { Document as PdfDocument, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

// 配置 pdfjs worker（使用与 react-pdf 匹配的 pdfjs-dist 版本）
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface PdfViewerProps {
  url: string;
}

/** PDF 预览器（react-pdf + pdf.js），支持翻页，只读。 */
export function PdfViewer({ url }: PdfViewerProps) {
  const { t } = useTranslation();
  const [numPages, setNumPages] = useState(0);
  const [pageNum, setPageNum] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const onDocLoad = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPageNum(1);
    setError(null);
  };

  const onError = (err: Error) => {
    setError(err.message || t('kb.pdfLoadFailed'));
  };

  if (error) {
    return (
      <div style={{ padding: 24, textAlign: 'center', color: 'var(--error)', fontSize: 13 }}>
        {t('kb.pdfLoadFailedMsg', { error })}
        <br />
        <a href={url} download style={{ color: 'var(--accent)', fontSize: 12, marginTop: 8, display: 'inline-block' }}>
          {t('kb.clickDownloadOriginal')}
        </a>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-base)' }}>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, padding: 8, borderBottom: '1px solid var(--bg-card)' }}>
        <button
          onClick={() => setPageNum(Math.max(1, pageNum - 1))}
          disabled={pageNum <= 1}
          style={{ background: 'none', border: '1px solid var(--border-strong)', color: 'var(--text-secondary)', borderRadius: 4, cursor: pageNum <= 1 ? 'not-allowed' : 'pointer', padding: 2, opacity: pageNum <= 1 ? 0.4 : 1 }}
        >
          <ChevronLeft size={16} />
        </button>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          {t('kb.pdfPageInfo', { current: pageNum, total: numPages || '?' })}
        </span>
        <button
          onClick={() => setPageNum(Math.min(numPages, pageNum + 1))}
          disabled={pageNum >= numPages}
          style={{ background: 'none', border: '1px solid var(--border-strong)', color: 'var(--text-secondary)', borderRadius: 4, cursor: pageNum >= numPages ? 'not-allowed' : 'pointer', padding: 2, opacity: pageNum >= numPages ? 0.4 : 1 }}
        >
          <ChevronRight size={16} />
        </button>
      </div>
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', justifyContent: 'center', padding: 16 }}>
        <PdfDocument file={url} onLoadSuccess={onDocLoad} onLoadError={onError} loading={<div style={{ padding: 24, color: 'var(--text-muted)', fontSize: 13 }}>{t('kb.loadingShort')}</div>}>
          <Page pageNumber={pageNum} width={Math.min(700, window.innerWidth - 120)} />
        </PdfDocument>
      </div>
    </div>
  );
}
