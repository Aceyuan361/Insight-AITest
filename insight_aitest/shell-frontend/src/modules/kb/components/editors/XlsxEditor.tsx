import { useState, useEffect, useRef } from 'react';
import * as XLSX from 'xlsx';
import { Download, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface XlsxEditorProps {
  url: string;
  filename: string;
  onSave: (blob: Blob, filename: string) => Promise<void>;
  saving: boolean;
  readOnly?: boolean;
}

/**
 * xlsx 在线编辑器（基于 Univer + SheetJS 桥接）。
 *
 * 加载 .xlsx → SheetJS 解析为 Univer workbook 数据 → Univer 可视化编辑
 * → 导出回 SheetJS workbook → 写 .xlsx Blob 上传后端。
 *
 * 纯前端方案：Univer 官方 xlsx 导入/导出依赖 Univer Server，
 * 这里用 SheetJS 做 IWorkbookData ↔ XLSX.WorkBook 的桥接转换。
 */
export function XlsxEditor({ url, filename, onSave, saving, readOnly = false }: XlsxEditorProps) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const univerRef = useRef<any>(null);
  const apiRef = useRef<any>(null);

  useEffect(() => {
    let disposed = false;

    async function init() {
      try {
        setLoading(true);
        // 1. 动态导入 Univer presets（懒加载）
        const { createUniver, defaultTheme, LocaleType } = await import('@univerjs/presets');
        const { UniverSheetsCorePreset } = await import('@univerjs/preset-sheets-core');
        await import('@univerjs/preset-sheets-core/lib/index.css').catch(() => {});

        if (disposed || !containerRef.current) return;

        // 2. 加载 xlsx 文件 → SheetJS workbook → 转 Univer workbook data
        const buf = await fetch(url).then((r) => r.arrayBuffer());
        const wb = XLSX.read(buf, { type: 'array' });
        const workbookData = xlsxToUniver(wb, filename);

        // 3. 初始化 Univer
        const { univerAPI, univer } = createUniver({
          locale: LocaleType.EN_US,
          theme: defaultTheme,
          presets: [UniverSheetsCorePreset({ container: containerRef.current })],
        });
        univerAPI.createWorkbook(workbookData);
        univerRef.current = univer;
        apiRef.current = univerAPI;

        if (!disposed) setLoading(false);
      } catch (e: any) {
        if (!disposed) {
          setError(e.message || t('kb.xlsxLoadFailed'));
          setLoading(false);
        }
      }
    }

    init();

    return () => {
      disposed = true;
      if (univerRef.current?.dispose) {
        try { univerRef.current.dispose(); } catch { /* 静默 */ }
      }
      univerRef.current = null;
      apiRef.current = null;
    };
  }, [url, filename]);

  /** SheetJS workbook → Univer IWorkbookData（桥接转换） */
  function xlsxToUniver(wb: XLSX.WorkBook, name: string) {
    const sheets: Record<string, any> = {};
    for (const sheetName of wb.SheetNames) {
      const ws = wb.Sheets[sheetName];
      const range = XLSX.utils.decode_range(ws['!ref'] || 'A1');
      const cellData: Record<string, any> = {};
      for (let r = range.s.r; r <= range.e.r; r++) {
        for (let c = range.s.c; c <= range.e.c; c++) {
          const addr = XLSX.utils.encode_cell({ r, c });
          const cell = ws[addr];
          if (cell == null) continue;
          cellData[`${r}_${c}`] = {
            v: cell.v ?? '',
            t: cell.t === 'n' ? 2 : cell.t === 'b' ? 3 : 1, // 1=string 2=number 3=boolean
          };
        }
      }
      sheets[sheetName] = {
        id: sheetName,
        name: sheetName,
        cellData,
        rowCount: Math.max(range.e.r + 1, 20),
        columnCount: Math.max(range.e.c + 1, 10),
      };
    }
    return {
      id: 'workbook-' + Date.now(),
      name,
      sheets,
    };
  }

  /** Univer workbook → SheetJS workbook（导出转换） */
  function univerToXlsx(): XLSX.WorkBook {
    const api = apiRef.current;
    const fWorkbook = api?.getActiveWorkbook?.();
    const snapshot = fWorkbook?.getSnapshot?.() || fWorkbook?.save?.();
    const wb = XLSX.utils.book_new();
    const sheets = snapshot?.sheets || {};
    for (const [, sheetData] of Object.entries(sheets)) {
      const sd = sheetData as any;
      const aoa: any[][] = [];
      const cellData = sd.cellData || {};
      for (const [key, cell] of Object.entries(cellData)) {
        const [r, c] = key.split('_').map(Number);
        if (!aoa[r]) aoa[r] = [];
        const cv = (cell as any).v;
        aoa[r][c] = cv ?? '';
      }
      const ws = XLSX.utils.aoa_to_sheet(aoa);
      XLSX.utils.book_append_sheet(wb, ws, sd.name || 'Sheet');
    }
    return wb;
  }

  const handleSave = async () => {
    try {
      const wb = univerToXlsx();
      const out = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
      const blob = new Blob([out], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      await onSave(blob, filename);
    } catch (e: any) {
      setError(t('kb.exportFailed', { message: e.message || String(e) }));
    }
  };

  const handleDownload = () => {
    try {
      const wb = univerToXlsx();
      XLSX.writeFile(wb, filename);
    } catch (e: any) {
      setError(t('kb.downloadFailed', { message: e.message || String(e) }));
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
        <Loader2 size={16} className="animate-spin" /> {t('kb.loadXlsxEditor')}
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24, textAlign: 'center', color: 'var(--error)', fontSize: 13 }}>
        {error}
        <br />
        <a href={url} download style={{ color: 'var(--accent)', fontSize: 12, marginTop: 8, display: 'inline-block' }}>
          {t('kb.downloadOriginalLocal')}
        </a>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '6px 12px', borderBottom: '1px solid var(--bg-card)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          {readOnly ? t('kb.xlsxReadOnlyHint') : t('kb.xlsxEditHint')}
        </span>
        <div style={{ display: 'flex', gap: 6 }}>
          {!readOnly && (
            <button onClick={handleSave} disabled={saving} style={btnStyle(saving)}>
              {saving ? t('kb.saving') : t('kb.save')}
            </button>
          )}
          <a href={url} download onClick={(e) => { e.preventDefault(); handleDownload(); }} style={{ ...btnStyle(false), textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <Download size={13} /> {t('kb.download')}
          </a>
        </div>
      </div>
      <div ref={containerRef} style={{ flex: 1, overflow: 'hidden' }} />
    </div>
  );
}

function btnStyle(disabled: boolean): React.CSSProperties {
  return {
    background: disabled ? 'var(--bg-elevated)' : 'var(--accent)',
    color: disabled ? 'var(--text-muted)' : '#fff',
    border: 'none',
    padding: '4px 12px',
    borderRadius: 4,
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontSize: 12,
  };
}
