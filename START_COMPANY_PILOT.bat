@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ======================================================
echo   MGC Language Lab - Pilot Launcher v6.0.17
echo ======================================================
echo.

where git >nul 2>nul
if "%ERRORLEVEL%"=="0" if exist ".git" (
  echo Updating project from GitHub...
  git pull --ff-only origin main
  if not "%ERRORLEVEL%"=="0" echo WARNING: Git update was skipped. Starting current local copy.
  echo.
)

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
echo [GO] MGC Language Lab pilot launcher completed successfully.
pause
exit /b 0
