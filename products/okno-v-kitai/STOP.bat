@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\one-click-stop.ps1"
if not "%ERRORLEVEL%"=="0" pause
