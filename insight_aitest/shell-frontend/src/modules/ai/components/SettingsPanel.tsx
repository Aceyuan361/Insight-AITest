import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useConfigStore, type AIConfigUpdate, type ProviderOut, type ProviderUpsert } from '../store/configStore';
import { Play, AlertTriangle, Plus, Trash2, Check, Zap, Edit3, ChevronDown, Sun, Moon } from 'lucide-react';
import { useThemeStore, type Theme } from '@/shared/store/themeStore';

const inputStyle: React.CSSProperties = {
  flex: 1, background: "var(--bg-card)", border: '1px solid var(--bg-elevated)',
  borderRadius: 4, color: "var(--text-primary)", padding: '6px 8px', fontFamily: 'inherit', fontSize: 13,
};
const labelStyle: React.CSSProperties = {
  fontSize: 12, color: "var(--text-secondary)", width: 110, flexShrink: 0, paddingTop: 6,
};

export function SettingsPanel() {
  const { t } = useTranslation();
  const { config, loading, saving, loadConfig, updateConfig } = useConfigStore();
  const [form, setForm] = useState<AIConfigUpdate>({});
  const [vectorExpanded, setVectorExpanded] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  useEffect(() => {
    if (config) {
      setForm({
        chunk_size: config.chunk_size,
        chunk_overlap: config.chunk_overlap,
        top_k: config.top_k,
        min_score: config.min_score,
        rerank_enabled: config.rerank_enabled,
        rerank_fetch_k: config.rerank_fetch_k,
        history_turns: config.history_turns,
        ocr_enabled: config.ocr_enabled,
        vector_enabled: config.vector_enabled,
        embed_base_url: config.embed_base_url,
        embed_model: config.embed_model,
      });
      setVectorExpanded(config.vector_enabled);
    }
  }, [config]);

  if (loading || !config) {
    return <div style={{ padding: 24, color: "var(--text-muted)" }}>{t('settings.loadingConfig')}</div>;
  }

  const set = (k: keyof AIConfigUpdate, v: string | number | boolean) =>
    setForm((f) => ({ ...f, [k]: v }));

  const saveRag = async () => {
    setMsg(null);
    try {
      await updateConfig({ ...form });
      setMsg({ ok: true, text: t('settings.saved') });
    } catch (e: any) {
      setMsg({ ok: false, text: e.message || t('settings.saveFailed') });
    }
  };

  return (
    <div style={{ padding: 24, overflow: 'auto', color: "var(--text-primary)" }}>
      {/* ===== 主题切换 ===== */}
      <ThemeSection />

      {/* ===== Provider 管理（Cursor 风格灵活切换）===== */}
      <ProviderSection />

      {/* ===== 向量检索子分类（可折叠）===== */}
      <div style={{ borderTop: '1px solid var(--bg-card)', margin: '24px 0 4px', paddingTop: 14 }}>
        <button
          onClick={() => setVectorExpanded((v) => !v)}
          style={{
            background: 'none', border: 'none', color: "var(--text-secondary)", cursor: 'pointer',
            fontSize: 13, padding: 0, display: 'flex', alignItems: 'center', gap: 6,
          }}
        >
          <Play size={12} strokeWidth={1.5} style={{ color: form.vector_enabled ? "var(--accent)" : 'var(--text-secondary)', transform: vectorExpanded ? 'rotate(90deg)' : 'none', display: 'inline-flex' }} />
          {t('settings.vectorRetrieval')}{form.vector_enabled ? t('settings.ragEnabled') : t('settings.ragDisabled')}
        </button>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, marginBottom: 0 }}>
          {t('settings.ragHint')}
        </p>
      </div>

      {vectorExpanded && (
        <>
          <Row label={t('settings.enableVector')}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: "var(--text-secondary)", cursor: 'pointer' }}>
              <input type="checkbox" checked={form.vector_enabled ?? false}
                onChange={(e) => set('vector_enabled', e.target.checked)} />
              {t('settings.enableVectorHint')}
            </label>
          </Row>

          <Row label={t('settings.embedEndpoint')}>
            <input style={inputStyle} value={form.embed_base_url ?? ''}
              placeholder={t('settings.embedEndpointPlaceholder')}
              onChange={(e) => set('embed_base_url', e.target.value)} />
          </Row>

          <Row label={t('settings.vectorModel')}>
            <input style={inputStyle} value={form.embed_model ?? ''}
              onChange={(e) => set('embed_model', e.target.value)} />
          </Row>

          <Row label={t('settings.vectorDim')}>
            <input style={{ ...inputStyle, color: "var(--text-muted)", cursor: 'not-allowed' }}
              value={config.embed_dim} disabled
              title={t('settings.vectorDimTitle')} />
            <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 8 }}><AlertTriangle size={13} strokeWidth={1.5} style={{ verticalAlign: '-2px', marginRight: 4 }} />{t('settings.vectorDimHint')}</span>
          </Row>

          <Row label={t('settings.chunkSize')}>
            <NumInput value={form.chunk_size} onChange={(v) => set('chunk_size', v)} />
          </Row>
          <Row label={t('settings.chunkOverlap')}>
            <NumInput value={form.chunk_overlap} onChange={(v) => set('chunk_overlap', v)} />
          </Row>
          <Row label={t('settings.topK')}>
            <NumInput value={form.top_k} onChange={(v) => set('top_k', v)} />
          </Row>
          <Row label={t('settings.relevanceThreshold')}>
            <input style={inputStyle} type="number" step="0.05"
              value={form.min_score ?? ''} onChange={(e) => set('min_score', parseFloat(e.target.value))} />
          </Row>

          <Row label={t('settings.llmRerank')}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: "var(--text-secondary)", cursor: 'pointer' }}>
              <input type="checkbox" checked={form.rerank_enabled ?? false}
                onChange={(e) => set('rerank_enabled', e.target.checked)} />
              {t('settings.rerankHint')}
            </label>
          </Row>
          <Row label={t('settings.rerankCandidates')}>
            <NumInput value={form.rerank_fetch_k} onChange={(v) => set('rerank_fetch_k', v)} />
          </Row>
        </>
      )}

      <Row label={t('settings.imageOcr')}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: "var(--text-secondary)", cursor: 'pointer' }}>
          <input type="checkbox" checked={form.ocr_enabled ?? false}
            onChange={(e) => set('ocr_enabled', e.target.checked)} />
          {t('settings.ocrHint')}
        </label>
      </Row>

      <Row label={t('settings.historyRounds')}>
        <NumInput value={form.history_turns} onChange={(v) => set('history_turns', v)} />
      </Row>

      <div style={{ marginTop: 24, display: 'flex', alignItems: 'center', gap: 12 }}>
        <button
          onClick={saveRag}
          disabled={saving}
          style={{
            background: "var(--accent)", color: "var(--bg-base)", border: 'none', borderRadius: 6,
            padding: '8px 24px', cursor: saving ? 'wait' : 'pointer', fontWeight: 600,
          }}
        >
          {saving ? t('settings.saving') : t('settings.saveRag')}
        </button>
        {msg && (
          <span style={{ fontSize: 13, color: msg.ok ? 'var(--chart-4)' : "var(--error)" }}>{msg.text}</span>
        )}
      </div>
    </div>
  );
}

