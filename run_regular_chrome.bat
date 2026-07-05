@echo off
cd /d "%~dp0"
findstr /R "^CAPTIVE_ENTRY_URL=.$ ^CAPTIVE_ENTRY_URL=http" .env >nul 2>nul
if errorlevel 1 (
  echo CAPTIVE_ENTRY_URL is not configured.
  echo Edit .env and set CAPTIVE_ENTRY_URL to a URL that you confirmed opens the login page in regular Chrome.
  exit /b 1
)
.venv\Scripts\python.exe open_regular_chrome.py entry
