import { useEffect, useState } from 'react';
import { Paperclip, FolderInput } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useCaseStore, type TestCase } from '../store/caseStore';
import { FunctionalStepsEditor, type FunctionalContent } from './FunctionalStepsEditor';
import { ApiStepsEditor, type ApiContent } from './ApiStepsEditor';
import { ContentRenderer } from './ContentRenderer';
import { useConfirmStore } from '../../../shared/store/confirmStore';
import { useProjectStore } from '../../../shared/store/projectStore';
import { toast } from 'sonner';

const inputStyle: React.CSSProperties = {
  background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', borderRadius: 4,
  color: "var(--text-primary)", padding: '6px 8px', fontFamily: 'inherit', fontSize: 13,
};
const labelStyle: React.CSSProperties = { fontSize: 12, color: "var(--text-secondary)", width: 90, flexShrink: 0, paddingTop: 6 };

export function CaseEditor() {
  const { t } = useTranslation();
  const { cases, activeId, updateCase, updateStatus, deleteCase, assignCase } = useCaseStore();
  const { confirm } = useConfirmStore();
  const { projects, versions, loadProjects, loadVersions } = useProjectStore();
  const c = cases.find((x) => x.id === activeId);
  const [form, setForm] = useState<TestCase | null>(null);

  useEffect(() => { loadProjects(); }, [loadProjects]);

  useEffect(() => { setForm(c ?? null); }, [c?.id]);

  if (!form) {
    return <div style={{ padding: 40, color: 'var(--text-muted)' }}>{t('testcase.selectOrCreateHint')}</div>;
  }

  const set = <K extends keyof TestCase>(k: K, v: TestCase[K]) =>
    setForm((f) => (f ? { ...f, [k]: v } : f));
  const save = () => {
    if (!form) return;
    updateCase(form.id, {
      title: form.title, description: form.description, priority: form.priority,
      test_design: form.test_design, preconditions: form.preconditions,
      content: form.content, tags: form.tags,
    });
  };

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: 24, color: "var(--text-primary)" }}>
      {/* 元信息区 */}
      <div style={{ marginBottom: 16 }}>
        <Row label={t('testcase.caseTitle')}>
          <input style={{ ...inputStyle, width: '100%' }} value={form.title}
            onChange={(e) => set('title', e.target.value)} />
        </Row>
        <div style={{ display: 'flex', gap: 12 }}>
          <Row label={t('testcase.status')}>
            <select style={inputStyle} value={form.type} disabled
              onChange={(e) => set('type', e.target.value)}>
              <option value="functional">{t('testcase.typeFunctional')}</option>
              <option value="api">{t('testcase.typeApi')}</option>
              <option value="performance">{t('testcase.typePerformance')}</option>
              <option value="ui">{t('testcase.typeUi')}</option>
            </select>
          </Row>
          <Row label={t('testcase.priority')}>
            <select style={inputStyle} value={form.priority}
              onChange={(e) => set('priority', e.target.value)}>
              <option value="p0">P0</option><option value="p1">P1</option>
              <option value="p2">P2</option><option value="p3">P3</option>
            </select>
          </Row>
          <Row label={t('testcase.design')}>
            <select style={inputStyle} value={form.test_design}
              onChange={(e) => set('test_design', e.target.value)}>
              <option value="positive">{t('testcase.designPositive')}</option><option value="negative">{t('testcase.designNegative')}</option>
              <option value="boundary">{t('testcase.designBoundary')}</option><option value="edge">{t('testcase.designEdge')}</option>
            </select>
          </Row>
          <Row label={t('testcase.status')}>
            <select style={inputStyle} value={form.status}
              onChange={(e) => updateStatus(form.id, e.target.value)}>
              <option value="draft">{t('testcase.statusPending')}</option><option value="reviewed">{t('testcase.statusReviewed')}</option>
              <option value="ready">{t('testcase.statusReady')}</option><option value="deprecated">{t('testcase.statusDeprecated')}</option>
            </select>
          </Row>
        </div>
        <Row label={t('testcase.preconditions')}>
          <input style={{ ...inputStyle, width: '100%' }} value={form.preconditions}
            onChange={(e) => set('preconditions', e.target.value)} />
        </Row>
      </div>

      {/* 归属迁移区 */}
      <AssignmentSection
        form={form}
        projects={projects}
        versions={versions}
        onLoadVersions={loadVersions}
        onAssign={async (pid, vid) => {
          const updated = await assignCase(form.id, pid, vid);
          setForm(updated);
          toast.success(t('testcase.assignMoved'));
        }}
      />

      {/* 内容编辑区（按类型） */}
      {form.type === 'functional' ? (
        <FunctionalStepsEditor
          content={form.content as unknown as FunctionalContent}
          onChange={(content) => set('content', content as unknown as Record<string, unknown>)} />
      ) : form.type === 'api' ? (
        <ApiStepsEditor
          content={(form.content as unknown as ApiContent) ?? { base_url: '', steps: [] }}
          onChange={(content) => set('content', content as unknown as Record<string, unknown>)} />
      ) : (
        <ContentRenderer type={form.type} content={form.content} />
      )}

      {/* 底部操作 */}
      <div style={{ marginTop: 24, display: 'flex', alignItems: 'center', gap: 12,
        borderTop: '1px solid var(--bg-card)', paddingTop: 16 }}>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <Paperclip size={12} strokeWidth={1.5} /> {t('testcase.sourceLabel', { source: form.source })}
          {form.last_result && t('testcase.lastResultLabel', { result: form.last_result })}
        </span>
        <div style={{ flex: 1 }} />
        <button onClick={() => exportCase(form)} style={secondaryBtn}>{t('testcase.exportJson')}</button>
        <button onClick={save} style={primaryBtn}>{t('testcase.save')}</button>
        {form.status === 'draft' && (
          <button onClick={() => updateStatus(form.id, 'reviewed')} style={secondaryBtn}>
            {t('testcase.markReviewed')}
          </button>
        )}
        <button onClick={() => confirm({
          title: t('testcase.confirmDelete'),
          message: t('testcase.confirmDeleteMessage', { title: form.title }),
          variant: 'danger',
          onConfirm: () => deleteCase(form.id),
        })} style={{ ...secondaryBtn, color: "var(--error)" }}>
          {t('testcase.delete')}
        </button>
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', marginBottom: 8 }}>
      <span style={labelStyle}>{label}</span>
      <div style={{ flex: 1 }}>{children}</div>
    </div>
  );
}

