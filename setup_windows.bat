@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_CMD="

call :resolve_python
if not defined PYTHON_CMD (
  call :install_python
  call :resolve_python
)

if not defined PYTHON_CMD (
  echo Failed to find or install Python 3.10 or newer.
  echo Install Python manually, reopen the terminal, then run setup_windows.bat again.
  exit /b 1
)

echo Using Python command: %PYTHON_CMD%

if not exist .venv\Scripts\python.exe (
  echo Creating virtual environment: .venv
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 exit /b %errorlevel%
)

echo Installing Python dependencies
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 exit /b %errorlevel%

.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 exit /b %errorlevel%

echo Installing Playwright Chromium
.venv\Scripts\python.exe -m playwright install chromium
if errorlevel 1 exit /b %errorlevel%

if not exist .env copy .env.example .env
if not exist logs mkdir logs
if not exist screenshots mkdir screenshots

echo Windows setup completed.
exit /b 0

:resolve_python
set "PYTHON_CMD="
call :try_python "py -3"
if defined PYTHON_CMD exit /b 0
call :try_python "python"
if defined PYTHON_CMD exit /b 0
call :try_python "python3"
if defined PYTHON_CMD exit /b 0
exit /b 1

:try_python
set "CANDIDATE=%~1"
%CANDIDATE% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_CMD=%CANDIDATE%"
  exit /b 0
)
exit /b 1

:install_python
echo Python 3.10 or newer was not found.
echo Trying to install Python 3.12 with winget...
where winget >nul 2>nul
if errorlevel 1 (
  echo winget was not found. Cannot install Python automatically.
  exit /b 1
)

winget install --id Python.Python.3.12 --source winget --scope user --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
  echo winget Python install failed.
  exit /b 1
)

set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
echo Python install completed.
exit /b 0
