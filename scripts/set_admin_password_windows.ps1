param()

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root
$EnvFile = Join-Path $Root ".env.lan"

function Write-Utf8NoBom([string]$Path, [string]$Text) {
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $encoding)
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
    Write-Utf8NoBom $Path $text
}

if (-not (Test-Path $EnvFile)) {
    throw ".env.lan ещё не создан. Сначала запустите start-lan.cmd."
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker не найден."
}

docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker Engine не запущен." }

$secure = Read-Host "Новый пароль для admin" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}

if ([string]::IsNullOrWhiteSpace($password) -or $password.Length -lt 12) {
    throw "Пароль администратора должен быть не короче 12 символов."
}

Set-EnvValue $EnvFile "MGC_ADMIN_PASSWORD" $password
Set-EnvValue $EnvFile "MGC_ADMIN_DEPARTMENT" "Администрация"
Set-EnvValue $EnvFile "MGC_ADMIN_SYNC_CREDENTIALS" "true"

Write-Host "Перезапускаю app-контейнер и применяю новый пароль..." -ForegroundColor Cyan
docker compose --env-file .env.lan -f docker-compose.lan.yml up -d --no-deps --force-recreate app
if ($LASTEXITCODE -ne 0) { throw "Не удалось пересоздать app-контейнер." }

$portLine = Get-Content -LiteralPath $EnvFile | Where-Object { $_ -match '^MGC_PORT=' } | Select-Object -First 1
$Port = if ($portLine) { ($portLine -split '=', 2)[1].Trim() } else { "8080" }
$deadline = (Get-Date).AddMinutes(2)
while ((Get-Date) -lt $deadline) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health/ready" -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200) {
            Write-Host "Пароль admin обновлён. Логин: admin · Отдел: Администрация" -ForegroundColor Green
            exit 0
        }
    } catch {}
    Start-Sleep -Seconds 2
}

throw "Контейнер перезапущен, но readiness не вернулся в OK. Проверьте docker compose logs app."
