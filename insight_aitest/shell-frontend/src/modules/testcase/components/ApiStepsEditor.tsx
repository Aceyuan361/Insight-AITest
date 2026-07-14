import { useState, useRef } from 'react';
import { ArrowUp, ArrowDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';

/** 单条 API 测试步骤 */
export interface ApiStep {
  method: string;        // GET/POST/PUT/PATCH/DELETE
  path: string;          // /api/login
  headers?: Record<string, string>;
  body?: Record<string, unknown> | string;
  assertions?: ApiAssertion[];
  extract?: Record<string, string>;  // {varName: "$.jsonpath"}
}

export interface ApiAssertion {
  type: string;        // status_code|header|jsonpath|response_time|json_schema|contains
  expected: string;
  path?: string;       // for jsonpath/header types
}

export interface ApiContent {
  base_url: string;
  steps: ApiStep[];
}

interface ApiStepsEditorProps {
  content: ApiContent;
  onChange: (content: ApiContent) => void;
}

const METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];
const ASSERTION_TYPE_KEYS: Record<string, string> = {
  status_code: 'testcase.assertionStatusCode',
  header: 'testcase.assertionHeader',
  jsonpath: 'testcase.assertionJsonPath',
  response_time: 'testcase.assertionResponseTime',
  json_schema: 'testcase.assertionJsonSchema',
  contains: 'testcase.assertionContains',
};
const ASSERTION_TYPE_VALUES = ['status_code', 'header', 'jsonpath', 'response_time', 'json_schema', 'contains'];
// 断言类型需要 path 字段（jsonpath 取值路径 / header 头名）
const TYPES_NEED_PATH = new Set(['jsonpath', 'header']);

/** 受控 JSON 文本域：把对象/字符串与可编辑文本互转，解析失败时显示红框。
 *  用「上次发出值」做参照，仅在外部值变化（非自身编辑回显）时才同步显示文本，
 *  避免每次合法输入都被 pretty-print 覆盖，同时正确处理步骤重排。 */
function JsonField({ value, onChange, placeholder }: {
  value: Record<string, unknown> | string | undefined;
  onChange: (v: Record<string, unknown> | string) => void;
  placeholder?: string;
}) {
  const [text, setText] = useState<string>(() => (
    value && typeof value === 'object' ? JSON.stringify(value, null, 2)
    : typeof value === 'string' ? value : ''
  ));
  const [error, setError] = useState(false);
  const lastEmitted = useRef<unknown>(value);

  // 外部值与上次发出值不一致 → 是外部改动（如重排/初始化），同步显示
  if (value !== lastEmitted.current) {
    lastEmitted.current = value;
    const next = value && typeof value === 'object' ? JSON.stringify(value, null, 2)
      : typeof value === 'string' ? value : '';
    setText(next);
    setError(false);
  }

  const update = (raw: string) => {
    setText(raw);
    if (!raw.trim()) {
      setError(false);
      lastEmitted.current = '';
      onChange('');
      return;
    }
    try {
      const parsed = JSON.parse(raw);
      setError(false);
      lastEmitted.current = parsed;
      onChange(parsed);
    } catch {
      setError(true);
      lastEmitted.current = raw;
      onChange(raw);
    }
  };

  return (
    <textarea
      style={{ ...jsonAreaStyle, borderColor: error ? 'var(--error)' : 'var(--bg-elevated)' }}
      placeholder={placeholder}
      value={text}
      onChange={(e) => update(e.target.value)}
    />
  );
}

