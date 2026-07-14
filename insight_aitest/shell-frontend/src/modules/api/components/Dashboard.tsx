import { useEffect, useState } from 'react'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { CheckCircle, XCircle, AlertCircle, Clock, TrendingUp } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface Stats {
  total: number
  passed: number
  failed: number
  error: number
  last_run_at: string | null
  last_status: string | null
  avg_duration_ms: number
  pass_rate: number
  trend: { date: string; total: number; passed: number; failed: number; error: number; pass_rate: number }[]
  top_failures: { case_title: string; case_id: number; failed: number; error: number; total: number }[]
}

export function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const { t } = useTranslation()

  useEffect(() => {
    let cancelled = false
    fetch('/api/modules/api/runs/stats?limit=1000')
      .then((r) => r.json())
      .then((data: any) => {
        if (cancelled) return
        // 防御性：后端可能未返回新字段（旧版本兼容）
        setStats({
          total: data.total ?? 0,
          passed: data.passed ?? 0,
          failed: data.failed ?? 0,
          error: data.error ?? 0,
          last_run_at: data.last_run_at ?? null,
          last_status: data.last_status ?? null,
          avg_duration_ms: data.avg_duration_ms ?? 0,
          pass_rate: data.pass_rate ?? 0,
          trend: data.trend ?? [],
          top_failures: data.top_failures ?? [],
        })
      })
      .catch((e) => console.error('Dashboard load failed:', e))
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  if (loading) return <div style={{ padding: 24, color: 'var(--text-muted)', fontSize: 13 }}>{t('api.loading')}</div>
  if (!stats) return <div style={{ padding: 24, color: 'var(--text-muted)', fontSize: 13 }}>{t('api.noData')}</div>

  return (
    <div style={{ flex: 1, height: '100%', overflow: 'auto', padding: 16, color: "var(--text-primary)" }}>
      {/* 数字卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginBottom: 20 }}>
        <StatCard icon={<TrendingUp size={18} />} label={t('api.totalRuns')} value={stats.total} color="var(--accent)" />
        <StatCard icon={<CheckCircle size={18} />} label={t('api.passRate')} value={`${stats.pass_rate}%`} color="var(--success)" sub={`${stats.passed} passed`} />
        <StatCard icon={<XCircle size={18} />} label={t('api.failed')} value={stats.failed} color="var(--error)" />
        <StatCard icon={<AlertCircle size={18} />} label={t('api.error')} value={stats.error} color="var(--chart-3)" />
        <StatCard icon={<Clock size={18} />} label={t('api.avgDuration')} value={`${stats.avg_duration_ms}ms`} color="var(--chart-4)" />
      </div>

      {/* 趋势图 */}
      <div style={{ background: 'var(--bg-card)', borderRadius: 8, padding: 16, marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, marginTop: 0, marginBottom: 12, color: "var(--text-primary)" }}>
          {t('api.trend30Days')}
        </h3>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={stats.trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-strong)" opacity={0.3} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} interval={4} />
            <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
            <Tooltip
              contentStyle={{ background: 'var(--bg-base)', border: '1px solid var(--border-strong)', borderRadius: 6, fontSize: 12 }}
              labelStyle={{ color: 'var(--text-primary)' }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Line type="monotone" dataKey="total" stroke="var(--accent)" strokeWidth={2} name={t('api.totalRuns')} dot={false} />
            <Line type="monotone" dataKey="passed" stroke="var(--success)" strokeWidth={2} name={t('api.passed')} dot={false} />
            <Line type="monotone" dataKey="failed" stroke="var(--error)" strokeWidth={2} name={t('api.failed')} dot={false} />
            <Line type="monotone" dataKey="error" stroke="var(--chart-3)" strokeWidth={1.5} name={t('api.error')} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 通过率折线图 */}
      <div style={{ background: 'var(--bg-card)', borderRadius: 8, padding: 16, marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, marginTop: 0, marginBottom: 12, color: "var(--text-primary)" }}>
          {t('api.passRateTrend')}
        </h3>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={stats.trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-strong)" opacity={0.3} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} interval={4} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
            <Tooltip
              contentStyle={{ background: 'var(--bg-base)', border: '1px solid var(--border-strong)', borderRadius: 6, fontSize: 12 }}
              formatter={(v: any) => `${v}%`}
            />
            <Line type="monotone" dataKey="pass_rate" stroke="var(--success)" strokeWidth={2} name={t('api.passRate')} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 失败 TOP5 */}
      {stats.top_failures.length > 0 && (
        <div style={{ background: 'var(--bg-card)', borderRadius: 8, padding: 16 }}>
          <h3 style={{ fontSize: 14, marginTop: 0, marginBottom: 12, color: "var(--text-primary)" }}>
            {t('api.topFailures')}
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={stats.top_failures} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-strong)" opacity={0.3} />
              <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
              <YAxis type="category" dataKey="case_title" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} width={120} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-base)', border: '1px solid var(--border-strong)', borderRadius: 6, fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="failed" stackId="a" fill="var(--error)" name={t('api.failed')} />
              <Bar dataKey="error" stackId="a" fill="var(--chart-3)" name={t('api.error')} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

function StatCard({ icon, label, value, color, sub }: {
  icon: React.ReactNode; label: string; value: string | number; color: string; sub?: string
}) {
  return (
    <div style={{ background: 'var(--bg-card)', borderRadius: 8, padding: 14, display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: 11 }}>
        <span style={{ color }}>{icon}</span>
        {label}
      </div>
      <div style={{ fontSize: 24, fontWeight: 700, color }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{sub}</div>}
    </div>
  )
}
