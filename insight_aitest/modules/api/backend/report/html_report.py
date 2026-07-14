# -*- coding: utf-8 -*-
"""API 执行 HTML 报告生成器（纯 Python，无外部依赖）。

消费 RunRecord + StepResult，输出自包含 HTML（内嵌 CSS，无外部资源）。
后续若需 Allure 可独立加，不冲突。
"""

from __future__ import annotations

import html
import json
from typing import Any

from insight_aitest.modules.api.backend.persistence.models import RunRecord, StepResult

_STATUS_LABEL = {"passed": "通过", "failed": "失败", "error": "错误"}
_STATUS_COLOR = {"passed": "#16a34a", "failed": "#dc2626", "error": "#ea580c"}

_CSS = """
body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 24px; background: #f8fafc; color: #1e293b; }
.card { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.1); padding: 20px; margin-bottom: 16px; }
h1 { margin: 0 0 8px; font-size: 22px; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 12px; color: #fff; font-size: 12px; font-weight: 600; }
.meta { display: flex; gap: 24px; margin-top: 12px; flex-wrap: wrap; }
.meta div { font-size: 13px; }
.meta b { color: #64748b; font-weight: 500; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #e2e8f0; }
th { color: #64748b; font-weight: 600; }
.step { margin-bottom: 12px; }
.step-head { font-weight: 600; margin-bottom: 6px; }
.assert-pass { color: #16a34a; }
.assert-fail { color: #dc2626; }
pre { background: #f1f5f9; padding: 10px; border-radius: 4px; font-size: 12px; overflow-x: auto; max-height: 240px; }
details { margin-top: 6px; }
summary { cursor: pointer; font-size: 13px; color: #64748b; }
"""


def _esc(v: Any) -> str:
    """HTML 转义防 XSS。"""
    return html.escape(str(v) if v is not None else "")


def _fmt_json(v: Any) -> str:
    """JSON 美化 + 转义。"""
    try:
        return _esc(json.dumps(v, ensure_ascii=False, indent=2, default=str))
    except (TypeError, ValueError):
        return _esc(str(v))


def _step_block(step: StepResult) -> str:
    req = step.request or {}
    method = _esc(req.get("method", ""))
    url = _esc(req.get("url", ""))
    assert_rows = []
    for a in step.assertions or []:
        cls = "assert-pass" if a.get("passed") else "assert-fail"
        mark = "✓" if a.get("passed") else "✗"
        assert_rows.append(
            f'<tr><td>{_esc(a.get("type", ""))}</td><td>{_esc(a.get("target", ""))}</td>'
            f'<td>{_esc(a.get("expected", ""))}</td><td>{_esc(a.get("actual", ""))}</td>'
            f'<td class="{cls}">{mark}</td></tr>'
        )
    assertions_html = (
        "<table><tr><th>类型</th><th>目标</th><th>期望</th><th>实际</th><th>结果</th></tr>"
        + "".join(assert_rows)
        + "</table>"
        if assert_rows
        else ""
    )
    error_html = (
        f'<div style="color:#dc2626;margin-top:6px;">错误: {_esc(step.error)}</div>'
        if step.error
        else ""
    )
    extracts_html = (
        f"<details><summary>提取变量</summary><pre>{_fmt_json(step.extracts)}</pre></details>"
        if step.extracts
        else ""
    )
    status_code = step.status_code if step.status_code is not None else "—"
    return f"""
    <div class="card step">
      <div class="step-head">步骤 {step.step_index + 1}: {method} {url}</div>
      <div class="meta">
        <div><b>状态码:</b> {_esc(status_code)}</div>
        <div><b>耗时:</b> {step.elapsed_ms}ms</div>
      </div>
      {assertions_html}
      {error_html}
      <details><summary>响应体</summary><pre>{_fmt_json(step.response_body)}</pre></details>
      {extracts_html}
    </div>
    """


def render_run_html(run: RunRecord) -> str:
    """渲染单次执行记录为自包含 HTML 字符串。"""
    status_val = run.status.value
    label = _STATUS_LABEL.get(status_val, status_val)
    color = _STATUS_COLOR.get(status_val, "#64748b")
    step_blocks = "".join(_step_block(s) for s in run.steps)
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>执行报告 - {_esc(run.case_title)}</title>
<style>{_CSS}</style></head><body>
<div class="card">
  <h1>{_esc(run.case_title)}</h1>
  <span class="badge" style="background:{color}">{label}</span>
  <div class="meta">
    <div><b>用例 ID:</b> {run.case_id}</div>
    <div><b>执行 ID:</b> {run.id}</div>
    <div><b>步骤:</b> {run.passed_steps}/{run.total_steps} 通过</div>
    <div><b>总耗时:</b> {run.duration_ms}ms</div>
    <div><b>开始:</b> {_esc(run.started_at)}</div>
  </div>
