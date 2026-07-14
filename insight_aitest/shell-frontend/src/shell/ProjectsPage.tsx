import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ChevronDown, ChevronRight, Circle, CircleDot, X } from 'lucide-react';
import { useConfirmStore } from '../shared/store/confirmStore';

interface Project {
  id: number;
  name: string;
  description: string;
  color: string;
  version_count: number;
  created_at: string;
}

interface Version {
  id: number;
  project_id: number;
  name: string;
  description: string;
  is_active: boolean;
  created_at: string;
}

const BASE = '/api/platform';

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [editing, setEditing] = useState<{ id: number | null; name: string; description: string; color: string } | null>(null);
  const [editingVer, setEditingVer] = useState<{ projectId: number; id: number | null; name: string; description: string } | null>(null);
  const { confirm } = useConfirmStore();

  const loadProjects = async () => {
    const r = await fetch(`${BASE}/projects`);
    setProjects(await r.json());
  };

  useEffect(() => { loadProjects(); }, []);

  const loadVersions = async (projectId: number) => {
    const r = await fetch(`${BASE}/projects/${projectId}/versions`);
    setVersions(await r.json());
  };

  const saveProject = async () => {
    if (!editing) return;
    const body = { name: editing.name, description: editing.description, color: editing.color };
    if (editing.id) {
      await fetch(`${BASE}/projects/${editing.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    } else {
      await fetch(`${BASE}/projects`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    }
    setEditing(null);
    await loadProjects();
  };

  const deleteProject = (p: Project) => {
    confirm({
      title: '确认删除',
      message: `确定要删除项目「${p.name}」吗？\n\n项目下的版本将被一并删除。\n如果项目下有文档或用例，删除将被阻止。`,
      variant: 'danger',
      onConfirm: async () => {
        const r = await fetch(`${BASE}/projects/${p.id}`, { method: 'DELETE' });
        if (r.ok) {
          await loadProjects();
          setExpandedId(null);
        } else {
          const err = await r.json();
          toast.error(err.detail || '删除失败');
        }
      },
    });
  };

  const saveVersion = async () => {
    if (!editingVer) return;
    const body = { name: editingVer.name, description: editingVer.description };
    if (editingVer.id) {
      await fetch(`${BASE}/versions/${editingVer.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    } else {
      await fetch(`${BASE}/projects/${editingVer.projectId}/versions`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    }
    setEditingVer(null);
    if (expandedId) await loadVersions(expandedId);
    await loadProjects();
  };

  const deleteVersion = (v: Version) => {
    confirm({
      title: '确认删除',
      message: `确定要删除版本「${v.name}」吗？`,
      variant: 'danger',
      onConfirm: async () => {
        const r = await fetch(`${BASE}/versions/${v.id}`, { method: 'DELETE' });
        if (r.ok) {
          if (expandedId) await loadVersions(expandedId);
          await loadProjects();
        }
      },
    });
  };

  const toggleExpand = (projectId: number) => {
    if (expandedId === projectId) {
      setExpandedId(null);
    } else {
      setExpandedId(projectId);
      loadVersions(projectId);
    }
  };

  return (
    <div style={{ padding: 24, color: "var(--text-primary)", maxWidth: 800, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, margin: 0 }}>项目管理</h2>
        <button onClick={() => setEditing({ id: null, name: '', description: '', color: "var(--accent)" })} style={primaryBtn}>+ 新建项目</button>
      </div>

      {projects.length === 0 && (
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
          还没有项目。创建一个开始分类管理你的测试资产。
        </div>
      )}

      {projects.map((p) => (
        <div key={p.id} style={{ marginBottom: 12, border: '1px solid var(--bg-card)', borderRadius: 8, background: "var(--bg-base)", overflow: 'hidden' }}>
          <div
            style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer' }}
            onClick={() => toggleExpand(p.id)}
          >
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: p.color, flexShrink: 0 }} />
            <span style={{ flex: 1, fontWeight: 600, fontSize: 14 }}>{p.name}</span>
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{p.version_count} 个版本</span>
            <button onClick={(e) => { e.stopPropagation(); setEditing({ id: p.id, name: p.name, description: p.description, color: p.color }); }} style={miniBtn}>编辑</button>
            <button onClick={(e) => { e.stopPropagation(); deleteProject(p); }} style={{ ...miniBtn, color: "var(--error)" }}>删除</button>
            <span style={{ color: "var(--text-muted)", display: 'inline-flex', alignItems: 'center' }}>
              {expandedId === p.id ? <ChevronDown size={12} strokeWidth={1.5} /> : <ChevronRight size={12} strokeWidth={1.5} />}
            </span>
          </div>
          {p.description && expandedId !== p.id && (
            <div style={{ padding: '0 36px 8px', fontSize: 12, color: "var(--text-muted)" }}>{p.description}</div>
          )}
          {expandedId === p.id && (
            <div style={{ padding: '8px 16px 12px 36px', borderTop: '1px solid var(--bg-card)' }}>
              {versions.map((v) => (
                <div key={v.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0' }}>
                  <span style={{ fontSize: 12, color: v.is_active ? 'var(--chart-4)' : "var(--text-muted)", display: 'inline-flex', alignItems: 'center' }}>
                    {v.is_active ? <CircleDot size={12} strokeWidth={1.5} /> : <Circle size={12} strokeWidth={1.5} />}
                  </span>
                  <span style={{ fontSize: 13, flex: 1 }}>{v.name}</span>
                  {v.description && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{v.description}</span>}
                  <button onClick={() => setEditingVer({ projectId: p.id, id: v.id, name: v.name, description: v.description })} style={miniBtn}>编辑</button>
                  <button onClick={() => deleteVersion(v)} style={{ ...miniBtn, color: "var(--error)" }}>删除</button>
                </div>
              ))}
              <button onClick={() => setEditingVer({ projectId: p.id, id: null, name: '', description: '' })} style={{ ...miniBtn, marginTop: 4 }}>+ 新建版本</button>
            </div>
          )}
        </div>
      ))}

      {/* 项目编辑弹窗 */}
      {editing && (
        <Modal title={editing.id ? '编辑项目' : '新建项目'} onClose={() => setEditing(null)}>
          <Field label="名称">
            <input style={inputStyle} value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} />
          </Field>
          <Field label="描述">
            <input style={inputStyle} value={editing.description} onChange={(e) => setEditing({ ...editing, description: e.target.value })} />
          </Field>
          <Field label="标识色">
            <input type="color" value={editing.color} onChange={(e) => setEditing({ ...editing, color: e.target.value })} style={{ width: 40, height: 28, border: 'none', background: 'none' }} />
          </Field>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
            <button onClick={() => setEditing(null)} style={secondaryBtn}>取消</button>
            <button onClick={saveProject} style={primaryBtn}>保存</button>
          </div>
        </Modal>
      )}

      {/* 版本编辑弹窗 */}
      {editingVer && (
        <Modal title={editingVer.id ? '编辑版本' : '新建版本'} onClose={() => setEditingVer(null)}>
          <Field label="版本名">
            <input style={inputStyle} value={editingVer.name} onChange={(e) => setEditingVer({ ...editingVer, name: e.target.value })} placeholder="如 v2.0" />
          </Field>
          <Field label="描述">
            <input style={inputStyle} value={editingVer.description} onChange={(e) => setEditingVer({ ...editingVer, description: e.target.value })} />
          </Field>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
            <button onClick={() => setEditingVer(null)} style={secondaryBtn}>取消</button>
            <button onClick={saveVersion} style={primaryBtn}>保存</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 1000, display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: 60 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ width: 'min(480px, 90vw)', background: "var(--bg-base)", border: '1px solid var(--bg-elevated)', borderRadius: 10, padding: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <strong style={{ fontSize: 14 }}>{title}</strong>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: "var(--text-secondary)", cursor: 'pointer', display: 'inline-flex', alignItems: 'center', padding: 0 }}>
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>{children}</div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 11, color: "var(--text-secondary)", marginBottom: 4 }}>{label}</label>
      {children}
    </div>
  );
}

const inputStyle: React.CSSProperties = { width: '100%', background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', borderRadius: 4, color: "var(--text-primary)", padding: '6px 8px', fontSize: 13 };
const primaryBtn: React.CSSProperties = { background: "var(--accent)", color: "var(--bg-base)", border: 'none', borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: 12, fontWeight: 600 };
const secondaryBtn: React.CSSProperties = { background: 'none', border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)", borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: 12 };
const miniBtn: React.CSSProperties = { background: 'none', border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)", borderRadius: 3, padding: '2px 8px', cursor: 'pointer', fontSize: 11 };