export function ApiStepsEditor({ content, onChange }: ApiStepsEditorProps) {
  const { t } = useTranslation();
  const steps = content.steps || [];
  const update = (patch: Partial<ApiContent>) => onChange({ ...content, ...patch });
  const updateStep = (i: number, patch: Partial<ApiStep>) =>
    update({ steps: steps.map((s, idx) => (idx === i ? { ...s, ...patch } : s)) });
  const addStep = () => update({
    steps: [...steps, { method: 'GET', path: '/', headers: {}, body: {}, assertions: [], extract: {} }],
  });
  const delStep = (i: number) => update({ steps: steps.filter((_, idx) => idx !== i) });
  const moveStep = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= steps.length) return;
    const arr = [...steps];
    [arr[i], arr[j]] = [arr[j], arr[i]];
    update({ steps: arr });
  };

  return (
    <div>
      <div style={sectionLabelStyle}>Base URL</div>
      <input
        style={{ ...inputStyle, width: '100%' }}
        placeholder="https://example.com"
        value={content.base_url || ''}
        onChange={(e) => update({ base_url: e.target.value })}
      />

      <div style={{ ...sectionLabelStyle, marginTop: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>{t('testcase.apiStepsLabel')}</span>
        <button onClick={addStep} style={{ ...miniBtn, border: '1px dashed var(--bg-elevated)', padding: '4px 10px' }}>
          + {t('testcase.addStep')}
        </button>
      </div>

      {steps.length === 0 && (
        <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '8px 0' }}>{t('testcase.noStepsHint')}</div>
      )}

      {steps.map((s, i) => (
        <StepCard
          key={i}
          index={i}
          total={steps.length}
          step={s}
          onChange={(patch) => updateStep(i, patch)}
          onDelete={() => delStep(i)}
          onMove={(dir) => moveStep(i, dir)}
        />
      ))}
    </div>
  );
}

