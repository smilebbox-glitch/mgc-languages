param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root

function Stage([string]$Text) { Write-Host "`n==> $Text" -ForegroundColor Cyan }
function Fail([string]$Text) { throw $Text }
function Get-EnvValue([string]$Key) {
    if (-not (Test-Path '.env')) { return '' }
    $line = Get-Content '.env' | Where-Object { $_ -match ('^' + [regex]::Escape($Key) + '=') } | Select-Object -Last 1
    if (-not $line) { return '' }
    return $line.Substring($Key.Length + 1)
}
function Set-EnvValue([string]$Key, [string]$Value) {
    $lines = if (Test-Path '.env') { @(Get-Content '.env') } else { @() }
    $found = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match ('^' + [regex]::Escape($Key) + '=')) {
            $lines[$i] = "$Key=$Value"
            $found = $true
        }
    }
    if (-not $found) { $lines += "$Key=$Value" }
    [System.IO.File]::WriteAllLines((Join-Path $Root '.env'), $lines, [System.Text.UTF8Encoding]::new($false))
}
function New-Secret([int]$Bytes = 48) {
    $buffer = New-Object byte[] $Bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
    return (-join ($buffer | ForEach-Object { $_.ToString('x2') }))
}
function Ensure-Secret([string]$Key, [string]$Placeholder = '') {
    $v = Get-EnvValue $Key
    if ([string]::IsNullOrWhiteSpace($v) -or ($Placeholder -and $v -eq $Placeholder)) {
        Set-EnvValue $Key (New-Secret)
    }
}
function Docker-Ready { try { & docker info *> $null; return ($LASTEXITCODE -eq 0) } catch { return $false } }

Stage 'Checking Docker'
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $desktop = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
    if (Test-Path $desktop) {
        Start-Process $desktop | Out-Null
        $dockerBin = 'C:\Program Files\Docker\Docker\resources\bin'
        if (Test-Path $dockerBin) { $env:Path = "$dockerBin;$env:Path" }
    } else {
        Fail 'Docker is not installed or is not in PATH. Install Docker Desktop once, then double-click START.bat again.'
    }
}
& docker compose version *> $null
if ($LASTEXITCODE -ne 0) { Fail 'Docker Compose v2 is required.' }
if (-not (Docker-Ready)) {
    $desktop = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
    if (Test-Path $desktop) {
        Write-Host 'Starting Docker Desktop...'
        Start-Process $desktop -ErrorAction SilentlyContinue | Out-Null
        for ($i=0; $i -lt 60 -and -not (Docker-Ready); $i++) { Start-Sleep -Seconds 2 }
    }
}
if (-not (Docker-Ready)) { Fail 'Docker daemon is not running. Start Docker Desktop and run START.bat again.' }

Stage 'Preparing secure pilot configuration'
if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host 'Created .env from .env.example'
}
Ensure-Secret 'SCHEDULER_TOKEN' 'change-me-before-pilot'
Ensure-Secret 'USER_DATA_HMAC_KEY' 'change-me-user-data-hmac-before-pilot'
Ensure-Secret 'AUDIT_HMAC_KEY'
$currentVersion = Get-EnvValue 'APP_VERSION'
if ([string]::IsNullOrWhiteSpace($currentVersion) -or $currentVersion -eq '1.6.0-pilot') { Set-EnvValue 'APP_VERSION' '1.6.1-pilot' }
$authMode = Get-EnvValue 'AUTH_MODE'
if ([string]::IsNullOrWhiteSpace($authMode)) { $authMode = 'disabled' }
if ($authMode -eq 'disabled') {
    Ensure-Secret 'ADMIN_API_TOKEN'
} elseif ($authMode -eq 'proxy') {
    if ([string]::IsNullOrWhiteSpace((Get-EnvValue 'AUTH_PROXY_SECRET'))) {
        Fail 'AUTH_MODE=proxy is configured but AUTH_PROXY_SECRET is empty. Configure the reverse proxy secret, then rerun START.bat.'
    }
} else {
    Fail "Unsupported AUTH_MODE='$authMode'. Expected disabled or proxy."
}
$policies = @{
    SOURCE_HISTORY_RETENTION_DAYS = 1
    SOURCE_HISTORY_MAX_ROWS = 100
    SCHEDULER_LOCK_TTL_SECONDS = 30
    SOURCE_SLA_FX_SECONDS = 60
    SOURCE_SLA_NEWS_SECONDS = 60
    USAGE_RETENTION_DAYS = 1
}
foreach ($key in $policies.Keys) {
    $raw = Get-EnvValue $key
    $n = 0
    if (-not [int]::TryParse($raw, [ref]$n) -or $n -lt $policies[$key]) {
        Fail "$key must be an integer >= $($policies[$key])."
    }
}
$bindAddress = Get-EnvValue 'APP_BIND_ADDRESS'; if (-not $bindAddress) { $bindAddress = '127.0.0.1' }
$allowPublic = Get-EnvValue 'ALLOW_PUBLIC_BIND'; if (-not $allowPublic) { $allowPublic = 'NO' }
if ($bindAddress -eq '0.0.0.0' -and $allowPublic -ne 'YES') {
    Fail 'APP_BIND_ADDRESS=0.0.0.0 requires ALLOW_PUBLIC_BIND=YES and explicit network controls.'
}

