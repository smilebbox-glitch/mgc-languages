@echo off
setlocal
cd /d "%~dp0"
if not exist ".env.lan" (
  echo .env.lan not found. Nothing to stop.
  pause
  exit /b 0
)
docker compose --env-file .env.lan -f docker-compose.lan.yml down
if errorlevel 1 (
  echo Failed to stop MGC Languages LAN.
  pause
  exit /b 1
)
echo MGC Languages LAN stopped. PostgreSQL data volume was preserved.
pause
