import { useState, useEffect } from 'react';
import mammoth from 'mammoth';
import { Download } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface DocxViewerProps {
  /** docx 原始文件 URL（GET /raw） */
  url: string;
}

/** docx 预览器：用 mammoth 将 docx 转 HTML 渲染（只读预览）。
 *
 * 编辑场景：docx 是复杂排版二进制格式，在线 WYSIWYG 编辑保真度难保证。
 * 提供「下载 → 本地编辑 → 重新上传」的版本替换流程。
 */
export function DocxViewer({ url }: DocxViewerProps) {
  const { t } = useTranslation();
  const [html, setHtml] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(url)
      .then((r) => r.arrayBuffer())
      .then((buf) => mammoth.convertToHtml({ arrayBuffer: buf }))
      .then((result) => {
        if (!cancelled) {
          setHtml(result.value);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e.message || t('kb.docxParseFailed'));
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [url]);

  if (loading) {
    return <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>{t('kb.parseDocx')}</div>;
  }
  if (error) {
    return (
      <div style={{ padding: 24, textAlign: 'center', color: 'var(--error)', fontSize: 13 }}>
        {t('kb.docxParseFailedMsg', { error })}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '6px 12px', borderBottom: '1px solid var(--bg-card)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('kb.docxReadonlyHintFull')}</span>
        <a href={url} download style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--accent)', fontSize: 12 }}>
          <Download size={14} /> {t('kb.download')}
        </a>
      </div>
      <div
        className="docx-body"
        style={{ flex: 1, overflow: 'auto', padding: 24, fontSize: 13, lineHeight: 1.7, color: 'var(--text-primary)' }}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
