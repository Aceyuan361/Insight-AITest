import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { ReviewCase } from '../../ai/store/taskStore';

/** 用例 API 基址（与 ai/store/taskStore 的 CASE_BASE 保持一致）。 */
const CASE_BASE = '/api/modules/testcase/testcases';

const inputStyle: React.CSSProperties = {
  background: 'var(--bg-card)',
  border: '1px solid var(--bg-elevated)',
  borderRadius: 6,
  color: 'var(--text-primary)',
  padding: '6px 8px',
  fontFamily: 'inherit',
  fontSize: 13,
  width: '100%',
};

const labelStyle: React.CSSProperties = {
  fontSize: 12,
  color: 'var(--text-secondary)',
  width: 70,
  flexShrink: 0,
  paddingTop: 6,
};

/**
 * 简化版行内用例编辑器（用于用例审阅面板 ReviewRow 展开后编辑）。
 * 非完整移植 CaseEditor —— 仅含审阅阶段可编辑的核心字段：标题、描述、优先级、
 * 测试设计、content(JSON 文本)。保存走 PUT /testcases/{id}，成功后回调 onSaved。
 */
export function CaseEditorInline({
  caseData,
  onSaved,
  onClose,
}: {
  caseData: ReviewCase;
  onSaved: () => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<ReviewCase>(caseData);
  const [contentText, setContentText] = useState<string>(() => {
    try {
      return JSON.stringify(caseData.content ?? {}, null, 2);
    } catch {
      return '{}';
    }
  });
  const [showContent, setShowContent] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = <K extends keyof ReviewCase>(k: K, v: ReviewCase[K]) =>
    setDraft((d) => ({ ...d, [k]: v }));

  const save = async () => {
    setSaving(true);
    setError(null);
    let parsedContent: Record<string, unknown>;
    try {
      parsedContent = JSON.parse(contentText || '{}');
    } catch {
      setError(t('testcase.invalidJson'));
      setSaving(false);
      return;
    }
    try {
      const res = await fetch(`${CASE_BASE}/${caseData.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: draft.title,
          description: draft.description,
          priority: draft.priority,
          test_design: draft.test_design,
          content: parsedContent,
        }),
      });
      if (!res.ok) {
        const msg = await res.text().catch(() => `HTTP ${res.status}`);
        setError(t('testcase.saveFailed', { message: msg }));
        setSaving(false);
        return;
      }
      onSaved();
    } catch (e) {
      setError(t('testcase.networkError', { message: (e as Error).message }));
      setSaving(false);
    }
  };

  return (
    <div style={{ padding: '12px 16px', background: 'var(--bg-elevated)', borderTop: '1px solid var(--bg-elevated)' }}>
      <Row label={t('testcase.caseTitle')}>
        <input style={inputStyle} value={draft.title} onChange={(e) => set('title', e.target.value)} />
      </Row>
      <Row label={t('testcase.description')}>
        <textarea
          style={{ ...inputStyle, minHeight: 48, resize: 'vertical' }}
          value={draft.description ?? ''}
          onChange={(e) => set('description', e.target.value)}
        />
      </Row>
      <div style={{ display: 'flex', gap: 12 }}>
        <Row label={t('testcase.priority')}>
          <select style={inputStyle} value={draft.priority} onChange={(e) => set('priority', e.target.value)}>
            <option value="p0">P0</option>
            <option value="p1">P1</option>
            <option value="p2">P2</option>
            <option value="p3">P3</option>
          </select>
        </Row>
        <Row label={t('testcase.testDesign')}>
          <select style={inputStyle} value={draft.test_design} onChange={(e) => set('test_design', e.target.value)}>
            <option value="positive">{t('testcase.designPositive')}</option>
            <option value="negative">{t('testcase.designNegative')}</option>
            <option value="boundary">{t('testcase.designBoundary')}</option>
            <option value="edge">{t('testcase.designEdge')}</option>
          </select>
        </Row>
      </div>

      <div style={{ marginBottom: 8 }}>
        <button
          onClick={() => setShowContent((v) => !v)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-secondary)',
            fontSize: 12,
            cursor: 'pointer',
            padding: 0,
          }}
        >
          {showContent ? t('testcase.hideContentJson') : t('testcase.showContentJson')}
        </button>
      </div>
      {showContent && (
        <textarea
          style={{
            ...inputStyle,
            fontFamily: 'ui-monospace, monospace',
            fontSize: 12,
            minHeight: 120,
            resize: 'vertical',
          }}
          value={contentText}
          onChange={(e) => setContentText(e.target.value)}
        />
      )}

      {error && (
        <div style={{ fontSize: 12, color: 'var(--error)', marginTop: 8 }}>{error}</div>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 12 }}>
        <button
          onClick={onClose}
          disabled={saving}
          style={{
            background: 'none',
            border: '1px solid var(--bg-elevated)',
            color: 'var(--text-secondary)',
            borderRadius: 6,
            padding: '6px 16px',
            cursor: 'pointer',
            fontSize: 13,
          }}
        >
          {t('common.cancel')}
        </button>
        <button
          onClick={save}
          disabled={saving}
          style={{
            background: 'var(--accent)',
            color: 'var(--bg-base)',
            border: 'none',
            borderRadius: 6,
            padding: '6px 16px',
            cursor: 'pointer',
            fontSize: 13,
            fontWeight: 600,
            opacity: saving ? 0.6 : 1,
          }}
        >
          {saving ? t('testcase.saving') : t('testcase.save')}
        </button>
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', marginBottom: 8 }}>
      <span style={labelStyle}>{label}</span>
      <div style={{ flex: 1, minWidth: 0 }}>{children}</div>
    </div>
  );
}
