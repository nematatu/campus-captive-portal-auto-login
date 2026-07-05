@echo off
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
  echo .venv was not found. Running setup_windows.bat...
  call setup_windows.bat
  if errorlevel 1 exit /b %errorlevel%
)

.venv\Scripts\python.exe -c "import pyautogui, pyperclip" >nul 2>nul
if errorlevel 1 (
  echo pyautogui or pyperclip was not found. Installing requirements...
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 exit /b %errorlevel%
)

.venv\Scripts\python.exe auto_type_real_browser_windows.py %*
