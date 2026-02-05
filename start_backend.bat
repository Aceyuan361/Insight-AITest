@echo off
cd /d C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye\insight_eye-1.0.0\.worktrees\1.0.3
.venv\Scripts\python.exe -m uvicorn insight_eyes.web.app:app --host 0.0.0.0 --port 8000 --reload >> backend.log 2>&1
