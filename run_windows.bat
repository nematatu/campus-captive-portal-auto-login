@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe captive_login.py --windows-manual %*
