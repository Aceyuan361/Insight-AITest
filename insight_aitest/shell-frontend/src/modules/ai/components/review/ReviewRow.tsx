import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { ReviewCase } from '../../store/taskStore';
import { CaseEditorInline } from '../../../testcase/components/CaseEditorInline';
import { text } from '../agentStyles';

/** 单条用例审阅行：勾选框 + 标题/类型/优先级/设计/状态 + 编辑入口。
 *  编辑时下方展开 CaseEditorInline（跨整行 colSpan）。 */
export function ReviewRow({
  caseData,
  selected,
  onToggle,
  onSaved,
  colSpan,
}: {
  caseData: ReviewCase;
  selected: boolean;
  onToggle: () => void;
  onSaved: () => void;
  colSpan: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const { t } = useTranslation();

  const cellBase: React.CSSProperties = {
    padding: '8px 10px',
    fontSize: 12,
    color: text.secondary,
    borderBottom: '1px solid var(--hairline-soft)',
  };

  return (
    <>
      <tr style={{ background: selected ? 'rgba(16,185,129,0.04)' : 'transparent' }}>
        <td style={{ ...cellBase, width: 32, textAlign: 'center' }}>
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggle}
            style={{ accentColor: 'var(--accent)', cursor: 'pointer' }}
          />
        </td>
        <td style={{ ...cellBase, color: text.primary, fontWeight: 500 }}>{caseData.title}</td>
        <td style={{ ...cellBase, width: 64 }}>{caseData.type}</td>
        <td style={{ ...cellBase, width: 56 }}>{caseData.priority?.toUpperCase()}</td>
        <td style={{ ...cellBase, width: 64 }}>{caseData.test_design}</td>
        <td style={{ ...cellBase, width: 64 }}>
          <StatusBadge status={caseData.status} />
        </td>
        <td style={{ ...cellBase, width: 56, textAlign: 'right' }}>
          <button
            onClick={() => setExpanded((v) => !v)}
            style={{
              background: 'none',
              border: '1px solid var(--border)',
              color: text.secondary,
              borderRadius: 4,
              padding: '2px 8px',
              cursor: 'pointer',
              fontSize: 11,
            }}
          >
            {expanded ? t('ai.rowCollapse') : t('ai.rowEdit')}
          </button>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={colSpan} style={{ padding: 0, borderBottom: '1px solid var(--hairline-soft)' }}>
            <CaseEditorInline
              caseData={caseData}
              onSaved={() => {
                setExpanded(false);
                onSaved();
              }}
              onClose={() => setExpanded(false)}
            />
          </td>
        </tr>
      )}
    </>
  );
}

function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const map: Record<string, { labelKey: string; color: string }> = {
    draft: { labelKey: 'ai.statusDraft', color: text.muted },
    reviewed: { labelKey: 'ai.statusReviewed', color: text.accent },
    ready: { labelKey: 'ai.statusReady', color: text.success },
    deprecated: { labelKey: 'ai.statusDeprecated', color: text.danger },
  };
  const m = map[status] ?? { color: text.muted };
  const label = map[status] ? t(map[status].labelKey) : (status || '—');
  return (
    <span
      style={{
        fontSize: 11,
        color: m.color,
        border: `1px solid color-mix(in srgb, ${m.color} 30%, transparent)`,
        background: `color-mix(in srgb, ${m.color} 8%, transparent)`,
        borderRadius: 4,
        padding: '1px 6px',
      }}
    >
      {label}
    </span>
  );
}
