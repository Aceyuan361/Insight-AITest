import { useEffect, useMemo, useRef, useState } from 'react';
import { Camera, AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import i18n from '../../../shared/i18n';
import { useCaseStore } from '../store/caseStore';
import { useProjectStore } from '../../../shared/store/projectStore';

const inputStyle: React.CSSProperties = {
  background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', borderRadius: 4,
  color: "var(--text-primary)", padding: '8px', fontFamily: 'inherit', fontSize: 13,
  width: '100%',
};
const labelStyle: React.CSSProperties = { fontSize: 12, color: "var(--text-secondary)", marginBottom: 6 };
const primaryBtn: React.CSSProperties = {
  background: "var(--accent)", color: "var(--bg-base)", border: 'none', borderRadius: 6,
  padding: '8px 20px', cursor: 'pointer', fontWeight: 600,
};

/** File 转纯 base64（去掉 data:...;base64, 前缀，后端 client.py 会重新拼回 data URL） */
function fileToBase64(file: File): Promise<{ data: string; mime: string }> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // result 形如 "data:image/png;base64,XXXX"，取逗号后
      const commaIdx = result.indexOf(',');
      resolve({
        data: commaIdx >= 0 ? result.slice(commaIdx + 1) : result,
        mime: file.type || 'image/png',
      });
    };
    reader.onerror = () => reject(new Error(i18n.t('testcase.fileReadFailed')));
    reader.readAsDataURL(file);
  });
}

/**
 * 监听 AI 任务 SSE 流（GET /api/modules/ai/tasks/{id}/stream）。
 * 沿用 taskStore.streamTask 的 fetch + ReadableStream 解析方式。
 * 收到 done/error/cancelled 事件后 resolve。
 */
async function streamImageTask(taskId: number): Promise<void> {
  const res = await fetch(`/api/modules/ai/tasks/${taskId}/stream`);
  if (!res.body) return;
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop()!;
    for (const evt of events) {
      const type = evt.match(/^event: (.+)$/m)?.[1];
      const dataStr = evt.match(/^data: (.+)$/m)?.[1] ?? '{}';
      let data: Record<string, unknown>;
      try { data = JSON.parse(dataStr); } catch { continue; }
      if (type === 'error' && typeof data.message === 'string') {
        throw new Error(data.message);
      }
      if (type === 'done' || type === 'error' || type === 'cancelled') return;
    }
  }
}

