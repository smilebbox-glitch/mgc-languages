@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ======================================================
echo   MGC Language Lab - Company Pilot Launcher v6.0.17
echo ======================================================
echo.

where powershell.exe >nul 2>nul
if errorlevel 1 (
  echo [NO-GO] PowerShell is not available on this Windows PC.
  pause
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_company_pilot.ps1"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo [NO-GO] Pilot launcher stopped with code %RC%.
  echo Read the message above, correct the configuration, and run this file again.
  pause
  exit /b %RC%
)

echo.
echo [GO] MGC Language Lab company pilot is running.
pause
exit /b 0
