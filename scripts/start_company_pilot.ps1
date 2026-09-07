$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Stop-NoGo([string]$Message, [int]$Code = 1) {
    Write-Host "[NO-GO] $Message" -ForegroundColor Red
    exit $Code
}

Write-Host "MGC Language Lab - Company Pilot v6.0.17" -ForegroundColor Cyan
Write-Host "Working directory: $Root"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Stop-NoGo "Docker CLI is not installed or not in PATH. Install/start Docker Desktop first." 10
}

try {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) { throw 'docker info failed' }
} catch {
    Stop-NoGo "Docker engine is not running. Start Docker Desktop and run START_COMPANY_PILOT.bat again." 11
}

try {
    docker compose version *> $null
    if ($LASTEXITCODE -ne 0) { throw 'docker compose unavailable' }
} catch {
    Stop-NoGo "Docker Compose v2 is unavailable." 12
}

$EnvFile = Join-Path $Root '.env.pilot'
$Template = Join-Path $Root '.env.company-pilot.example'
if (-not (Test-Path $EnvFile)) {
    if (-not (Test-Path $Template)) { Stop-NoGo "Missing .env.company-pilot.example." 13 }
    Copy-Item $Template $EnvFile
    Write-Host ""
    Write-Host "[FIRST RUN] Created .env.pilot from the secure company template." -ForegroundColor Yellow
    Write-Host "IT must fill real corporate values once: passwords, OIDC/SSO, DNS/hosts and secrets." -ForegroundColor Yellow
    Start-Process notepad.exe $EnvFile
    Stop-NoGo "First-time configuration is required. Save .env.pilot, then double-click START_COMPANY_PILOT.bat again." 14
}

Write-Host "[1/5] Running company pilot preflight..." -ForegroundColor Cyan
python "$Root\scripts\company_pilot_preflight.py" --env-file $EnvFile --strict-corporate
if ($LASTEXITCODE -ne 0) { Stop-NoGo "Strict corporate preflight did not return GO." 20 }

Write-Host "[2/5] Building pilot containers..." -ForegroundColor Cyan
docker compose --env-file $EnvFile -f "$Root\docker-compose.pilot.yml" build
if ($LASTEXITCODE -ne 0) { Stop-NoGo "Docker build failed." 21 }

Write-Host "[3/5] Starting pilot stack..." -ForegroundColor Cyan
docker compose --env-file $EnvFile -f "$Root\docker-compose.pilot.yml" up -d
if ($LASTEXITCODE -ne 0) { Stop-NoGo "Docker compose up failed." 22 }

$Port = '8080'
Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*MGC_PORT\s*=\s*(\d+)\s*$') { $script:Port = $Matches[1] }
}
$Url = "http://127.0.0.1:$Port"

Write-Host "[4/5] Waiting for readiness..." -ForegroundColor Cyan
$Ready = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri "$Url/health/ready" -TimeoutSec 3
        if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 300) { $Ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 2
}
if (-not $Ready) {
    docker compose --env-file $EnvFile -f "$Root\docker-compose.pilot.yml" ps
    Stop-NoGo "Service did not become ready within 60 seconds. Check container logs." 23
}

Write-Host "[5/5] Runtime validation..." -ForegroundColor Cyan
python "$Root\scripts\company_pilot_preflight.py" --env-file $EnvFile --url $Url
if ($LASTEXITCODE -ne 0) { Stop-NoGo "Runtime validation failed." 24 }

Write-Host "[GO] Pilot is healthy: $Url" -ForegroundColor Green
Start-Process $Url
exit 0
