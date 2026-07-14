import { useEffect, useState } from 'react';

/** /api/platform/dashboard/summary 返回结构。 */
interface DashboardSummary {
  executions: ExecutionItem[];
  stats: {
    api?: ModuleStat;
    ui?: ModuleStat;
  };
  testcases: { total: number; by_result: Record<string, number> };
  monitoring: { total_sessions: number; active_sessions: number };
}

interface ExecutionItem {
  id: number;
  module: string; // 'api' | 'ui'
  case_id?: number;
  case_title?: string;
  status: string; // passed/failed/error
  total_steps?: number;
  passed_steps?: number;
  duration_ms?: number;
  started_at?: string;
}

interface ModuleStat {
  total: number;
  passed: number;
  pass_rate: number;
  avg_duration_ms: number;
}

const STATUS_COLOR: Record<string, string> = {
  passed: 'var(--chart-4)',
  failed: "var(--error)",
  error: 'var(--chart-3)',
};

const RESULT_LABEL: Record<string, string> = {
  passed: '通过',
  failed: '失败',
  blocked: '阻塞',
  error: '错误',
  not_run: '未执行',
};

export function DashboardOverview() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetch('/api/platform/dashboard/summary')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => setData(d))
      .catch((e) => setError(e.message || '加载失败'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 24, color: "var(--text-muted)" }}>加载仪表盘…</div>;
  if (error || !data) {
    return <div style={{ padding: 24, color: "var(--error)" }}>仪表盘加载失败：{error}</div>;
  }

  const apiStat = data.stats.api;
  const uiStat = data.stats.ui;
  const tcByResult = data.testcases.by_result || {};

  return (
    <div style={{ padding: 24, color: "var(--text-primary)" }}>
      <h1 style={{ marginBottom: 4 }}>总览仪表盘</h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>跨模块执行结果聚合</p>

      {/* ===== 统计卡片 ===== */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
          gap: 16,
          marginBottom: 32,
        }}
      >
        <StatCard title="API 自动化" stat={apiStat} />
        <StatCard title="UI 自动化" stat={uiStat} />
        <SimpleCard
          title="测试用例"
          main={data.testcases.total}
          sub={Object.entries(tcByResult)
            .map(([k, v]) => `${RESULT_LABEL[k] ?? k} ${v}`)
            .join(' · ')}
        />
        <SimpleCard
          title="性能监控"
          main={data.monitoring.total_sessions}
          sub={`活跃 ${data.monitoring.active_sessions}`}
        />
      </div>

      {/* ===== 最近执行列表 ===== */}
      <section>
        <h3 style={{ color: "var(--accent)" }}>最近执行</h3>
        {data.executions.length === 0 ? (
          <p style={{ color: "var(--text-muted)" }}>暂无执行记录</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--bg-elevated)', color: "var(--text-secondary)", textAlign: 'left' }}>
                <th style={th}>模块</th>
                <th style={th}>用例</th>
                <th style={th}>状态</th>
                <th style={th}>步骤</th>
                <th style={th}>耗时</th>
                <th style={th}>时间</th>
              </tr>
            </thead>
            <tbody>
              {data.executions.map((e, i) => (
                <tr key={`${e.module}-${e.id}-${i}`} style={{ borderBottom: '1px solid var(--bg-card)' }}>
                  <td style={td}>
                    <span style={moduleTag(e.module)}>{e.module.toUpperCase()}</span>
                  </td>
                  <td style={td}>{e.case_title ?? `#${e.case_id ?? e.id}`}</td>
                  <td style={{ ...td, color: STATUS_COLOR[e.status] ?? "var(--text-secondary)" }}>
                    {e.status}
                  </td>
                  <td style={td}>
                    {e.passed_steps != null && e.total_steps != null
                      ? `${e.passed_steps}/${e.total_steps}`
                      : '-'}
                  </td>
                  <td style={td}>{fmtDuration(e.duration_ms)}</td>
                  <td style={{ ...td, color: "var(--text-secondary)" }}>{fmtTime(e.started_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

const th: React.CSSProperties = { padding: '8px 10px', fontWeight: 500 };
const td: React.CSSProperties = { padding: '10px', color: "var(--text-secondary)" };

function StatCard({ title, stat }: { title: string; stat?: ModuleStat }) {
  if (!stat || stat.total === 0) {
    return <SimpleCard title={title} main="—" sub="暂无执行" />;
  }
  const pct = Math.round(stat.pass_rate * 100);
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{title}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, margin: '8px 0' }}>
        <span style={{ fontSize: 28, fontWeight: 600, color: pct >= 80 ? 'var(--chart-4)' : pct >= 50 ? 'var(--chart-3)' : "var(--error)" }}>
          {pct}%
        </span>
        <span style={{ fontSize: 12, color: "var(--text-muted)" }}>通过率</span>
      </div>
      <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
        {stat.passed}/{stat.total} · 均 {fmtDuration(stat.avg_duration_ms)}
      </div>
      {/* 通过率条 */}
      <div style={{ height: 4, background: "var(--bg-card)", borderRadius: 2, marginTop: 8, overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            background: pct >= 80 ? 'var(--chart-4)' : pct >= 50 ? 'var(--chart-3)' : "var(--error)",
          }}
        />
      </div>
    </div>
  );
}

function SimpleCard({ title, main, sub }: { title: string; main: React.ReactNode; sub?: string }) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{title}</div>
      <div style={{ fontSize: 28, fontWeight: 600, margin: '8px 0' }}>{main}</div>
      {sub && <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{sub}</div>}
    </div>
  );
}

const cardStyle: React.CSSProperties = {
  background: "var(--bg-card)",
  border: '1px solid var(--bg-card)',
  borderRadius: 8,
  padding: 16,
};

function moduleTag(m: string): React.CSSProperties {
  const color = m === 'api' ? "var(--accent)" : 'var(--chart-2)';
  return {
    color,
    border: `1px solid ${color}40`,
    background: `${color}14`,
    borderRadius: 4,
    padding: '2px 6px',
    fontSize: 11,
  };
}

function fmtDuration(ms?: number): string {
  if (ms == null) return '-';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function fmtTime(s?: string): string {
  if (!s) return '-';
  try {
    const d = new Date(s);
    return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch {
    return s;
  }
}
