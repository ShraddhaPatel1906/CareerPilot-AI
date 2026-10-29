@echo off
cd /d "%~dp0"
chcp 65001 >nul
echo Starting CareerPilot AI at http://127.0.0.1:8080
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run_server.py
) else (
    python run_server.py
)
pause
