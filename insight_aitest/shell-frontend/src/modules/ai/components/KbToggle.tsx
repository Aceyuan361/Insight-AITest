import { useState, useEffect } from 'react';
import { MessageSquare, Zap, FileText, AlertCircle, Check, RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { text, RADIUS } from './agentStyles';
import { useProjectStore } from '../../../shared/store/projectStore';

export type KbMode = 'off' | 'auto' | 'manual';

interface DocInfo {
  id: number;
  filename: string;
  doc_type: string;
  status: string;
  char_count: number;
  created_at: string | null;
}

interface Props {
  mode: KbMode;
  onModeChange: (mode: KbMode) => void;
  selectedDocIds: number[];
  onDocIdsChange: (ids: number[]) => void;
}

const BASE = '/api/modules/ai/tasks';

export function KbToggle({ mode, onModeChange, selectedDocIds, onDocIdsChange }: Props) {
  const { t } = useTranslation();
  const { currentProjectId } = useProjectStore();
  const [docs, setDocs] = useState<DocInfo[]>([]);
  const [stats, setStats] = useState({ total_docs: 0, total_chunks: 0, vector_enabled: false });
  const [showPicker, setShowPicker] = useState(false);
  const [reindexing, setReindexing] = useState<Set<number>>(new Set());

  useEffect(() => {
    const params = currentProjectId != null ? `?project_id=${currentProjectId}` : '';
    fetch(`${BASE}/kb/stats${params}`)
      .then(r => r.ok ? r.json() : { total_docs: 0, total_chunks: 0, vector_enabled: false })
      .then(setStats).catch(() => setStats({ total_docs: 0, total_chunks: 0, vector_enabled: false }));
    fetch(`${BASE}/kb/documents${params}`)
      .then(r => r.ok ? r.json() : [])
      .then(data => setDocs(Array.isArray(data) ? data : []))
      .catch(() => setDocs([]));
  }, [currentProjectId]);

  const vectorReady = stats.vector_enabled;
  const iconSize = 13;

  const toggleDoc = (id: number) => {
    const next = selectedDocIds.includes(id)
      ? selectedDocIds.filter(x => x !== id)
      : [...selectedDocIds, id];
    onDocIdsChange(next);
  };

  const reindex = async (docId: number) => {
    setReindexing(prev => new Set([...prev, docId]));
    await fetch(`${BASE}/kb/reindex`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_ids: [docId] }),
    });
    setReindexing(prev => { const n = new Set(prev); n.delete(docId); return n; });
  };

  const docTypeLabel = (dt: string) => {
    if (dt.includes('prd') || dt.includes('需求')) return '📋 PRD';
    if (dt.includes('api') || dt.includes('接口')) return '🔌 接口文档';
    if (dt.includes('ui') || dt.includes('截图') || dt.includes('image')) return '🖼 UI截图';
    return '📄 其他';
  };

  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', gap: 4, position: 'relative' }}>
      {/* 三段式切换 */}
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        <div style={{
          display: 'inline-flex',
          border: '1px solid var(--border-strong)',
          borderRadius: RADIUS.sm,
          overflow: 'hidden',
        }}>
          {/* 关闭 */}
          <button
            onClick={() => onModeChange('off')}
            title={t('ai.kbPureLlmTitle')}
            style={btnStyle(mode === 'off', false)}
          ><MessageSquare size={iconSize} strokeWidth={1.5} /> {t('ai.pureLlm')}</button>
          {/* 自动 (向量) */}
          <button
            onClick={() => onModeChange('auto')}
            title={vectorReady ? t('ai.kbAutoTitle') : t('ai.kbAutoNeedConfig')}
            style={btnStyle(mode === 'auto', !vectorReady)}
          ><Zap size={iconSize} strokeWidth={1.5} /> {t('ai.kbAuto')}</button>
          {/* 手动 */}
          <button
            onClick={() => { onModeChange('manual'); setShowPicker(true); }}
            title={t('ai.kbManualTitle')}
            style={btnStyle(mode === 'manual', false)}
          ><FileText size={iconSize} strokeWidth={1.5} /> {t('ai.kbManual')}</button>
        </div>
        {!vectorReady && mode === 'auto' && (
          <AlertCircle size={iconSize} strokeWidth={1.5} style={{ color: 'var(--warning, var(--accent))' }} />
        )}
      </div>

      {/* 自动档：向量状态提示 */}
      {mode === 'auto' && (
        <div style={{ fontSize: 10, color: vectorReady ? text.accent : 'var(--warning)', paddingLeft: 4 }}>
          {vectorReady
            ? <>✅ {t('ai.kbVectorReady')} · {stats.total_docs} {t('ai.kbDocs')} / {stats.total_chunks} {t('ai.kbChunks')}</>
            : <>⚠️ {t('ai.kbVectorNotReady')}</>
          }
        </div>
      )}

      {/* 手动档：文档选择器 */}
      {mode === 'manual' && (
        <>
          <button
            onClick={() => setShowPicker(!showPicker)}
            style={{
              fontSize: 10, color: text.accent, background: 'none', border: 'none',
              cursor: 'pointer', textAlign: 'left', padding: '2px 4px',
            }}
          >
            {selectedDocIds.length > 0
              ? `📎 ${t('ai.kbSelected')} ${selectedDocIds.length} ${t('ai.kbDocs')}`
              : `📎 ${t('ai.kbSelectDocs')}`}
            {' '}{showPicker ? '▾' : '▸'}
          </button>
          {showPicker && (
            <div style={{
              border: '1px solid var(--border-strong)', borderRadius: 6,
              background: 'var(--bg-card)', padding: 6, maxHeight: 200, overflow: 'auto',
              fontSize: 10, minWidth: 260,
            }}>
              {docs.length === 0 && (
                <div style={{ color: text.muted, padding: 8, textAlign: 'center' }}>
                  {t('ai.kbNoDocs')}
                </div>
              )}
              {docs.map(d => (
                <div key={d.id} style={{
                  display: 'flex', alignItems: 'center', gap: 4, padding: '4px 6px',
                  borderRadius: 4, cursor: 'pointer',
                  background: selectedDocIds.includes(d.id) ? 'rgba(16,185,129,0.08)' : 'transparent',
                }} onClick={() => toggleDoc(d.id)}>
                  <span style={{
                    width: 14, height: 14, borderRadius: 3, flexShrink: 0,
                    border: `1px solid ${selectedDocIds.includes(d.id) ? 'var(--accent)' : 'var(--border-strong)'}`,
                    background: selectedDocIds.includes(d.id) ? 'var(--accent)' : 'transparent',
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    {selectedDocIds.includes(d.id) && <Check size={10} strokeWidth={2} color="#fff" />}
                  </span>
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {d.filename}
                  </span>
                  <span style={{ color: text.muted, whiteSpace: 'nowrap' }}>
                    {docTypeLabel(d.doc_type)}
                  </span>
                  {d.status !== 'ready' && d.status !== 'done' && (
                    <button
                      onClick={(e) => { e.stopPropagation(); reindex(d.id); }}
                      disabled={reindexing.has(d.id)}
                      title={t('ai.kbReindex')}
                      style={{
                        background: 'none', border: 'none', cursor: 'pointer', padding: 2,
                        color: text.muted, opacity: reindexing.has(d.id) ? 0.5 : 1,
                      }}
                    >
                      <RefreshCw size={10} strokeWidth={1.5} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function btnStyle(active: boolean, warning: boolean): React.CSSProperties {
  return {
    padding: '4px 8px',
    fontSize: 11,
    cursor: 'pointer',
    border: 'none',
    borderRight: '1px solid var(--bg-elevated)',
    background: active
      ? (warning ? 'rgba(250,173,20,0.14)' : 'rgba(16,185,129,0.14)')
      : 'transparent',
    color: active
      ? (warning ? 'var(--warning)' : 'var(--accent)')
      : 'var(--text-muted)',
    fontWeight: active ? 600 : 400,
    transition: 'all 0.15s cubic-bezier(0.16,1,0.3,1)',
    fontFamily: 'inherit',
    display: 'inline-flex',
    alignItems: 'center',
    gap: 3,
  };
}
