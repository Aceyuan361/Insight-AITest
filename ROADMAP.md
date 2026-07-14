# Roadmap

> Last updated: 2026-07-14 · Branch: `2.0.0`

Insight-AITest v2.0.0 is built as six subsystems (A–F). All six are complete in code
and tests. This document tracks their status and the deferred (YAGNI) work.

## Status overview

```
A  平台外壳 + 模块系统          Platform Shell + Module System      100% ✅
B  性能模块化                  Performance Module                   100% ✅
C  AI Agent + 本地知识库        AI Agent + Local Knowledge Base      100% ✅
D  测试用例生成                Test Case Generation                 100% ✅
E  API 自动化（+ E.1）          API Automation (+ suites/env)        100% ✅
F  UI 自动化（Midscene）        UI Automation (Midscene)             100% ✅（首版）
```

**v2.0.0 六大模块全部完成。**

Test baseline: `python -m pytest tests/ -q` → **719 passed, 1 skipped** (zero regressions).

## Subsystem detail

### A — Platform Shell + Module System ✅
Kernel scans `modules/*/manifest.yaml`, validates, topo-sorts, and registers
each module's router. Shared frontend shell renders modules via `module-map.ts`.
- `platform/kernel.py`, `platform/module_registry.py`, `platform/api/platform.py`
- Frontend: `shell/` (AppShell, TopBar, SideNav, Dashboard), `routing.tsx`

### B — Performance Module ✅
v1.0.0 performance features repackaged as the first pluggable module.
- Real-time metrics over WebSocket, device/app management, alert rules.
- Android (ADB) + iOS (pymobiledevice3).
- `modules/performance/`, frontend `/performance`.

### C — AI Assistant + Local Knowledge Base ✅
RAG chat grounded in uploaded documents; embeddings stored locally.
- Shared `LLMConfig` (chat/embedding models) under `platform/services/llm/`.
- `modules/ai/`, frontend `/ai`.

### D — Test Case Generation ✅
AI analyzes scenarios, selects test points, generates structured cases for review.
- Generated cases feed E and F.
- `modules/testcase/`, frontend `/testcase`.

### E — API Automation (+ E.1) ✅
Multi-step HTTP cases with assertions, `{{variable}}` chaining, history & stats.
- **E.1**: environments (configurable `base_url`) + suites (batch execution).
- `modules/api/`, frontend `/api-runner`.

### F — UI Automation (Midscene) ✅ (first version)
Vision-driven browser automation via PyMidscene + Playwright.
- Step normalization (`{action,target,value}` → natural-language sentence).
- Three kinds → three methods: `action`→`aiAction`, `assert`→`aiAssert`, `extract`→`aiQuery`.
- Per-step screenshots saved to disk (not DB); `error` doesn't abort later steps (mirrors E).
- `agent_factory(page)` injection point: real `PlaywrightAgent` in prod, `FakeAgent` in tests.
- `LLMConfig.vision_model` (falls back to `chat_model` for C/D compatibility).
- `modules/ui/`, frontend `/ui-runner`.
- **Tests:** 30 (executor 14, database 6, llm_config 2, runs_api 8).

## Deferred work (YAGNI — F.2 and later)

Not built in the first version; revisit on demand:

- **UI suite orchestration** — UI runs are slow; batch value is low. E's suites are not reused for F.
- **Environment management UI** — handled lightweightly via `?base_url=` override; no `environments` table for F.
- **Midscene bridge mode** / reuse the user's open browser — PyMidscene side not yet mature.
- **Mobile UI** (iOS / Android automation) — first version is Web only.
- **Visual regression** (screenshot diffing), recorder, retry/parallel execution,
  WebSocket live push, video recording.

## Notes

- UI Automation (F) end-to-end prerequisite: set a vision model (`INSIGHT_EYE_AI_VISION_MODEL`)
  with a valid API key, then `playwright install chromium`.
