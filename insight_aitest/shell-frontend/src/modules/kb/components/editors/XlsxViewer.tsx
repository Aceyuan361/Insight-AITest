import { useState, useEffect } from 'react';
import * as XLSX from 'xlsx';
import { Download } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface XlsxViewerProps {
  url: string;
  filename: string;
}

interface SheetData {
  name: string;
  rows: (string | number | null)[][];
}

/** xlsx/pptx 预览器：用 SheetJS 读取电子表格，渲染为 HTML 表格（只读）。
 * 支持多 sheet 切换。编辑走下载→上传替换流程。
 */
export function XlsxViewer({ url, filename }: XlsxViewerProps) {
  const { t } = useTranslation();
  const [sheets, setSheets] = useState<SheetData[]>([]);
  const [activeSheet, setActiveSheet] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(url)
      .then((r) => r.arrayBuffer())
      .then((buf) => {
        const wb = XLSX.read(buf, { type: 'array' });
        const result: SheetData[] = wb.SheetNames.map((name) => {
          const ws = wb.Sheets[name];
          const rows = XLSX.utils.sheet_to_json<(string | number | null)[]>(ws, {
            header: 1,
            defval: null,
            blankrows: false,
          });
          return { name, rows: rows.slice(0, 500) }; // 限制最多 500 行
        });
        if (!cancelled) {
          setSheets(result);
          setActiveSheet(0);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e.message || t('kb.xlsxParseFailed'));
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [url]);

  if (loading) return <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>{t('kb.parseFile', { name: filename })}</div>;
  if (error) return <div style={{ padding: 24, textAlign: 'center', color: 'var(--error)', fontSize: 13 }}>{t('kb.fileParseFailed', { name: filename, error })}</div>;
  if (!sheets.length) return <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>{t('kb.emptyFile')}</div>;

  const sheet = sheets[activeSheet];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '6px 12px', borderBottom: '1px solid var(--bg-card)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {sheets.map((s, i) => (
            <button
              key={i}
              onClick={() => setActiveSheet(i)}
              style={{
                background: i === activeSheet ? 'var(--accent)' : 'none',
                color: i === activeSheet ? '#fff' : 'var(--text-secondary)',
                border: '1px solid var(--border-strong)',
                padding: '2px 8px',
                borderRadius: 4,
                cursor: 'pointer',
                fontSize: 12,
              }}
            >
              {s.name}
            </button>
          ))}
        </div>
        <a href={url} download style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--accent)', fontSize: 12, flexShrink: 0 }}>
          <Download size={14} /> {t('kb.download')}
        </a>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: 8 }}>
        <table style={{ borderCollapse: 'collapse', fontSize: 12, width: '100%' }}>
          <tbody>
            {sheet.rows.map((row, ri) => (
              <tr key={ri}>
                {row.map((cell, ci) => (
                  <td
                    key={ci}
                    style={{
                      border: '1px solid var(--bg-elevated)',
                      padding: '4px 8px',
                      background: ri === 0 ? 'var(--bg-card)' : 'transparent',
                      color: 'var(--text-primary)',
                      fontWeight: ri === 0 ? 600 : 400,
                      whiteSpace: 'nowrap',
                      maxWidth: 300,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {cell ?? ''}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
