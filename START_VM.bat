@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ======================================================
echo   MGC Languages - Test VM CPU-only / no AI
echo ======================================================

where powershell.exe >nul 2>nul
if errorlevel 1 (
  echo [NO-GO] PowerShell is not available.
  pause
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-vm.ps1"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [NO-GO] VM startup failed. See the message above.
  pause
  exit /b %RC%
)

echo.
echo [GO] MGC Languages VM is ready.
pause
exit /b 0
