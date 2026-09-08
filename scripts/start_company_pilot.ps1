$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Stop-NoGo([string]$Message, [int]$Code = 1) {
    Write-Host "[NO-GO] $Message" -ForegroundColor Red
    exit $Code
}

function Write-Utf8NoBom([string]$Path, [string]$Text) {
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $encoding)
}

function New-Secret([int]$Bytes = 32) {
    $buffer = New-Object byte[] $Bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
    return ([Convert]::ToBase64String($buffer)).TrimEnd('=').Replace('+','-').Replace('/','_')
}

function Get-EnvValue([string]$Path, [string]$Key) {
    if (-not (Test-Path $Path)) { return '' }
    $line = Get-Content -LiteralPath $Path | Where-Object { $_ -match ('^\s*' + [Regex]::Escape($Key) + '\s*=') } | Select-Object -Last 1
    if (-not $line) { return '' }
    return (($line -split '=', 2)[1]).Trim().Trim('"').Trim("'")
}

function Set-EnvValue([string]$Path, [string]$Key, [string]$Value) {
    $text = if (Test-Path $Path) { Get-Content -LiteralPath $Path -Raw } else { '' }
    $pattern = '(?m)^\s*' + [Regex]::Escape($Key) + '\s*=.*$'
    $line = "$Key=$Value"
    if ([Regex]::IsMatch($text, $pattern)) {
        $text = [Regex]::Replace($text, $pattern, $line)
    } else {
        if ($text.Length -gt 0 -and -not $text.EndsWith("`n")) { $text += "`r`n" }
        $text += "$line`r`n"
    }
    Write-Utf8NoBom $Path $text
}

function Test-Placeholder([string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value)) { return $true }
    return $Value -match '(?i)CHANGE_ME|changeme|replace-me|example'
}

function Ensure-Secret([string]$Path, [string]$Key, [int]$Bytes = 32) {
    $current = Get-EnvValue $Path $Key
    if (Test-Placeholder $current) {
        Set-EnvValue $Path $Key (New-Secret $Bytes)
        Write-Host "Generated local secret: $Key" -ForegroundColor DarkGray
    }
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
}

# Corporate OIDC credentials must be issued by the company's identity provider.
# Never invent them. Until IT supplies them, use the existing local/LAN pilot profile.
$OidcClientId = Get-EnvValue $EnvFile 'OIDC_CLIENT_ID'
$OidcClientSecret = Get-EnvValue $EnvFile 'OIDC_CLIENT_SECRET'
$HasCorporateOidc = -not (Test-Placeholder $OidcClientId) -and -not (Test-Placeholder $OidcClientSecret)

if (-not $HasCorporateOidc) {
    Write-Host ""
    Write-Host "[LOCAL PILOT] Corporate OIDC/SSO credentials are not configured." -ForegroundColor Yellow
    Write-Host "Starting the secured local/LAN pilot instead. Local secrets will be generated automatically." -ForegroundColor Yellow
    Write-Host "This mode is for pilot/demo use and is NOT the corporate SSO-certified rollout profile." -ForegroundColor Yellow
    Write-Host "When IT provides OIDC_CLIENT_ID and OIDC_CLIENT_SECRET, this launcher will automatically use strict corporate mode." -ForegroundColor Yellow
    Write-Host ""

    $LanEnv = Join-Path $Root '.env.lan'
    $LanLauncher = Join-Path $Root 'scripts\start_lan_windows.ps1'
    if (-not (Test-Path $LanLauncher)) { Stop-NoGo "Missing local/LAN pilot launcher." 30 }

    try {
        if (Test-Path $LanEnv) {
            # Repair an older manually copied LAN config that still contains placeholders.
            Ensure-Secret $LanEnv 'POSTGRES_PASSWORD' 32
            Ensure-Secret $LanEnv 'OIDC_STATE_SECRET' 32
            Ensure-Secret $LanEnv 'METRICS_TOKEN' 32
            Ensure-Secret $LanEnv 'MGC_ADMIN_PASSWORD' 24
            & $LanLauncher
        } else {
            # First local launch remains one-click: create a strong admin password automatically.
            $BootstrapAdminPassword = New-Secret 24
            & $LanLauncher -AdminPassword $BootstrapAdminPassword
        }
        if ($LASTEXITCODE -ne 0) { Stop-NoGo "Local/LAN pilot launcher failed." 30 }
        Write-Host "[GO] Local/LAN pilot started successfully." -ForegroundColor Green
        exit 0
    } catch {
        Stop-NoGo ("Local/LAN pilot launcher failed: " + $_.Exception.Message) 30
    }
}

# These secrets are deployment-local and can be generated safely. Corporate client
# credentials above are deliberately never generated by this launcher.
Ensure-Secret $EnvFile 'POSTGRES_PASSWORD' 32
Ensure-Secret $EnvFile 'OIDC_STATE_SECRET' 32
Ensure-Secret $EnvFile 'METRICS_TOKEN' 32

Write-Host "[MODE] Corporate OIDC credentials detected; using strict corporate profile." -ForegroundColor Green
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

Write-Host "[GO] Strict corporate pilot is healthy: $Url" -ForegroundColor Green
Start-Process $Url
exit 0
