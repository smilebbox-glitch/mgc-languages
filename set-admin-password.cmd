@echo off
setlocal
cd /d "%~dp0"
echo MGC Languages - change admin password
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\set_admin_password_windows.ps1"
if errorlevel 1 (
  echo.
  echo Admin password update failed. See the error above.
  pause
  exit /b 1
)
echo.
pause