function StepCard({ index, total, step, onChange, onDelete, onMove }: {
  index: number;
  total: number;
  step: ApiStep;
  onChange: (patch: Partial<ApiStep>) => void;
  onDelete: () => void;
  onMove: (dir: -1 | 1) => void;
}) {
  const { t } = useTranslation();
  const assertions = step.assertions || [];
  const extract = step.extract || {};
  const extractEntries = Object.entries(extract);

  const updateAssertion = (ai: number, patch: Partial<ApiAssertion>) =>
    onChange({ assertions: assertions.map((a, idx) => (idx === ai ? { ...a, ...patch } : a)) });
  const addAssertion = () =>
    onChange({ assertions: [...assertions, { type: 'status_code', expected: '200' }] });
  const delAssertion = (ai: number) =>
    onChange({ assertions: assertions.filter((_, idx) => idx !== ai) });

  return (
    <div style={cardStyle}>
      {/* 头部：序号 + method + path + 操作 */}
      <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 10 }}>
        <span style={{ color: 'var(--accent)', width: 20, fontSize: 13, flexShrink: 0 }}>{index + 1}</span>
        <select
          style={{ ...inputStyle, width: 110, flexShrink: 0, fontWeight: 600 }}
          value={step.method}
          onChange={(e) => onChange({ method: e.target.value })}
        >
          {METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <input
          style={{ ...inputStyle, flex: 1 }}
          placeholder="/api/login"
          value={step.path}
          onChange={(e) => onChange({ path: e.target.value })}
        />
        <button onClick={() => onMove(-1)} disabled={index === 0}
          style={{ ...miniBtn, opacity: index === 0 ? 0.3 : 1, display: 'inline-flex', alignItems: 'center' }}>
          <ArrowUp size={12} strokeWidth={1.5} />
        </button>
        <button onClick={() => onMove(1)} disabled={index === total - 1}
          style={{ ...miniBtn, opacity: index === total - 1 ? 0.3 : 1, display: 'inline-flex', alignItems: 'center' }}>
          <ArrowDown size={12} strokeWidth={1.5} />
        </button>
        <button onClick={onDelete} style={{ ...miniBtn, color: 'var(--error)' }}>×</button>
      </div>

      {/* Headers */}
      <div style={subLabelStyle}>Headers (JSON)</div>
      <JsonField
        value={step.headers}
        placeholder={'{\n  "Content-Type": "application/json"\n}'}
        onChange={(v) => onChange({ headers: typeof v === 'string' ? (v ? step.headers : {}) : v as Record<string, string> })}
      />

      {/* Body */}
      <div style={{ ...subLabelStyle, marginTop: 10 }}>Body (JSON)</div>
      <JsonField
        value={step.body}
        placeholder={'{\n  "username": "admin"\n}'}
        onChange={(v) => onChange({ body: v as Record<string, unknown> | string })}
      />

      {/* Assertions */}
      <div style={{ ...subLabelStyle, marginTop: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>{t('testcase.assertionsLabel')}</span>
        <button onClick={addAssertion} style={{ ...miniBtn, border: '1px dashed var(--bg-elevated)', padding: '2px 8px' }}>
          {t('testcase.addAssertion')}
        </button>
      </div>
      {assertions.length === 0 && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', padding: '4px 0' }}>{t('testcase.noAssertions')}</div>
      )}
      {assertions.map((a, ai) => (
        <div key={ai} style={{ display: 'flex', gap: 6, marginBottom: 6, alignItems: 'center' }}>
          <select style={{ ...inputStyle, width: 180 }} value={a.type}
            onChange={(e) => updateAssertion(ai, { type: e.target.value })}>
            {ASSERTION_TYPE_VALUES.map((val) => <option key={val} value={val}>{t(ASSERTION_TYPE_KEYS[val])}</option>)}
          </select>
          {TYPES_NEED_PATH.has(a.type) && (
            <input style={{ ...inputStyle, width: 140 }} placeholder="$.data.id / Content-Type"
              value={a.path || ''} onChange={(e) => updateAssertion(ai, { path: e.target.value })} />
          )}
          <input style={{ ...inputStyle, flex: 1 }} placeholder={t('testcase.expectedValuePlaceholder')}
            value={a.expected} onChange={(e) => updateAssertion(ai, { expected: e.target.value })} />
          <button onClick={() => delAssertion(ai)} style={{ ...miniBtn, color: 'var(--error)' }}>×</button>
        </div>
      ))}

      {/* Extract (只读展示) */}
      <div style={{ ...subLabelStyle, marginTop: 10 }}>{t('testcase.extractVariablesLabel')}</div>
      {extractEntries.length === 0 ? (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', padding: '4px 0' }}>{t('testcase.noExtract')}</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {extractEntries.map(([k, v]) => (
            <div key={k} style={extractRowStyle}>
              <code style={{ color: 'var(--chart-2)' }}>{k}</code>
              <span style={{ color: 'var(--text-muted)' }}>←</span>
              <code style={{ color: 'var(--text-secondary)' }}>{v}</code>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', borderRadius: 4,
  color: "var(--text-primary)", padding: '6px 8px', fontFamily: 'inherit', fontSize: 13,
};
const jsonAreaStyle: React.CSSProperties = {
  background: "var(--bg-card)", border: '1px solid var(--bg-elevated)', borderRadius: 4,
  color: "var(--text-primary)", padding: '8px', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
  fontSize: 12, width: '100%', minHeight: 64, resize: 'vertical',
};
const miniBtn: React.CSSProperties = {
  background: 'none', border: '1px solid var(--bg-elevated)', color: "var(--text-secondary)",
  padding: '2px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 12,
};
const sectionLabelStyle: React.CSSProperties = { fontSize: 12, color: "var(--text-secondary)", marginBottom: 6 };
const subLabelStyle: React.CSSProperties = { fontSize: 11, color: "var(--text-muted)", marginBottom: 4 };
const cardStyle: React.CSSProperties = {
  background: 'var(--bg-base)', border: '1px solid var(--bg-card)', borderRadius: 6,
  padding: 12, marginBottom: 10,
};
const extractRowStyle: React.CSSProperties = {
  display: 'flex', gap: 8, alignItems: 'center', fontSize: 12,
  background: 'var(--bg-card)', padding: '3px 8px', borderRadius: 4,
};
