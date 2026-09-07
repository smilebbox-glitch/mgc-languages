@echo off
setlocal
cd /d "%~dp0"
echo Starting MGC Languages for local network users...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_lan_windows.ps1"
if errorlevel 1 (
  echo.
  echo Startup failed. See the error above.
  pause
  exit /b 1
)
echo.
echo MGC Languages LAN startup finished.
pause