/** 归属迁移：展示当前项目/版本，提供目标项目+版本下拉与保存。 */
function AssignmentSection({ form, projects, versions, onLoadVersions, onAssign }: {
  form: TestCase;
  projects: { id: number; name: string }[];
  versions: { id: number; name: string; project_id: number }[];
  onLoadVersions: (projectId: number) => void;
  onAssign: (projectId: number | undefined, versionId: number | undefined) => Promise<void>;
}) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [selProject, setSelProject] = useState<number | ''>(form.project_id ?? '');
  const [selVersion, setSelVersion] = useState<number | ''>(form.version_id ?? '');
  const [saving, setSaving] = useState(false);

  // 当前项目/版本名称（从列表反查；找不到则显示 id）
  const curProject = projects.find((p) => p.id === form.project_id);
  const curVersion = versions.find((v) => v.id === form.version_id);

  const startEdit = () => {
    setSelProject(form.project_id ?? '');
    setSelVersion(form.version_id ?? '');
    // 已有项目则预载版本列表
    if (form.project_id != null) onLoadVersions(form.project_id);
    setEditing(true);
  };

  const changeProject = (pid: number | '') => {
    setSelProject(pid);
    setSelVersion('');
    if (pid !== '') onLoadVersions(pid);
  };

  const doSave = async () => {
    setSaving(true);
    try {
      await onAssign(selProject === '' ? undefined : selProject, selVersion === '' ? undefined : selVersion);
      setEditing(false);
    } catch (e) {
      toast.error(t('testcase.moveFailed', { message: (e as Error).message }));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      marginBottom: 16, padding: 12, borderRadius: 6,
      background: 'var(--bg-base)', border: '1px solid var(--bg-card)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: editing ? 10 : 0 }}>
        <FolderInput size={13} strokeWidth={1.5} style={{ color: 'var(--accent)' }} />
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{t('testcase.assignmentLabel')}</span>
        <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>
          {curProject?.name ?? (form.project_id != null ? `#${form.project_id}` : t('testcase.unassigned'))}
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>/</span>
        <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>
          {curVersion?.name ?? (form.version_id != null ? `#${form.version_id}` : t('testcase.allVersions'))}
        </span>
        <div style={{ flex: 1 }} />
        {!editing && (
          <button onClick={startEdit} style={{ ...miniBtn, border: '1px solid var(--bg-elevated)' }}>{t('testcase.moveAssignment')}</button>
        )}
      </div>

      {editing && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <select style={assignSelectStyle} value={selProject} onChange={(e) => changeProject(e.target.value ? Number(e.target.value) : '')}>
            <option value="">{t('testcase.selectProject')}</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <select style={assignSelectStyle} value={selVersion} onChange={(e) => setSelVersion(e.target.value ? Number(e.target.value) : '')}>
            <option value="">{t('testcase.allVersions')}</option>
            {versions.filter((v) => selProject === '' || v.project_id === selProject)
              .map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
          </select>
          <button onClick={doSave} disabled={saving}
            style={{ ...primaryBtn, padding: '4px 12px', fontSize: 12, opacity: saving ? 0.5 : 1 }}>
            {saving ? t('testcase.movingAssignment') : t('testcase.save')}
          </button>
          <button onClick={() => setEditing(false)} style={{ ...miniBtn, border: '1px solid var(--bg-elevated)' }}>{t('common.cancel')}</button>
        </div>
      )}
    </div>
  );
}

async function exportCase(c: TestCase) {
  const r = await fetch(`/api/modules/testcase/testcases/${c.id}/export`);
  if (!r.ok) return;
  const blob = new Blob([JSON.stringify(await r.json(), null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${c.title || 'testcase'}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

const primaryBtn: React.CSSProperties = {
  background: "var(--accent)", color: "var(--bg-base)", border: 'none', borderRadius: 6,
  padding: '8px 20px', cursor: 'pointer', fontWeight: 600,
};
const secondaryBtn: React.CSSProperties = {
  background: 'none', border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)",
  borderRadius: 6, padding: '8px 16px', cursor: 'pointer',
};
const miniBtn: React.CSSProperties = {
  background: 'none', border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)",
  padding: '2px 10px', borderRadius: 4, cursor: 'pointer', fontSize: 12,
};
const assignSelectStyle: React.CSSProperties = {
  background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', borderRadius: 4,
  color: "var(--text-primary)", padding: '4px 8px', fontFamily: 'inherit', fontSize: 13, minWidth: 140,
};
