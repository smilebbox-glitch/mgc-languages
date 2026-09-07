param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

function New-Secret([int]$Bytes = 24) {
    $buffer = New-Object byte[] $Bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
    return ([Convert]::ToBase64String($buffer)).TrimEnd('=').Replace('+','-').Replace('/','_')
}

function Get-LanIPv4 {
    try {
        $route = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix "0.0.0.0/0" -ErrorAction Stop |
            Sort-Object RouteMetric, InterfaceMetric |
            Select-Object -First 1
        if ($route) {
            $ip = Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $route.InterfaceIndex -ErrorAction Stop |
                Where-Object { $_.IPAddress -ne "127.0.0.1" -and $_.IPAddress -notlike "169.254.*" } |
                Select-Object -First 1 -ExpandProperty IPAddress
            if ($ip) { return $ip }
        }
    } catch {}

    try {
        return Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
            Where-Object {
                $_.IPAddress -ne "127.0.0.1" -and
                $_.IPAddress -notlike "169.254.*" -and
                $_.AddressState -eq "Preferred"
            } |
            Sort-Object InterfaceMetric |
            Select-Object -First 1 -ExpandProperty IPAddress
    } catch {}

    return "127.0.0.1"
}

function Set-EnvValue([string]$Path, [string]$Key, [string]$Value) {
    $text = Get-Content -LiteralPath $Path -Raw
    $pattern = "(?m)^" + [Regex]::Escape($Key) + "=.*$"
    $line = "$Key=$Value"
    if ([Regex]::IsMatch($text, $pattern)) {
        $text = [Regex]::Replace($text, $pattern, $line)
    } else {
        if ($text.Length -gt 0 -and -not $text.EndsWith("`n")) { $text += "`r`n" }
        $text += "$line`r`n"
    }
    Set-Content -LiteralPath $Path -Value $text -Encoding UTF8
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker не найден. Установите/запустите Docker Desktop и повторите запуск."
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop установлен, но Docker Engine не запущен. Запустите Docker Desktop."
}

docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Команда 'docker compose' недоступна. Обновите Docker Desktop."
}

$LanIp = Get-LanIPv4
$ComputerName = $env:COMPUTERNAME
if ([string]::IsNullOrWhiteSpace($ComputerName)) { $ComputerName = "mgc-server" }
$EnvFile = Join-Path $Root ".env.lan"
$NewConfig = -not (Test-Path $EnvFile)

if ($NewConfig) {
    $dbPassword = New-Secret 32
    $adminPassword = New-Secret 24
    $stateSecret = New-Secret 32
    $metricsToken = New-Secret 32
    $trusted = "localhost,127.0.0.1,$LanIp,$ComputerName"

    @"
MGC_BIND_ADDRESS=0.0.0.0
MGC_PORT=8080
MGC_TRUSTED_HOSTS=$trusted
POSTGRES_DB=mgc_languages
POSTGRES_USER=mgc_languages
POSTGRES_PASSWORD=$dbPassword
MGC_ADMIN_USERNAME=admin
MGC_ADMIN_PASSWORD=$adminPassword
MGC_ADMIN_DISPLAY_NAME=MGC Admin
OIDC_STATE_SECRET=$stateSecret
METRICS_TOKEN=$metricsToken
REGISTRATION_ENABLED=true
SESSION_TTL_HOURS=168
WEB_CONCURRENCY=2
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=5
TTS_ENABLED=true
TTS_CONCURRENCY=2
CORS_ORIGINS=
"@ | Set-Content -LiteralPath $EnvFile -Encoding UTF8
} else {
    $trusted = "localhost,127.0.0.1,$LanIp,$ComputerName"
    Set-EnvValue $EnvFile "MGC_BIND_ADDRESS" "0.0.0.0"
    Set-EnvValue $EnvFile "MGC_TRUSTED_HOSTS" $trusted
}

$portLine = Get-Content -LiteralPath $EnvFile | Where-Object { $_ -match '^MGC_PORT=' } | Select-Object -First 1
$Port = if ($portLine) { ($portLine -split '=', 2)[1].Trim() } else { "8080" }

Write-Host ""
Write-Host "MGC Languages LAN" -ForegroundColor Cyan
Write-Host "Server IP: $LanIp"
Write-Host "Trusted hosts: $trusted"
Write-Host "Workers: $(if ((Get-Content $EnvFile | Select-String '^WEB_CONCURRENCY=')) { ((Get-Content $EnvFile | Select-String '^WEB_CONCURRENCY=').Line -split '=',2)[1] } else { '2' })"
Write-Host ""

$composeArgs = @("compose", "--env-file", ".env.lan", "-f", "docker-compose.lan.yml", "up", "-d")
if (-not $SkipBuild) { $composeArgs += "--build" }
& docker @composeArgs
if ($LASTEXITCODE -ne 0) { throw "docker compose up завершился с ошибкой." }

$healthUrl = "http://127.0.0.1:$Port/health/ready"
$deadline = (Get-Date).AddMinutes(3)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 2
}

if (-not $ready) {
    Write-Host "Сервис запущен, но readiness пока не стал 200. Проверьте: docker compose --env-file .env.lan -f docker-compose.lan.yml logs app" -ForegroundColor Yellow
} else {
    Write-Host "Readiness: OK" -ForegroundColor Green
}

Write-Host ""
Write-Host "Открыть на этом компьютере: http://localhost:$Port" -ForegroundColor Green
if ($LanIp -ne "127.0.0.1") {
    Write-Host "Ссылка для коллег в той же сети: http://${LanIp}:$Port" -ForegroundColor Green
    Write-Host "Также может работать: http://${ComputerName}:$Port"
}
Write-Host ""

if ($NewConfig) {
    $adminLine = Get-Content -LiteralPath $EnvFile | Where-Object { $_ -match '^MGC_ADMIN_PASSWORD=' } | Select-Object -First 1
    $adminPasswordSaved = ($adminLine -split '=', 2)[1]
    Write-Host "Первый администратор: admin" -ForegroundColor Cyan
    Write-Host "Пароль администратора: $adminPasswordSaved" -ForegroundColor Cyan
    Write-Host "Пароль сохранён локально в .env.lan (файл исключён из Git)."
}

Write-Host "Если коллеги не открывают ссылку, разрешите входящий TCP-порт $Port в Windows Firewall для Private/Domain сети." -ForegroundColor Yellow
Write-Host "Для корпоративного rollout вместо открытого LAN-профиля используйте TLS + OIDC + явный TRUSTED_HOSTS." -ForegroundColor Yellow