</div>
{step_blocks}
</body></html>"""


def render_suite_html(suite_run: dict, child_runs: list[RunRecord]) -> str:
    """渲染套件聚合 HTML 报告。

    suite_run: {id, suite_name, status, total, done, setup_status,
                environment_name, started_at, finished_at, error, case_run_ids}
    child_runs: list[RunRecord] — 每条 case 的执行明细
    """
    status_val = suite_run.get("status", "")
    label = _STATUS_LABEL.get(status_val, status_val)
    color = _STATUS_COLOR.get(status_val, "#64748b")

    total = suite_run.get("total", 0)
    passed_count = sum(1 for r in child_runs if r.status and r.status.value == "passed")
    failed_count = total - passed_count

    # 每个 case 的折叠明细
    case_blocks = []
    for r in child_runs:
        sv = r.status.value if r.status else "unknown"
        cl = _STATUS_COLOR.get(sv, "#64748b")
        step_blocks = "".join(_step_block(s) for s in r.steps)
        case_blocks.append(f"""
    <details class="card" style="border-left:4px solid {cl};">
      <summary style="font-weight:600;font-size:15px;cursor:pointer;">
        {_esc(r.case_title)}
        <span class="badge" style="background:{cl};margin-left:8px;">{_STATUS_LABEL.get(sv, sv)}</span>
        <span style="color:#64748b;font-weight:400;font-size:13px;margin-left:8px;">{r.passed_steps}/{r.total_steps} 步</span>
      </summary>
      {step_blocks}
    </details>""")

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>套件报告 - {_esc(suite_run.get('suite_name',''))}</title>
<style>{_CSS}</style></head><body>
<div class="card">
  <h1>套件报告: {_esc(suite_run.get('suite_name',''))}</h1>
  <span class="badge" style="background:{color}">{label}</span>
  <div class="meta">
    <div><b>套件执行 ID:</b> {suite_run.get('id','')}</div>
    <div><b>用例总数:</b> {total}</div>
    <div><b>通过:</b> {passed_count}</div>
    <div><b>失败:</b> {failed_count}</div>
    <div><b>Setup:</b> {_esc(suite_run.get('setup_status') or '无')}</div>
    <div><b>环境:</b> {_esc(suite_run.get('environment_name') or '默认')}</div>
    <div><b>开始:</b> {_esc(suite_run.get('started_at',''))}</div>
  </div>
</div>
{''.join(case_blocks)}
</body></html>"""


def render_junit_xml(suite_run: dict, child_runs: list[RunRecord]) -> str:
    """渲染 JUnit XML 报告（CI/CD 标准格式）。

    suite_run: 同 render_suite_html
    child_runs: list[RunRecord]
    """
    import xml.etree.ElementTree as ET

    total = suite_run.get("total", 0)
    failures = sum(1 for r in child_runs if r.status and r.status.value in ("failed", "error"))
    errors = sum(1 for r in child_runs if r.status and r.status.value == "error")
    total_time = sum((r.duration_ms or 0) for r in child_runs) / 1000.0

    ts = ET.Element("testsuite", {
        "name": suite_run.get("suite_name", ""),
        "tests": str(total),
        "failures": str(failures),
        "errors": str(errors),
        "time": f"{total_time:.3f}",
        "timestamp": str(suite_run.get("started_at", "")),
    })

    for r in child_runs:
        sv = r.status.value if r.status else "unknown"
        tc = ET.SubElement(ts, "testcase", {
            "name": r.case_title or f"case-{r.case_id}",
            "classname": suite_run.get("suite_name", ""),
            "time": f"{(r.duration_ms or 0) / 1000.0:.3f}",
        })
        if sv == "error":
            err_msg = ""
            for s in r.steps:
                if s.error:
                    err_msg = s.error
                    break
            ET.SubElement(tc, "error", {"message": err_msg or "执行错误"})
        elif sv == "failed":
            # 取第一个失败断言
            fail_msg = ""
            for s in r.steps:
                for a in (s.assertions or []):
                    if not a.get("passed"):
                        fail_msg = f"{a.get('type')} {a.get('target')}: expected={a.get('expected')} actual={a.get('actual')}"
                        break
                if fail_msg:
                    break
            ET.SubElement(tc, "failure", {"message": fail_msg or "断言失败"})
        elif sv == "passed":
            pass  # 通过的 testcase 不需要子元素

    _indent_xml(ts)
    xml_str = ET.tostring(ts, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'


def _indent_xml(elem: ET.Element, level: int = 0) -> None:
    """简单缩进 XML（Python 3.9+ 有 ET.indent，这里兼容写法）。"""
    indent = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        for child in elem:
            _indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent
        if not elem.tail or not elem.tail.strip():
            elem.tail = "\n" + "  " * (level - 1) if level > 0 else "\n"
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = "\n" + "  " * (level - 1)
