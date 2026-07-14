@echo off
REM 启动平台后端并指向本地 mock LLM（无需真实 API key）。
REM 用法：双击或在终端运行 scripts\run_ai_mock.bat
set INSIGHT_EYE_AI_LLM_BASE_URL=http://127.0.0.1:8088/v1
set INSIGHT_EYE_AI_LLM_API_KEY=mock-key
set INSIGHT_EYE_AI_EMBED_DIM=8
echo [run_ai_mock] 平台后端启动，LLM 指向 mock (http://127.0.0.1:8088/v1)
py -m insight_aitest
