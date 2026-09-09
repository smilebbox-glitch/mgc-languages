$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root
$EnvFile = Join-Path $Root '.env.vm'
$Example = Join-Path $Root '.env.vm.example'

function New-HexSecret([int]$Bytes = 32) {
    $buffer = New-Object byte[] $Bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
    return (-join ($buffer | ForEach-Object { $_.ToString('x2') }))
}

function Set-SmallEnvValue([string]$Key, [string]$Value) {
    $lines = [System.Collections.Generic.List[string]]::new()
    $found = $false
    $reader = [System.IO.StreamReader]::new($EnvFile)
    try {
        while (($line = $reader.ReadLine()) -ne $null) {
            if ($line.StartsWith("$Key=")) { $lines.Add("$Key=$Value"); $found = $true } else { $lines.Add($line) }
        }
    } finally { $reader.Dispose() }
    if (-not $found) { $lines.Add("$Key=$Value") }
    [System.IO.File]::WriteAllLines($EnvFile, $lines, [System.Text.UTF8Encoding]::new($false))
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker is not installed or not in PATH.' }
& docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker daemon is not running.' }
& docker compose version *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose v2 is required.' }

if (-not (Test-Path $EnvFile)) {
    Copy-Item $Example $EnvFile
    Set-SmallEnvValue 'POSTGRES_PASSWORD' (New-HexSecret)
    Set-SmallEnvValue 'OIDC_STATE_SECRET' (New-HexSecret)
    Set-SmallEnvValue 'MGC_ADMIN_PASSWORD' (New-HexSecret)
    Set-SmallEnvValue 'METRICS_TOKEN' (New-HexSecret)
    Write-Host 'Created .env.vm with generated local credentials.' -ForegroundColor Green
}

$composeArgs = @('compose','--env-file','.env.vm','-f','docker-compose.lan.yml','-f','docker-compose.vm.yml')
Write-Host 'Validating CPU-only / no-AI VM configuration...' -ForegroundColor Cyan
& docker @composeArgs config *> $null
if ($LASTEXITCODE -ne 0) { throw 'docker compose config failed.' }

Write-Host 'Building MGC Languages...' -ForegroundColor Cyan
& docker @composeArgs build app
if ($LASTEXITCODE -ne 0) { throw 'Docker build failed.' }

Write-Host 'Starting PostgreSQL + app + nginx...' -ForegroundColor Cyan
& docker @composeArgs up -d db app nginx
if ($LASTEXITCODE -ne 0) { throw 'Docker startup failed.' }

$cid = (& docker @composeArgs ps -q app).Trim()
if (-not $cid) { throw 'App container was not created.' }
$health = ''
for ($i=0; $i -lt 120; $i++) {
    $health = (& docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $cid 2>$null).Trim()
    if ($health -eq 'healthy') { break }
    if ($health -in @('exited','dead')) { & docker @composeArgs logs --tail=160 app db; throw 'Application stopped during startup.' }
    Start-Sleep -Seconds 2
}
if ($health -ne 'healthy') { & docker @composeArgs logs --tail=160 app db; throw 'Application did not become healthy.' }

$port = '8080'
$reader = [System.IO.StreamReader]::new($EnvFile)
try { while (($line = $reader.ReadLine()) -ne $null) { if ($line.StartsWith('MGC_PORT=')) { $port = $line.Substring(9) } } } finally { $reader.Dispose() }

Write-Host ''
Write-Host '[GO] MGC Languages VM is ready (CPU-only, server-side AI/TTS disabled).' -ForegroundColor Green
Write-Host "Open: http://127.0.0.1:$port" -ForegroundColor Green
Write-Host 'Admin password is stored only in .env.vm on this VM.' -ForegroundColor Yellow