// ===== Provider 卡片管理区 =====
function ProviderSection() {
  const { t } = useTranslation();
  const { config, presets, loadPresets, upsertProvider, deleteProvider, activateProvider, testConnection, saving } = useConfigStore();
  const [editing, setEditing] = useState<ProviderOut | null>(null);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    loadPresets();
  }, [loadPresets]);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <strong style={{ fontSize: 14 }}>{t('settings.modelProvider')}</strong>
        <button
          onClick={() => { setAdding(true); setEditing(null); }}
          style={{
            background: 'none', border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)",
            borderRadius: 4, padding: '4px 10px', cursor: 'pointer', fontSize: 12,
            display: 'flex', alignItems: 'center', gap: 4,
          }}
        >
          <Plus size={13} strokeWidth={1.5} /> {t('settings.addProvider')}
        </button>
      </div>
      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 0, marginBottom: 12 }}>
        {t('settings.providerHint')}
      </p>

      {(config?.providers || []).length === 0 && !adding && (
        <div style={{ padding: 16, border: '1px dashed var(--bg-elevated)', borderRadius: 6, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>
          {t('settings.noProvider')}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {(config?.providers || []).map((p) => (
          <ProviderCard
            key={p.id}
            provider={p}
            isActive={p.id === config?.active_provider_id}
            onActivate={() => activateProvider(p.id)}
            onEdit={() => { setEditing(p); setAdding(false); }}
            onDelete={async () => {
              if (confirm(t('settings.confirmDeleteProvider', { name: p.name }))) {
                try { await deleteProvider(p.id); } catch (e: any) { alert(e.message); }
              }
            }}
          />
        ))}
      </div>

      {(adding || editing) && (
        <ProviderEditor
          provider={editing}
          presets={presets}
          saving={saving}
          onSave={async (body) => {
            try {
              await upsertProvider(editing ? editing.id : 'new', body);
              setAdding(false); setEditing(null);
            } catch (e: any) { alert(e.message); }
          }}
          onCancel={() => { setAdding(false); setEditing(null); }}
          onTest={testConnection}
        />
      )}
    </div>
  );
}

function ProviderCard({ provider, isActive, onActivate, onEdit, onDelete }: {
  provider: ProviderOut;
  isActive: boolean;
  onActivate: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div style={{
      border: `1px solid ${isActive ? 'var(--accent)' : 'var(--bg-elevated)'}`,
      background: isActive ? 'rgba(91,140,123,0.06)' : 'var(--bg-card)',
      borderRadius: 6, padding: 12,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <strong style={{ fontSize: 13 }}>{provider.name}</strong>
          {isActive && (
            <span style={{ fontSize: 10, color: 'var(--accent)', border: '1px solid var(--accent)', borderRadius: 3, padding: '1px 6px' }}>
              {t('settings.currentActive')}
            </span>
          )}
          {!provider.api_key_set && (
            <span style={{ fontSize: 10, color: 'var(--error)', border: '1px solid var(--error)', borderRadius: 3, padding: '1px 6px' }}>
              {t('settings.noApiKey')}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {!isActive && (
            <button onClick={onActivate} title={t('settings.activateProvider')}
              style={btnStyle('var(--accent)', 'var(--bg-base)')}>
              <Check size={12} strokeWidth={2} /> {t('settings.activate')}
            </button>
          )}
          <button onClick={onEdit} title={t('settings.editTitle')}
            style={btnStyle('transparent', 'var(--text-secondary)', '1px solid var(--bg-elevated)')}>
            <Edit3 size={12} strokeWidth={1.5} />
          </button>
          {!isActive && (
            <button onClick={onDelete} title={t('settings.deleteTitle')}
              style={btnStyle('transparent', 'var(--error)', '1px solid var(--bg-elevated)')}>
              <Trash2 size={12} strokeWidth={1.5} />
            </button>
          )}
        </div>
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.6 }}>
        <div>{t('settings.providerModel')}：<span style={{ color: 'var(--text-secondary)' }}>{provider.chat_model || '—'}</span></div>
        <div>{t('settings.providerEndpoint')}：<span style={{ color: 'var(--text-secondary)' }}>{provider.base_url}</span></div>
        {provider.vision_model && (
          <div>{t('settings.providerVision')}：<span style={{ color: 'var(--text-secondary)' }}>{provider.vision_model}</span></div>
        )}
      </div>
    </div>
  );
}

function ProviderEditor({ provider, presets, saving, onSave, onCancel, onTest }: {
  provider: ProviderOut | null;
  presets: { name: string; base_url: string; models: string[] }[];
  saving: boolean;
  onSave: (body: ProviderUpsert) => void;
  onCancel: () => void;
  onTest: (baseUrl: string, apiKey: string, model: string) => Promise<{ ok: boolean; message: string }>;
}) {
  const [name, setName] = useState(provider?.name || '');
  const [baseUrl, setBaseUrl] = useState(provider?.base_url || '');
  const [apiKey, setApiKey] = useState('');
  const [chatModel, setChatModel] = useState(provider?.chat_model || '');
  const [visionModel, setVisionModel] = useState(provider?.vision_model || '');
  const [modelOpen, setModelOpen] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [testing, setTesting] = useState(false);
  const { t } = useTranslation();

  // 匹配预设的模型列表
  const matchedPreset = presets.find((s) => s.base_url === baseUrl);
  const modelOptions = matchedPreset?.models || [];

  const handlePresetPick = (p: { name: string; base_url: string; models: string[] }) => {
    setName(name || p.name);
    setBaseUrl(p.base_url);
    if (!chatModel && p.models.length > 0) setChatModel(p.models[0]);
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await onTest(baseUrl, apiKey || 'placeholder', chatModel);
      setTestResult(r);
    } catch (e: any) {
      setTestResult({ ok: false, message: e.message });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = () => {
    if (!name.trim()) { alert(t('settings.fillName')); return; }
    if (!baseUrl.trim()) { alert(t('settings.fillBaseUrl')); return; }
    if (!chatModel.trim()) { alert(t('settings.fillChatModel')); return; }
    onSave({
      name: name.trim(),
      base_url: baseUrl.trim(),
      api_key: apiKey.trim() || undefined,
      chat_model: chatModel.trim(),
      vision_model: visionModel.trim(),
    });
  };

  return (
    <div style={{
      marginTop: 8, border: '1px solid var(--accent)', borderRadius: 6, padding: 12,
      background: 'var(--bg-base)',
    }}>
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
        {provider ? t('settings.editProvider') : t('settings.newProvider')}
      </div>

      {/* 预设快捷填充 */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
        {presets.map((p) => (
          <button key={p.name} onClick={() => handlePresetPick(p)}
            style={{
              background: baseUrl === p.base_url ? 'rgba(91,140,123,0.12)' : 'var(--bg-card)',
              border: baseUrl === p.base_url ? '1px solid var(--accent)' : '1px solid var(--bg-elevated)',
              color: baseUrl === p.base_url ? 'var(--accent)' : 'var(--text-secondary)',
              padding: '3px 8px', borderRadius: 3, cursor: 'pointer', fontSize: 11,
            }}>
            {p.name}
          </button>
        ))}
      </div>

      <Row label={t('settings.fieldName')}>
        <input style={inputStyle} value={name} placeholder={t('settings.namePlaceholder')}
          onChange={(e) => setName(e.target.value)} />
      </Row>
      <Row label="Base URL">
        <input style={inputStyle} value={baseUrl} placeholder="https://api.openai.com/v1"
          onChange={(e) => setBaseUrl(e.target.value)} />
      </Row>
      <Row label={t('settings.apiKey')}>
        <input style={inputStyle} type="password" value={apiKey}
          placeholder={provider?.api_key_set ? t('settings.apiKeySet') : t('settings.apiKeyPlaceholder')}
          onChange={(e) => setApiKey(e.target.value)} />
      </Row>
      <Row label={t('settings.chatModel')}>
        <div style={{ flex: 1, position: 'relative' }}>
          <input style={inputStyle} value={chatModel} placeholder={t('settings.chatModelPlaceholder')}
            onChange={(e) => setChatModel(e.target.value)}
            onFocus={() => setModelOpen(true)}
            onBlur={() => setTimeout(() => setModelOpen(false), 150)} />
          {modelOptions.length > 0 && (
            <button onClick={() => setModelOpen((v) => !v)}
              style={{ position: 'absolute', right: 4, top: 4, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4 }}>
              <ChevronDown size={13} />
            </button>
          )}
          {modelOpen && modelOptions.length > 0 && (
            <div style={{
              position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10,
              background: 'var(--bg-card)', border: '1px solid var(--bg-elevated)', borderRadius: 4,
              maxHeight: 160, overflow: 'auto', boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            }}>
              {modelOptions.map((m) => (
                <div key={m} onMouseDown={() => { setChatModel(m); setModelOpen(false); }}
                  style={{ padding: '6px 8px', fontSize: 12, cursor: 'pointer', color: 'var(--text-secondary)' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-elevated)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}>
                  {m}
                </div>
              ))}
            </div>
          )}
        </div>
      </Row>
      <Row label={t('settings.visionModel')}>
        <input style={inputStyle} value={visionModel} placeholder={t('settings.visionModelPlaceholder')}
          onChange={(e) => setVisionModel(e.target.value)} />
      </Row>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12 }}>
        <button onClick={handleSave} disabled={saving}
          style={{ background: 'var(--accent)', color: 'var(--bg-base)', border: 'none', borderRadius: 4, padding: '6px 16px', cursor: saving ? 'wait' : 'pointer', fontSize: 12, fontWeight: 600 }}>
          {saving ? t('settings.saving') : t('settings.save')}
        </button>
        <button onClick={handleTest} disabled={testing || !baseUrl || !chatModel}
          style={{ background: 'none', border: '1px solid var(--bg-elevated)', color: 'var(--text-secondary)', borderRadius: 4, padding: '6px 12px', cursor: testing ? 'wait' : 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
          <Zap size={12} strokeWidth={1.5} /> {testing ? t('settings.testing') : t('settings.testConnection')}
        </button>
        <button onClick={onCancel}
          style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12 }}>
          {t('common.cancel')}
        </button>
        {testResult && (
          <span style={{ fontSize: 11, color: testResult.ok ? 'var(--chart-4)' : 'var(--error)' }}>
            {testResult.ok ? '✓ ' : '✗ '}{testResult.message}
          </span>
        )}
      </div>
    </div>
  );
}

function ThemeSection() {
  const { t } = useTranslation();
  const { theme, setTheme } = useThemeStore();
  const options: { value: Theme; label: string; icon: typeof Sun }[] = [
    { value: 'dark', label: t('settings.dark'), icon: Moon },
    { value: 'light', label: t('settings.light'), icon: Sun },
  ];
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
        <Play size={12} strokeWidth={1.5} style={{ color: "var(--accent)" }} />
        {t('settings.appearance')}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        {options.map((opt) => {
          const active = theme === opt.value;
          const Icon = opt.icon;
          return (
            <button
              key={opt.value}
              onClick={() => setTheme(opt.value)}
              style={{
                flex: 1,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                padding: '10px 12px', fontSize: 13,
                background: active ? 'var(--accent)' : 'var(--bg-card)',
                color: active ? 'var(--bg-base)' : 'var(--text-secondary)',
                border: `1px solid ${active ? 'var(--accent)' : 'var(--bg-elevated)'}`,
                borderRadius: 6, cursor: 'pointer', transition: 'all 0.15s',
              }}
            >
              <Icon size={14} strokeWidth={1.5} />
              {opt.label}
            </button>
          );
        })}
      </div>
      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, marginBottom: 0 }}>
        {t('settings.themeHint')}
      </p>
    </div>
  );
}

function btnStyle(bg: string, color: string, border?: string): React.CSSProperties {
  return {
    background: bg, color, border: border || 'none',
    borderRadius: 3, padding: '3px 8px', cursor: 'pointer', fontSize: 11,
    display: 'flex', alignItems: 'center', gap: 3,
  };
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', marginBottom: 10 }}>
      <span style={labelStyle}>{label}</span>
      <div style={{ display: 'flex', flex: 1, alignItems: 'center', flexWrap: 'wrap', gap: 4 }}>
        {children}
      </div>
    </div>
  );
}

function NumInput({ value, onChange }: { value: number | undefined; onChange: (v: number) => void }) {
  return (
    <input style={inputStyle} type="number"
      value={value ?? ''} onChange={(e) => onChange(parseInt(e.target.value, 10) || 0)} />
  );
}
