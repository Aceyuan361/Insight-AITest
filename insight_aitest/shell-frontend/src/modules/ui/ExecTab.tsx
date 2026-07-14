import { useEffect, useState } from 'react';
import { Play, ArrowLeft, ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useRunStore } from './store/runStore';
import { useProjectStore } from '../../shared/store/projectStore';
import { useIsMobile } from '../../shared/hooks/useIsMobile';
import { CasePicker } from '../../shared/components/CasePicker';
import { RunList } from '../../shared/components/RunList';
import { RunDetail } from './components/RunDetail';

const DEFAULT_CONFIG = {
  headless: true,
  viewport_width: 1280,
  viewport_height: 720,
  timeout: 30000,
  retry: 0,
  screenshot_on_failure: true,
};

function loadConfig(): typeof DEFAULT_CONFIG {
  try {
    const saved = localStorage.getItem('ui_browser_config');
    if (saved) return { ...DEFAULT_CONFIG, ...JSON.parse(saved) };
  } catch {}
  return DEFAULT_CONFIG;
}

function saveConfig(cfg: typeof DEFAULT_CONFIG) {
  try { localStorage.setItem('ui_browser_config', JSON.stringify(cfg)); } catch {}
}

export function ExecTab() {
  const { cases, loadingCases, selectedCaseId, runs, selectedRun, executing, execError,
          loadCases, selectCase, execute, loadRunDetail } = useRunStore();
  const { t } = useTranslation();
  const [baseUrl, setBaseUrl] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [config, setConfig] = useState(loadConfig);
  const currentProjectId = useProjectStore((s) => s.currentProjectId);
  const currentVersionId = useProjectStore((s) => s.currentVersionId);
  const isMobile = useIsMobile();
  useEffect(() => { loadCases(); }, [loadCases, currentProjectId, currentVersionId]);
  const selectedCase = cases.find((c) => c.id === selectedCaseId);

  const updateConfig = (patch: Partial<typeof DEFAULT_CONFIG>) => {
    const next = { ...config, ...patch };
    setConfig(next);
    saveConfig(next);
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: isMobile ? 'column' : 'row' }}>
      <div style={{
        width: isMobile ? '100%' : 280,
        borderRight: isMobile ? 'none' : '1px solid var(--bg-card)',
        borderBottom: isMobile ? '1px solid var(--bg-card)' : 'none',
        display: 'flex', flexDirection: 'column',
        ...(isMobile ? { maxHeight: 320, overflowY: 'auto' } : {}),
      }}>
        <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--bg-card)', fontSize: 13, color: "var(--text-secondary)" }}>{t('ui.casesTitle')}</div>
        <CasePicker cases={cases} selectedId={selectedCaseId} onSelect={selectCase} loading={loadingCases} emptyLabel={t('ui.noCasesHint')} />
      </div>
      <div style={{
        width: isMobile ? '100%' : 340,
        borderRight: isMobile ? 'none' : '1px solid var(--bg-card)',
        borderBottom: isMobile ? '1px solid var(--bg-card)' : 'none',
        display: 'flex', flexDirection: 'column',
        ...(isMobile ? { maxHeight: 400, overflowY: 'auto' } : {}),
      }}>
        <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--bg-card)', display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{selectedCase ? selectedCase.title : t('ui.selectCase')}</span>
          <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)}
            placeholder={t('ui.baseUrlOverridePlaceholder')}
            style={{ background: "var(--bg-base)", color: "var(--text-primary)", border: '1px solid var(--bg-elevated)', borderRadius: 3, padding: '4px 8px', fontSize: 12 }} />

          {/* 高级设置 */}
          <button onClick={() => setShowAdvanced(!showAdvanced)} style={{
            background: 'transparent', border: 'none', color: "var(--text-muted)", cursor: 'pointer',
            fontSize: 11, display: 'inline-flex', alignItems: 'center', gap: 4, padding: 0,
          }}>
            {showAdvanced ? <ChevronUp size={11} strokeWidth={1.5} /> : <ChevronDown size={11} strokeWidth={1.5} />}
            {t('ui.advancedSettings')}
          </button>
          {showAdvanced && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, padding: '6px 0' }}>
              <label style={{ fontSize: 11, color: "var(--text-secondary)", display: 'flex', alignItems: 'center', gap: 6 }}>
                <input type="checkbox" checked={config.headless}
                  onChange={(e) => updateConfig({ headless: e.target.checked })} />
                {t('ui.headlessMode')}
              </label>
              <div style={{ display: 'flex', gap: 6 }}>
                <label style={{ fontSize: 11, color: "var(--text-muted)", flex: 1 }}>
                  {t('ui.width')}
                  <input type="number" value={config.viewport_width} min={320} max={3840}
                    onChange={(e) => updateConfig({ viewport_width: Number(e.target.value) })}
                    style={numInputStyle} />
                </label>
                <label style={{ fontSize: 11, color: "var(--text-muted)", flex: 1 }}>
                  {t('ui.height')}
                  <input type="number" value={config.viewport_height} min={240} max={3840}
                    onChange={(e) => updateConfig({ viewport_height: Number(e.target.value) })}
                    style={numInputStyle} />
                </label>
              </div>
              <label style={{ fontSize: 11, color: "var(--text-muted)" }}>
                {t('ui.timeoutMs')}
                <input type="number" value={config.timeout} min={1000} max={300000} step={1000}
                  onChange={(e) => updateConfig({ timeout: Number(e.target.value) })}
                  style={numInputStyle} />
              </label>
              <label style={{ fontSize: 11, color: "var(--text-muted)" }}>
                {t('ui.retryCount')}
                <input type="number" value={config.retry} min={0} max={5}
                  onChange={(e) => updateConfig({ retry: Number(e.target.value) })}
                  style={numInputStyle} />
              </label>
              <label style={{ fontSize: 11, color: "var(--text-secondary)", display: 'flex', alignItems: 'center', gap: 6 }}>
                <input type="checkbox" checked={config.screenshot_on_failure}
                  onChange={(e) => updateConfig({ screenshot_on_failure: e.target.checked })} />
                {t('ui.screenshotOnFailure')}
              </label>
            </div>
          )}

          {execError && (
            <div style={{ fontSize: 11, color: 'var(--error)', background: 'var(--surface-tint)', padding: '4px 8px', borderRadius: 3, display: 'flex', alignItems: 'flex-start', gap: 4 }}>
              <AlertTriangle size={12} strokeWidth={1.5} style={{ flexShrink: 0, marginTop: 1 }} />
              <span>{execError}</span>
            </div>
          )}

          {selectedCase && (
            <button onClick={() => execute(selectedCase.id, baseUrl || undefined, config)} disabled={executing} style={{
              background: "var(--accent)", color: "var(--bg-base)", border: 'none', borderRadius: 4,
              padding: '6px 12px', cursor: executing ? 'wait' : 'pointer', fontSize: 12, fontWeight: 600,
              display: 'inline-flex', alignItems: 'center', gap: 4,
            }}>{executing ? t('ui.executing') : <><Play size={12} strokeWidth={1.5} /> {t('ui.run')}</>}</button>
          )}
        </div>
        {selectedCase ? (
          <RunList runs={runs} selectedRunId={selectedRun?.id ?? null} onSelect={loadRunDetail} />
        ) : (
          <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <ArrowLeft size={12} strokeWidth={1.5} /> {t('ui.selectCase')}
          </div>
        )}
      </div>
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--bg-card)', fontSize: 13, color: "var(--text-secondary)" }}>{t('ui.execDetail')}</div>
        <div style={{ flex: 1, overflow: 'auto' }}><RunDetail run={selectedRun} /></div>
      </div>
    </div>
  );
}

const numInputStyle: React.CSSProperties = {
  width: '100%', background: "var(--bg-base)", color: "var(--text-primary)", border: '1px solid var(--bg-elevated)',
  borderRadius: 3, padding: '3px 6px', fontSize: 11, marginTop: 2,
};
