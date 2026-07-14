import { useEffect, useState } from 'react';
import { Plus, Trash2, Play, RefreshCw, AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useSchedStore } from '../store/schedStore';
import { useRunStore } from '../store/runStore';

export function SchedulePanel() {
  const { schedules, loading, unavailable, load, create, update, remove, trigger } = useSchedStore();
  const { cases, loadCases } = useRunStore();
  const { t } = useTranslation();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [cron, setCron] = useState('0 9 * * 1-5');
  const [selected, setSelected] = useState<number[]>([]);
  const [baseUrl, setBaseUrl] = useState('');

  useEffect(() => {
    load();
    loadCases();
  }, [load, loadCases]);

  const toggle = (id: number) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const submit = async () => {
    if (!name.trim() || selected.length === 0 || !cron.trim()) return;
    await create({ name, cron_expression: cron, case_ids: selected, base_url: baseUrl || null });
    setName(''); setCron('0 9 * * 1-5'); setSelected([]); setBaseUrl('');
    setShowForm(false);
  };

  if (unavailable) {
    return (
      <div style={{ padding: 24, color: 'var(--text-muted)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
        <AlertTriangle size={16} style={{ color: 'var(--chart-4)' }} />
        {t('ui.schedUnavailable')}
      </div>
    );
  }

  return (
    <div style={{ flex: 1, height: '100%', overflow: 'auto', padding: 16, color: "var(--text-primary)" }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h3 style={{ fontSize: 15, margin: 0 }}>{t('ui.scheduledExec')}</h3>
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={() => load()} style={btnStyle}><RefreshCw size={12} strokeWidth={1.5} /> {t('ui.refresh')}</button>
          <button onClick={() => setShowForm(!showForm)} style={primaryBtn}><Plus size={12} strokeWidth={1.5} /> {t('ui.create')}</button>
        </div>
      </div>

      {showForm && (
        <div style={{ background: 'var(--bg-card)', borderRadius: 8, padding: 16, marginBottom: 16 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <label style={labelStyle}>{t('ui.name')}
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder={t('ui.scheduleName')} style={inputStyle} />
            </label>
            <label style={labelStyle}>{t('ui.cronFullHint')}
              <input value={cron} onChange={(e) => setCron(e.target.value)} placeholder="0 9 * * 1-5" style={inputStyle} />
            </label>
            <div style={labelStyle}>{t('ui.selectCasesCount', { count: selected.length })}</div>
            <div style={{ maxHeight: 200, overflow: 'auto', border: '1px solid var(--bg-elevated)', borderRadius: 4, padding: 6 }}>
              {cases.map((c) => (
                <label key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: "var(--text-secondary)", padding: '2px 0' }}>
                  <input type="checkbox" checked={selected.includes(c.id)} onChange={() => toggle(c.id)} />
                  {c.title}
                </label>
              ))}
              {cases.length === 0 && <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('ui.noBatchCases')}</div>}
            </div>
            <label style={labelStyle}>{t('ui.sharedBaseUrlPlaceholder')}
              <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://staging.example.com" style={inputStyle} />
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={submit} style={primaryBtn}>{t('ui.create')}</button>
              <button onClick={() => setShowForm(false)} style={btnStyle}>{t('ui.cancel')}</button>
            </div>
          </div>
        </div>
      )}

      {loading && <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{t('ui.loading')}</div>}

      {schedules.map((s) => (
        <div key={s.id} style={{ background: 'var(--bg-card)', borderRadius: 6, padding: 12, marginBottom: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 13, color: "var(--text-primary)", flex: 1 }}>{s.name}</span>
            {s.enabled ? (
              <span style={badgeStyle('var(--success)')}>{t('ui.enabled')}</span>
            ) : (
              <span style={badgeStyle('var(--text-muted)')}>{t('ui.disabled')}</span>
            )}
            <button onClick={() => update(s.id, { enabled: !s.enabled })} style={btnStyle}>
              {s.enabled ? t('ui.disable') : t('ui.enable')}
            </button>
            <button onClick={() => trigger(s.id)} style={{ ...btnStyle, display: 'inline-flex', alignItems: 'center', gap: 3 }}>
              <Play size={11} strokeWidth={1.5} /> {t('ui.runNow')}
            </button>
            <button onClick={() => remove(s.id)} style={{ ...btnStyle, color: 'var(--error)', display: 'inline-flex', alignItems: 'center' }}>
              <Trash2 size={11} strokeWidth={1.5} />
            </button>
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 6 }}>
            {t('ui.cronLine', { cron: s.cron_expression, count: s.case_ids.length })}
            {s.base_url && ` · URL: ${s.base_url}`}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
            {t('ui.lastRunLine', { status: s.last_status ?? t('ui.notRun'), time: s.last_run_at ? new Date(s.last_run_at).toLocaleString() : '-' })}
          </div>
        </div>
      ))}

      {!loading && schedules.length === 0 && (
        <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{t('ui.noSchedules')}</div>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%', background: "var(--bg-base)", color: "var(--text-primary)", border: '1px solid var(--bg-elevated)',
  borderRadius: 4, padding: '6px 8px', fontSize: 13, marginTop: 4,
};
const labelStyle: React.CSSProperties = { fontSize: 11, color: "var(--text-muted)", display: 'block' };
const primaryBtn: React.CSSProperties = {
  background: "var(--accent)", color: "var(--bg-base)", border: 'none', borderRadius: 4,
  padding: '4px 12px', cursor: 'pointer', fontSize: 12, fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 4,
};
const btnStyle: React.CSSProperties = {
  background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)",
  borderRadius: 4, padding: '4px 10px', cursor: 'pointer', fontSize: 11,
};
function badgeStyle(color: string): React.CSSProperties {
  return { fontSize: 10, color, border: `1px solid ${color}`, borderRadius: 3, padding: '1px 6px' };
}
