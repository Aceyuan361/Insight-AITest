import { useEffect, useState } from 'react';
import { Eye, Check, AlertTriangle, Loader, Zap } from 'lucide-react';
import { useTranslation, Trans } from 'react-i18next';
import { useConfigStore } from '../store/configStore';

const PRESETS = [
  { label: 'GPT-4o', base_url: 'https://api.openai.com/v1', model: 'gpt-4o' },
  { label: 'GPT-4o mini', base_url: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
  { label: 'Claude 3.5 Sonnet', base_url: 'https://api.anthropic.com/v1', model: 'claude-3-5-sonnet-20241022' },
  { label: '通义千问 VL', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-vl-max' },
];

export function VisionConfig() {
  const { config, loading, saving, load, save, test } = useConfigStore();
  const { t } = useTranslation();
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('');
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (config) {
      setBaseUrl(config.base_url);
      setModel(config.model);
    }
  }, [config]);

  const doSave = async () => {
    setMsg(null);
    await save({ base_url: baseUrl, api_key: apiKey || undefined, model });
    setMsg({ ok: true, text: t('ui.saved') });
    setApiKey('');
  };

  const doTest = async () => {
    setMsg(null);
    setTesting(true);
    // 测试时用配置中的 api_key（如果输入框有新值则用新值）
    const cfg = config;
    const key = apiKey || (cfg?.api_key_set ? '__use_saved__' : '');
    if (!key || key === '__use_saved__') {
      // 后端 test 接口需要明文 key，如果没输入则提示
      if (!apiKey) {
        setMsg({ ok: false, text: t('ui.enterApiKey') });
        setTesting(false);
        return;
      }
    }
    const result = await test(baseUrl || config?.global_base_url || '', apiKey, model || config?.global_model || '');
    setMsg({ ok: result.ok, text: result.message });
    setTesting(false);
  };

  if (loading) return <div style={{ padding: 24, color: 'var(--text-muted)', fontSize: 13 }}>{t('ui.loading')}</div>;

  return (
    <div style={{ flex: 1, height: '100%', overflow: 'auto', padding: 16, color: "var(--text-primary)", maxWidth: 600 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <Eye size={18} style={{ color: 'var(--accent)' }} />
        <h3 style={{ fontSize: 15, margin: 0 }}>{t('ui.visionConfigTitle')}</h3>
      </div>

      {/* 说明 */}
      <div style={{
        background: 'var(--surface-tint)', borderRadius: 8, padding: 12, marginBottom: 16,
        fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6,
      }}>
        <Trans t={t} i18nKey="ui.visionDesc1" components={{ strong: <strong style={{ color: 'var(--text-secondary)' }} /> }} />
        <br />
        {t('ui.visionDesc2', { model: config?.global_model || '-' })}
        <br />
        {t('ui.visionDesc3')}
      </div>

      {/* 快捷预设 */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>{t('ui.quickSelect')}</div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {PRESETS.map((p) => (
            <button key={p.label} onClick={() => { setBaseUrl(p.base_url); setModel(p.model); }} style={{
              background: 'var(--bg-card)', border: '1px solid var(--bg-elevated)', color: 'var(--text-secondary)',
              borderRadius: 4, padding: '4px 10px', cursor: 'pointer', fontSize: 11,
            }}>{p.label}</button>
          ))}
        </div>
      </div>

      {/* 表单 */}
      <label style={labelStyle}>
        {t('ui.visionBaseUrl')}
        <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)}
          placeholder={config ? t('ui.baseUrlPlaceholderGlobal', { url: config.global_base_url }) : 'https://api.openai.com/v1'}
          style={inputStyle} />
      </label>

      <label style={labelStyle}>
        {t('ui.visionApiKey')}
        <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
          placeholder={config?.api_key_set ? t('ui.apiKeyConfigured') : t('ui.apiKeyUseGlobal')}
          style={inputStyle} />
      </label>

      <label style={labelStyle}>
        {t('ui.visionModelName')}
        <input value={model} onChange={(e) => setModel(e.target.value)}
          placeholder={config ? t('ui.baseUrlPlaceholderGlobal', { url: config.global_model }) : 'gpt-4o'}
          style={inputStyle} />
      </label>

      {/* 按钮 */}
      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        <button onClick={doSave} disabled={saving} style={primaryBtn}>
          {saving ? <><Loader size={12} className="animate-spin" /> {t('ui.saving')}</> : t('ui.saveVision')}
        </button>
        <button onClick={doTest} disabled={testing} style={secondaryBtn}>
          {testing ? <><Loader size={12} className="animate-spin" /> {t('ui.testing')}</> : <><Zap size={12} /> {t('ui.testConnection')}</>}
        </button>
      </div>

      {/* 消息 */}
      {msg && (
        <div style={{
          marginTop: 12, fontSize: 12, padding: '6px 10px', borderRadius: 4,
          color: msg.ok ? 'var(--success)' : 'var(--error)',
          background: msg.ok ? 'rgba(34,197,94,0.05)' : 'rgba(239,68,68,0.05)',
          display: 'inline-flex', alignItems: 'flex-start', gap: 6,
        }}>
          {msg.ok ? <Check size={13} style={{ flexShrink: 0, marginTop: 1 }} /> : <AlertTriangle size={13} style={{ flexShrink: 0, marginTop: 1 }} />}
          <span>{msg.text}</span>
        </div>
      )}
    </div>
  );
}

const labelStyle: React.CSSProperties = { display: 'block', fontSize: 11, color: 'var(--text-muted)', marginBottom: 12 };
const inputStyle: React.CSSProperties = {
  width: '100%', display: 'block', marginTop: 4,
  background: 'var(--bg-card)', border: '1px solid var(--bg-elevated)', borderRadius: 4,
  color: 'var(--text-primary)', padding: '8px 10px', fontSize: 13,
};
const primaryBtn: React.CSSProperties = {
  background: 'var(--accent)', color: 'var(--bg-base)', border: 'none', borderRadius: 4,
  padding: '8px 16px', cursor: 'pointer', fontSize: 12, fontWeight: 600,
  display: 'inline-flex', alignItems: 'center', gap: 6,
};
const secondaryBtn: React.CSSProperties = {
  background: 'var(--bg-card)', border: '1px solid var(--bg-elevated)', color: 'var(--text-secondary)',
  borderRadius: 4, padding: '8px 16px', cursor: 'pointer', fontSize: 12,
  display: 'inline-flex', alignItems: 'center', gap: 6,
};
