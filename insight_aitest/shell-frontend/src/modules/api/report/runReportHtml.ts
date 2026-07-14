/**
 * API 自动化测试报告（HTML，前端生成）。
 *
 * 复用现有「Blob + <a download>」下载范式（见 shared/api/htmlExporter.ts），
 * 但报告模板是 API 模块专用（逐步断言明细表），不耦合性能模块的 ECharts 图表。
 * 报告为自包含 HTML：内联 CSS、暗色 neon 风格、离线可看、单文件可分享。
 */
import type { RunDetail, StepResult } from '../store/runStore'
import type { SuiteRunDetail } from '../store/suiteStore'

// ===== 下载（与现有 htmlExporter.downloadHtmlFile 同款，内联以保持模块自洽） =====
function downloadHtml(content: string, filename: string): void {
  const blob = new Blob([content], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const STATUS_COLOR: Record<string, string> = {
  passed: '#22c55e', failed: '#f87171', error: '#fbbf24',
  completed: '#22c55e', interrupted: '#fbbf24', running: '#00e5ff',
}
const STATUS_LABEL: Record<string, string> = {
  passed: '✓ 通过', failed: '✗ 失败', error: '⚠ 异常',
  completed: '✓ 完成', failed_suite: '✗ 失败', interrupted: '⚠ 中断', running: '… 运行中',
}

function esc(s: unknown): string {
  if (s === null || s === undefined) return ''
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function fmtTime(iso: string | null | undefined): string {
  if (!iso) return '-'
  try { return new Date(iso).toLocaleString() } catch { return iso }
}

function fmtBody(body: unknown): string {
  if (body === null || body === undefined || body === '') return ''
  try {
    return typeof body === 'string' ? body : JSON.stringify(body, null, 2)
  } catch {
    return String(body)
  }
}

// ===== 单步渲染 =====
function renderStep(step: StepResult, idx: number): string {
  const code = step.status_code ?? '—'
  const stepColor = step.passed ? '#22c55e' : '#f87171'
  const assertRows = (step.assertions || []).map((a) => `
      <tr>
        <td class="mono">${esc(a.type)}</td>
        <td class="mono">${esc(a.target)}</td>
        <td class="mono">${esc(a.expected)}</td>
        <td class="mono">${esc(a.actual)}</td>
        <td class="${a.passed ? 'ok' : 'bad'}">${a.passed ? '✓' : '✗'}</td>
      </tr>`).join('') || '<tr><td colspan="5" class="muted">（无断言）</td></tr>'

  const errBlock = step.error
    ? `<div class="err">⚠ ${esc(step.error)}</div>` : ''

  const reqBody = fmtBody(step.request.body)
  const resBody = fmtBody(step.response_body)

  return `
    <div class="step">
      <div class="step-head">
        <span class="badge" style="background:${stepColor}22;color:${stepColor}">步骤 ${idx + 1}</span>
        <span class="mono method">${esc(step.request.method)}</span>
        <span class="mono url">${esc(step.request.url)}</span>
        <span class="badge" style="background:#222;color:#9CA3AF">HTTP ${esc(code)}</span>
        <span class="muted">${esc(step.elapsed_ms)} ms</span>
      </div>
      ${errBlock}
      <div class="cols">
        <div class="col">
          <div class="col-title">请求体</div>
          <pre class="code">${esc(reqBody) || '<span class="muted">（空）</span>'}</pre>
        </div>
        <div class="col">
          <div class="col-title">响应体${step.response_body && fmtBody(step.response_body).length > 60000 ? ' <span class="muted">(已截断)</span>' : ''}</div>
          <pre class="code">${esc(resBody) || '<span class="muted">（空）</span>'}</pre>
        </div>
      </div>
      ${step.extracts && Object.keys(step.extracts).length
        ? `<div class="extracts"><span class="muted">提取变量：</span>${Object.entries(step.extracts).map(([k, v]) => `<span class="kv"><b>${esc(k)}</b>=${esc(v)}</span>`).join(' ')}</div>` : ''}
      <table class="assert">
        <thead><tr><th>类型</th><th>目标/路径</th><th>期望</th><th>实际</th><th>结果</th></tr></thead>
        <tbody>${assertRows}</tbody>
      </table>
    </div>`
}

// ===== 报告 HTML 外壳 =====
function shell(title: string, body: string): string {
  const now = new Date().toLocaleString()
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #0a0a0a; color: #e0e0e0;
    font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; font-size: 13px; line-height: 1.6; }
  .wrap { max-width: 1100px; margin: 0 auto; padding: 32px 24px 64px; }
  h1 { font-size: 22px; margin: 0 0 4px; color: #fff; }
  h2 { font-size: 15px; margin: 28px 0 12px; color: #9CA3AF; font-weight: 600;
    border-left: 3px solid #00e5ff; padding-left: 8px; }
  .muted { color: #6b7280; }
  .mono { font-family: "JetBrains Mono", "Cascadia Code", Consolas, monospace; }
  .meta { color: #6b7280; font-size: 12px; margin-bottom: 20px; }
  .summary { display: flex; gap: 12px; flex-wrap: wrap; margin: 16px 0 8px; }
  .stat { background: #141414; border: 1px solid #1f1f1f; border-radius: 8px;
    padding: 12px 16px; min-width: 110px; }
  .stat .n { font-size: 22px; font-weight: 700; }
  .stat .l { font-size: 11px; color: #6b7280; margin-top: 2px; }
  .status-big { display: inline-block; padding: 4px 12px; border-radius: 6px;
    font-weight: 700; font-size: 14px; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
  .step { background: #111; border: 1px solid #1f1f1f; border-radius: 8px;
    padding: 14px; margin-bottom: 14px; }
  .step-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
  .method { color: #00e5ff; font-weight: 700; }
  .url { color: #ccc; word-break: break-all; flex: 1; }
  .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 10px 0; }
  .col-title { font-size: 11px; color: #6b7280; margin-bottom: 4px; }
  .code { background: #0a0a0a; border: 1px solid #1a1a1a; border-radius: 6px;
    padding: 10px; margin: 0; max-height: 280px; overflow: auto; white-space: pre-wrap;
    word-break: break-all; font-size: 12px; }
  .extracts { font-size: 12px; margin: 8px 0; }
  .kv { display: inline-block; background: #1a1a1a; border-radius: 4px; padding: 2px 6px; margin: 2px 4px 2px 0; }
  .err { background: #3a1a1a; border: 1px solid #5a2a2a; color: #fca5a5;
    border-radius: 6px; padding: 8px 10px; margin: 8px 0; font-size: 12px; }
  table.assert { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }
  table.assert th { text-align: left; color: #6b7280; font-weight: 600;
    padding: 6px 8px; border-bottom: 1px solid #1f1f1f; }
  table.assert td { padding: 6px 8px; border-bottom: 1px solid #161616; vertical-align: top; }
  .ok { color: #22c55e; font-weight: 700; }
  .bad { color: #f87171; font-weight: 700; }
  .case-row { display: flex; align-items: center; gap: 10px; padding: 8px 12px;
    background: #111; border: 1px solid #1f1f1f; border-radius: 6px; margin-bottom: 6px; }
  footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #1f1f1f;
    color: #4b5563; font-size: 11px; }
  @media (max-width: 720px) { .cols { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="wrap">
${body}
<footer>由 Insight-AITest v2.0.0 API 自动化模块生成 · ${esc(now)}</footer>
</div>
</body>
</html>`
}

// ===== 单次执行报告 =====
export function exportRunHtmlReport(run: RunDetail): void {
  const color = STATUS_COLOR[run.status] ?? '#9CA3AF'
  const label = STATUS_LABEL[run.status] ?? run.status
  const passRate = run.total_steps > 0
    ? Math.round((run.passed_steps / run.total_steps) * 100) : 0

  const body = `
    <h1>${esc(run.case_title)}</h1>
    <div class="meta">用例 #${esc(run.case_id)} · 执行 #${esc(run.id)} · 开始 ${fmtTime(run.started_at)} · 耗时 ${esc(run.duration_ms)} ms</div>
    <div><span class="status-big" style="background:${color}22;color:${color}">${label}</span></div>
    <div class="summary">
      <div class="stat"><div class="n" style="color:${color}">${esc(run.passed_steps)}/${esc(run.total_steps)}</div><div class="l">步骤通过</div></div>
      <div class="stat"><div class="n">${esc(passRate)}%</div><div class="l">通过率</div></div>
      <div class="stat"><div class="n">${esc(run.duration_ms)}</div><div class="l">耗时(ms)</div></div>
    </div>
    <h2>逐步明细</h2>
    ${(run.steps || []).map((s, i) => renderStep(s, i)).join('') || '<div class="muted">（无步骤）</div>'}`

  const html = shell(`API 报告 · ${run.case_title}`, body)
  downloadHtml(html, `API报告-${run.case_title}-run${run.id}.html`)
}

// ===== 套件执行报告（聚合 child runs） =====
export function exportSuiteHtmlReport(
  suiteRun: SuiteRunDetail,
  childRuns: RunDetail[],
): void {
  const color = STATUS_COLOR[suiteRun.status] ?? '#9CA3AF'
  const label = STATUS_LABEL[suiteRun.status] ?? suiteRun.status
  const totalSteps = childRuns.reduce((a, r) => a + (r.total_steps || 0), 0)
  const passedSteps = childRuns.reduce((a, r) => a + (r.passed_steps || 0), 0)
  const passRate = totalSteps > 0 ? Math.round((passedSteps / totalSteps) * 100) : 0
  const passedCases = childRuns.filter((r) => r.status === 'passed').length

  const caseRows = childRuns.map((r) => {
    const c = STATUS_COLOR[r.status] ?? '#9CA3AF'
    return `<div class="case-row">
      <span style="color:${c};font-weight:700;width:18px">${r.status === 'passed' ? '✓' : '✗'}</span>
      <span style="flex:1">${esc(r.case_title)} <span class="muted">#${esc(r.id)}</span></span>
      <span class="muted">${esc(r.passed_steps)}/${esc(r.total_steps)} 步 · ${esc(r.duration_ms)}ms</span>
    </div>`
  }).join('') || '<div class="muted">（无 case 执行记录）</div>'

  // 逐步明细：每个 case 一个小节
  const stepSections = childRuns.map((r) => {
    const c = STATUS_COLOR[r.status] ?? '#9CA3AF'
    return `<h2 style="border-left-color:${c}">${esc(r.case_title)} <span class="muted" style="font-weight:400">· ${esc(r.passed_steps)}/${esc(r.total_steps)}</span></h2>
    ${(r.steps || []).map((s, i) => renderStep(s, i)).join('') || '<div class="muted">（无步骤）</div>'}`
  }).join('')

  const body = `
    <h1>套件报告 · ${esc(suiteRun.suite_name)}</h1>
    <div class="meta">套件执行 #${esc(suiteRun.id)} · 环境 ${esc(suiteRun.environment_name || '默认')} · 开始 ${fmtTime(suiteRun.started_at)} · setup ${esc(suiteRun.setup_status || '无')}</div>
    ${suiteRun.error ? `<div class="err">⚠ ${esc(suiteRun.error)}</div>` : ''}
    <div><span class="status-big" style="background:${color}22;color:${color}">${label}</span></div>
    <div class="summary">
      <div class="stat"><div class="n" style="color:${color}">${esc(passedCases)}/${esc(childRuns.length)}</div><div class="l">用例通过</div></div>
      <div class="stat"><div class="n">${esc(passedSteps)}/${esc(totalSteps)}</div><div class="l">步骤通过</div></div>
      <div class="stat"><div class="n">${esc(passRate)}%</div><div class="l">总通过率</div></div>
    </div>
    <h2>用例汇总</h2>
    ${caseRows}
    <h2>逐步明细</h2>
    ${stepSections || '<div class="muted">（无步骤数据——child runs 未加载）</div>'}`

  const html = shell(`套件报告 · ${suiteRun.suite_name}`, body)
  downloadHtml(html, `套件报告-${suiteRun.suite_name}-run${suiteRun.id}.html`)
}
