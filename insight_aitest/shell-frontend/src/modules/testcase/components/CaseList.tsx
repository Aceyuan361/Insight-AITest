import { Search, Camera } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useCaseStore, type TestCase } from '../store/caseStore';
import { useConfirmStore } from '../../../shared/store/confirmStore';
import { useIsMobile } from '../../../shared/hooks/useIsMobile';

const STATUS_COLOR: Record<string, string> = {
  draft: "var(--warning)", reviewed: "var(--info)", ready: "var(--success)", deprecated: "var(--text-muted)",
};
const PRIORITY_COLOR: Record<string, string> = {
  p0: "var(--error)", p1: "var(--warning)", p2: "var(--text-muted)", p3: 'var(--border-strong)',
};

export function CaseList({ isMobile, onNew, onAnalyze, onFromImage }: {
  isMobile?: boolean; onNew: () => void; onAnalyze: () => void; onFromImage: () => void;
}) {
  const isMobileLayout = isMobile ?? useIsMobile();
  const { t } = useTranslation();
  const { cases, activeId, selectCase, deleteCase, loadCases } = useCaseStore();
  const { confirm } = useConfirmStore();

  const STATUS_LABEL: Record<string, string> = {
    draft: t('testcase.statusPending'), reviewed: t('testcase.statusReviewed'), ready: t('testcase.statusReady'), deprecated: t('testcase.statusDeprecated'),
  };

  return (
    <div style={{ width: isMobileLayout ? '100%' : 260, borderRight: '1px solid var(--bg-card)', display: 'flex',
      flexDirection: 'column', background: "var(--bg-base)", ...(isMobileLayout ? { maxHeight: 300, overflowY: 'auto' } : {}) }}>
      <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <button onClick={onNew} style={btnStyle("var(--bg-card)", "var(--accent)")}>+ {t('testcase.newCase')}</button>
        <button onClick={onAnalyze} style={{ ...btnStyle("var(--bg-card)", 'var(--chart-2)'), display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <Search size={13} strokeWidth={1.5} /> {t('testcase.aiAnalyzeGenerate')}
        </button>
        <button onClick={onFromImage} style={{ ...btnStyle("var(--bg-card)", 'var(--chart-4)'), display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <Camera size={13} strokeWidth={1.5} /> {t('testcase.generateFromScreenshot')}
        </button>
      </div>
      <div style={{ padding: '0 12px 8px', display: 'flex', gap: 6 }}>
        <select onChange={(e) => loadCases(e.target.value || undefined)}
          style={{ flex: 1, ...selectStyle }}>
          <option value="">{t('testcase.allTypes')}</option>
          <option value="functional">{t('testcase.typeFunctional')}</option>
          <option value="api">{t('testcase.typeApi')}</option>
          <option value="performance">{t('testcase.typePerformance')}</option>
          <option value="ui">{t('testcase.typeUi')}</option>
        </select>
      </div>
      <div style={{ flex: 1, overflow: 'auto' }}>
        {cases.length === 0 && (
          <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: 12 }}>{t('testcase.noCases')}</div>
        )}
        {cases.map((c) => (
          <CaseRow key={c.id} c={c} active={activeId === c.id}
            statusLabel={STATUS_LABEL[c.status] || c.status}
            onClick={() => selectCase(c.id)}
            onDelete={() => confirm({
              title: t('testcase.confirmDelete'),
              message: t('testcase.confirmDeleteMessage', { title: c.title }),
              variant: 'danger',
              onConfirm: () => deleteCase(c.id),
            })} />
        ))}
      </div>
    </div>
  );
}

function CaseRow({ c, active, statusLabel, onClick, onDelete }: {
  c: TestCase; active: boolean; statusLabel: string; onClick: () => void; onDelete: () => void;
}) {
  return (
    <div onClick={onClick} style={{
      padding: '8px 12px', cursor: 'pointer',
      background: active ? 'rgba(91,140,123,0.08)' : 'transparent',
      borderLeft: active ? '2px solid var(--accent)' : '2px solid transparent',
      display: 'flex', alignItems: 'center', gap: 6,
      color: active ? "var(--accent)" : 'var(--text-secondary)', fontSize: 13,
    }}>
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
        {c.title}
      </span>
      <span style={{ fontSize: 10, color: PRIORITY_COLOR[c.priority] || "var(--text-muted)", fontWeight: 600 }}>
        {c.priority.toUpperCase()}
      </span>
      <span style={{
        fontSize: 10, color: STATUS_COLOR[c.status] || "var(--text-muted)",
        border: `1px solid ${STATUS_COLOR[c.status] || "var(--text-muted)"}`,
        padding: '0 4px', borderRadius: 3,
      }}>
        {statusLabel}
      </span>
      <button onClick={(e) => { e.stopPropagation(); onDelete(); }}
        style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>×</button>
    </div>
  );
}

function btnStyle(bg: string, color: string): React.CSSProperties {
  return { width: '100%', background: bg, border: `1px solid var(--bg-elevated)`,
    color, padding: '8px', borderRadius: 6, cursor: 'pointer' };
}
const selectStyle: React.CSSProperties = {
  background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)",
  padding: '4px', borderRadius: 4, fontSize: 12,
};
