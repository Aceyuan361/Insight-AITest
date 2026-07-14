import { useTranslation } from 'react-i18next';
import type { ReviewCase } from '../../store/taskStore';
import { ReviewRow } from './ReviewRow';
import { text } from '../agentStyles';

/** 用例审阅表格：表头含全选勾选框，表体逐条渲染 ReviewRow。 */
export function ReviewTable({
  cases,
  selectedIds,
  onToggle,
  onToggleAll,
  onSaved,
}: {
  cases: ReviewCase[];
  selectedIds: Set<number>;
  onToggle: (caseId: number) => void;
  onToggleAll: () => void;
  onSaved: () => void;
}) {
  const allSelected = cases.length > 0 && selectedIds.size === cases.length;
  // 列数：勾选 + 标题 + 类型 + 优先级 + 设计 + 状态 + 操作 = 7
  const COL_SPAN = 7;
  const { t } = useTranslation();

  const thStyle: React.CSSProperties = {
    padding: '8px 10px',
    fontSize: 11,
    fontWeight: 600,
    color: text.muted,
    textAlign: 'left',
    borderBottom: '1px solid var(--border)',
    letterSpacing: '0.03em',
    whiteSpace: 'nowrap',
  };

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'auto' }}>
        <thead>
          <tr>
            <th style={{ ...thStyle, width: 32, textAlign: 'center' }}>
              <input
                type="checkbox"
                checked={allSelected}
                onChange={onToggleAll}
                style={{ accentColor: 'var(--accent)', cursor: 'pointer' }}
              />
            </th>
            <th style={thStyle}>{t('ai.colTitle')}</th>
            <th style={{ ...thStyle, width: 64 }}>{t('ai.colType')}</th>
            <th style={{ ...thStyle, width: 56 }}>{t('ai.colPriority')}</th>
            <th style={{ ...thStyle, width: 64 }}>{t('ai.colDesign')}</th>
            <th style={{ ...thStyle, width: 64 }}>{t('ai.colStatus')}</th>
            <th style={{ ...thStyle, width: 56, textAlign: 'right' }}>{t('ai.colActions')}</th>
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <ReviewRow
              key={c.id}
              caseData={c}
              selected={selectedIds.has(c.id)}
              onToggle={() => onToggle(c.id)}
              onSaved={onSaved}
              colSpan={COL_SPAN}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
