@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -c "import sys; print(sys.version)" >nul 2>nul
  if %errorlevel%==0 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
  where python >nul 2>nul
  if %errorlevel%==0 (
    python -c "import sys; print(sys.version)" >nul 2>nul
    if %errorlevel%==0 set "PYTHON_CMD=python"
  )
)

if not defined PYTHON_CMD (
  where python3 >nul 2>nul
  if %errorlevel%==0 (
    python3 -c "import sys; print(sys.version)" >nul 2>nul
    if %errorlevel%==0 set "PYTHON_CMD=python3"
  )
)

if not defined PYTHON_CMD (
  echo Python was not found.
  echo Install Python 3.10 or newer from https://www.python.org/downloads/windows/ or Microsoft Store.
  echo After installation, reopen the terminal and run setup_windows.bat again.
  exit /b 1
)

echo Using Python command: %PYTHON_CMD%
%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if not %errorlevel%==0 (
  echo Python 3.10 or newer is required.
  %PYTHON_CMD% --version
  exit /b 1
)

if not exist .venv\Scripts\python.exe (
  %PYTHON_CMD% -m venv .venv
  if not %errorlevel%==0 exit /b %errorlevel%
)

.venv\Scripts\python.exe -m pip install --upgrade pip
if not %errorlevel%==0 exit /b %errorlevel%

.venv\Scripts\python.exe -m pip install -r requirements.txt
if not %errorlevel%==0 exit /b %errorlevel%

.venv\Scripts\python.exe -m playwright install chromium
if not %errorlevel%==0 exit /b %errorlevel%

if not exist .env copy .env.example .env
if not exist logs mkdir logs
if not exist screenshots mkdir screenshots

echo Windows setup completed.