export function ImageGeneratePanel({ onDone }: { onDone?: () => void }) {
  const { t } = useTranslation();
  const { createQuickTask } = useCaseStore();
  const { currentProjectId, currentVersionId } = useProjectStore();
  const [files, setFiles] = useState<File[]>([]);
  const [baseUrl, setBaseUrl] = useState('');
  const [pointSummary, setPointSummary] = useState('');
  const [error, setError] = useState('');
  const [imageGenerating, setImageGenerating] = useState(false);
  const [genStatus, setGenStatus] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const addFiles = (newFiles: File[]) => {
    const images = newFiles.filter((f) => f.type.startsWith('image/'));
    if (images.length) setFiles((p) => [...p, ...images]);
  };

  const onPaste = (e: React.ClipboardEvent) => {
    const pasted = Array.from(e.clipboardData.files).filter((f) => f.type.startsWith('image/'));
    if (pasted.length) {
      e.preventDefault();
      addFiles(pasted);
    }
  };

  // object URL memo + cleanup（防内存泄漏：每次 files 变化重建，旧的 revoke）
  const thumbs = useMemo(() => files.map((f) => URL.createObjectURL(f)), [files]);
  useEffect(() => () => thumbs.forEach((url) => URL.revokeObjectURL(url)), [thumbs]);

  const submit = async () => {
    setError('');
    setGenStatus('');
    if (files.length === 0) {
      setError(t('testcase.selectAtLeastOneScreenshot'));
      return;
    }
    if (!baseUrl.trim()) {
      setError(t('testcase.fillBaseUrl'));
      return;
    }

    setImageGenerating(true);
    try {
      const images = await Promise.all(files.map(fileToBase64));
      setGenStatus(t('testcase.submittingTask'));
      const { task_id } = await createQuickTask('image_generate', {
        images: images.map((img) => ({ data: img.data, mime: img.mime })),
        base_url: baseUrl.trim(),
        point_summary: pointSummary.trim(),
        project_id: currentProjectId,
        version_id: currentVersionId,
      });

      setGenStatus(t('testcase.visionAnalyzing'));
      await streamImageTask(task_id);
      setGenStatus(t('testcase.generateComplete'));
      onDone?.();
    } catch (e) {
      setError((e as Error).message);
      setGenStatus('');
    } finally {
      setImageGenerating(false);
    }
  };

  return (
    <div
      style={{ padding: 24, maxWidth: 720, overflow: 'auto' }}
      onPaste={onPaste}
      tabIndex={0}  // 让 div 可获焦点接收 paste 事件
      autoFocus     // 进入面板自动获焦，Ctrl+V 直接粘贴图片
    >
      <h2 style={{ fontSize: 16, color: "var(--text-primary)", marginBottom: 4, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        <Camera size={16} strokeWidth={1.5} /> {t('testcase.screenshotGenerateUi')}
      </h2>
      <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 20, whiteSpace: 'pre-line' }}>
        {t('testcase.imageUploadHint')}
      </p>

      {/* 截图选择 + 预览 */}
      <div style={{ marginBottom: 16 }}>
        <div style={labelStyle}>{t('testcase.uiScreenshotsLabel')}</div>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept="image/*"
          style={{ display: 'none' }}
          onChange={(e) => {
            addFiles(Array.from(e.target.files ?? []));
            if (fileRef.current) fileRef.current.value = '';
          }}
        />
        <button
          onClick={() => fileRef.current?.click()}
          style={{
            background: "var(--bg-card)", border: '1px dashed var(--border-strong)', color: "var(--text-secondary)",
            padding: '12px 20px', borderRadius: 6, cursor: 'pointer', fontSize: 13,
          }}
        >
          {t('testcase.selectScreenshots')}
        </button>

        {files.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
            {files.map((f, i) => (
              <div
                key={i}
                style={{
                  position: 'relative', width: 100, height: 80,
                  border: '1px solid var(--bg-elevated)', borderRadius: 4, overflow: 'hidden',
                }}
              >
                <img
                  src={thumbs[i]}
                  alt={f.name}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
                <button
                  onClick={() => setFiles((p) => p.filter((_, idx) => idx !== i))}
                  style={{
                    position: 'absolute', top: 2, right: 2,
                    background: 'rgba(0,0,0,0.7)', color: 'var(--error)',
                    border: 'none', borderRadius: '50%', width: 18, height: 18,
                    cursor: 'pointer', fontSize: 11, lineHeight: '18px', padding: 0,
                  }}
                >
                  ×
                </button>
                <div style={{
                  position: 'absolute', bottom: 0, left: 0, right: 0,
                  background: 'rgba(0,0,0,0.6)', color: "var(--text-secondary)",
                  fontSize: 9, padding: '1px 4px', textAlign: 'center',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {i + 1}. {f.name}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* base_url */}
      <div style={{ marginBottom: 16 }}>
        <div style={labelStyle}>{t('testcase.targetBaseUrlLabel')}</div>
        <input
          style={inputStyle}
          placeholder="https://example.com/app"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
        />
      </div>

      {/* point_summary */}
      <div style={{ marginBottom: 16 }}>
        <div style={labelStyle}>{t('testcase.testFocusLabel')}</div>
        <textarea
          style={{ ...inputStyle, minHeight: 60, resize: 'vertical' }}
          placeholder={t('testcase.testFocusPlaceholder')}
          value={pointSummary}
          onChange={(e) => setPointSummary(e.target.value)}
        />
      </div>

      {/* 错误提示 */}
      {error && (
        <div style={{ color: 'var(--error)', fontSize: 12, marginBottom: 12, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <AlertTriangle size={12} strokeWidth={1.5} /> {error}
        </div>
      )}

      {/* 提交 */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <button
          onClick={submit}
          disabled={imageGenerating || files.length === 0 || !baseUrl.trim()}
          style={{
            ...primaryBtn,
            opacity: imageGenerating || files.length === 0 || !baseUrl.trim() ? 0.4 : 1,
          }}
        >
          {imageGenerating ? t('testcase.generatingVision') : t('testcase.generateUiCase')}
        </button>
        {genStatus && (
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{genStatus}</span>
        )}
      </div>
    </div>
  );
}