Stage 'Validating Docker Compose'
& docker compose config *> $null
if ($LASTEXITCODE -ne 0) { Fail 'docker compose config validation failed.' }

if (Test-Path 'okno-v-kitai-image.tar') {
    Stage 'Loading offline Docker image'
    & docker load -i 'okno-v-kitai-image.tar'
    if ($LASTEXITCODE -ne 0) { Fail 'docker load failed.' }
    $appVersion = Get-EnvValue 'APP_VERSION'; if (-not $appVersion) { $appVersion = '1.6.1-pilot' }
    $expectedImage = "okno-v-kitai:$appVersion"
    & docker image inspect $expectedImage *> $null
    if ($LASTEXITCODE -ne 0) { Fail "Offline image does not provide expected tag $expectedImage." }
    Stage 'Starting services without rebuild'
    & docker compose up -d --no-build
} else {
    Stage 'Building application image'
    & docker compose build
    if ($LASTEXITCODE -ne 0) { Fail 'Docker build failed. Check registry/network access and the build log above.' }
    Stage 'Starting web + scheduler'
    & docker compose up -d
}
if ($LASTEXITCODE -ne 0) { Fail 'docker compose up failed.' }

Stage 'Waiting for application readiness'
$cid = (& docker compose ps -q china-auto-radar).Trim()
if (-not $cid) { Fail 'Web container was not created.' }
$health = ''
for ($i=0; $i -lt 90; $i++) {
    $health = (& docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $cid 2>$null).Trim()
    if ($health -eq 'healthy') { break }
    if ($health -in @('exited','dead')) { & docker compose logs --tail=120 china-auto-radar; Fail 'Web container stopped during startup.' }
    Start-Sleep -Seconds 2
}
if ($health -ne 'healthy') { & docker compose logs --tail=120 china-auto-radar; Fail 'Application did not become healthy.' }

Stage 'Running smoke checks'
$port = Get-EnvValue 'APP_PORT'; if (-not $port) { $port = '3000' }
$base = "http://127.0.0.1:$port"
foreach ($path in @('/api/health','/api/ready','/api/content?section=travel-guide')) {
    $r = Invoke-WebRequest -UseBasicParsing -Uri ($base + $path) -TimeoutSec 15
    if ($r.StatusCode -lt 200 -or $r.StatusCode -ge 300) { Fail "$path returned HTTP $($r.StatusCode)" }
}
$running = @(& docker compose ps --status running --services)
if ($running -notcontains 'china-auto-radar-scheduler') { Fail 'Scheduler is not running.' }
Write-Host 'PASS  health/readiness/content + scheduler'

$adminToken = Get-EnvValue 'ADMIN_API_TOKEN'
$access = @(
    'Okno v Kitai Pilot v1.6.1',
    "URL: $base"
)
if ($authMode -eq 'disabled') { $access += "Admin API token: $adminToken" } else { $access += 'Authentication: corporate proxy / SSO' }
$access += ('Generated: ' + [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'))
[System.IO.File]::WriteAllLines((Join-Path $Root '.pilot-access.txt'), $access, [System.Text.UTF8Encoding]::new($false))

Stage 'READY'
Write-Host "Application: $base" -ForegroundColor Green
Write-Host "Access details: $(Join-Path $Root '.pilot-access.txt')"
Write-Host 'Stop: STOP.bat    Status: STATUS.bat'
if (-not $NoBrowser) { Start-Process $base -ErrorAction SilentlyContinue | Out-Null }
