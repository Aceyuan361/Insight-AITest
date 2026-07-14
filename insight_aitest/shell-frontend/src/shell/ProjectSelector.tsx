import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useProjectStore } from '../shared/store/projectStore';

/**
 * 全局 Project/Version 切换器，嵌入 TopBar。
 * 切换后各模块 store 通过 useProjectStore.getState() 感知并自动筛选。
 */
export function ProjectSelector() {
  const { projects, versions, currentProjectId, currentVersionId, loadProjects, setProject, setVersion } = useProjectStore();
  const { i18n } = useTranslation();

  useEffect(() => { loadProjects(); }, [loadProjects]);

  const currentProject = projects.find((p) => p.id === currentProjectId);

  const selectStyle: React.CSSProperties = {
    background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', color: "var(--text-primary)",
    padding: '4px 8px', borderRadius: 4, fontSize: 12, cursor: 'pointer',
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <select
        value={currentProjectId ?? ''}
        onChange={(e) => {
          const v = e.target.value;
          setProject(v ? Number(v) : null);
        }}
        style={selectStyle}
        title={i18n.language === 'en-US' ? 'Select project' : '选择项目'}
      >
        <option value="">{i18n.language === 'en-US' ? 'All projects' : '全部项目'}</option>
        {projects.map((p) => (
          <option key={p.id} value={p.id}>{p.name}</option>
        ))}
      </select>
      {currentProjectId !== null && (
        <>
          <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>/</span>
          <select
            value={currentVersionId ?? ''}
            onChange={(e) => {
              const v = e.target.value;
              setVersion(v ? Number(v) : null);
            }}
            style={selectStyle}
            title={i18n.language === 'en-US' ? 'Select version' : '选择版本'}
          >
            <option value="">{i18n.language === 'en-US' ? 'All versions' : '全部版本'}</option>
            {versions.map((v) => (
              <option key={v.id} value={v.id}>{v.name}</option>
            ))}
          </select>
        </>
      )}
      {currentProject && (
        <span
          style={{
            width: 6, height: 6, borderRadius: '50%',
            background: currentProject.color, flexShrink: 0,
          }}
        />
      )}
    </div>
  );
}
