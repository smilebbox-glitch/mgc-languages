@echo off
setlocal
cd /d "%~dp0"
echo Starting Okno v Kitai Pilot...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\one-click-start.ps1"
set RC=%ERRORLEVEL%
if not "%RC%"=="0" (
  echo.
  echo Startup failed. See the message above.
  pause
  exit /b %RC%
)
echo.
echo Okno v Kitai is ready.
pause
