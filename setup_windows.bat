@echo off
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3.12 -m venv .venv
) else (
  python -m venv .venv
)

.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m playwright install chromium

if not exist .env copy .env.example .env
if not exist logs mkdir logs
if not exist screenshots mkdir screenshots

echo Windows setup completed.
