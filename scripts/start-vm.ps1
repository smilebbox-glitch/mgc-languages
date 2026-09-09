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

function Get-VmIPv4 {
    try {
        $route = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -AddressFamily IPv4 -ErrorAction Stop |
            Sort-Object RouteMetric, InterfaceMetric |
            Select-Object -First 1
        if ($route) {
            $ip = Get-NetIPAddress -InterfaceIndex $route.InterfaceIndex -AddressFamily IPv4 -ErrorAction Stop |
                Where-Object { $_.AddressState -eq 'Preferred' -and $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
                Select-Object -First 1 -ExpandProperty IPAddress
            if ($ip) { return [string]$ip }
        }
    } catch {}

    try {
        $ip = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
            Where-Object { $_.AddressState -eq 'Preferred' -and $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
            Select-Object -First 1 -ExpandProperty IPAddress
        if ($ip) { return [string]$ip }
    } catch {}

    try {
        $ip = [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) |
            Where-Object { $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork -and $_.IPAddressToString -notlike '127.*' -and $_.IPAddressToString -notlike '169.254.*' } |
            Select-Object -First 1
        if ($ip) { return $ip.IPAddressToString }
    } catch {}

    return $null
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

# APP_ENV=pilot rejects wildcard trusted hosts. Repair existing .env.vm files on
# every start and allow only loopback plus the VM's detected primary IPv4.
$vmIp = Get-VmIPv4
$trustedHosts = 'localhost,127.0.0.1'
if ($vmIp) { $trustedHosts = "$trustedHosts,$vmIp" }
Set-SmallEnvValue 'MGC_TRUSTED_HOSTS' $trustedHosts

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
Write-Host "Local: http://127.0.0.1:$port" -ForegroundColor Green
if ($vmIp) { Write-Host "LAN:   http://${vmIp}:$port" -ForegroundColor Green }
Write-Host "Trusted hosts: $trustedHosts" -ForegroundColor DarkGray
Write-Host 'Admin password is stored only in .env.vm on this VM.' -ForegroundColor Yellow
