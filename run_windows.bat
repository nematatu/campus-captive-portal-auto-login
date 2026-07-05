@echo off
cd /d "%~dp0"
echo DISABLED: This runner is disabled to prevent further captive portal state changes.
echo Do not run login automation until the network state is recovered and the portal flow is understood.
exit /b 1
