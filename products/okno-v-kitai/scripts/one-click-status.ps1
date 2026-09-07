$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker is not installed or is not in PATH.' }
& docker compose ps
$cid = (& docker compose ps -q china-auto-radar 2>$null).Trim()
if ($cid) {
    $health = (& docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $cid 2>$null).Trim()
    Write-Host "Web health: $health"
}
$port = '3000'
if (Test-Path '.env') {
    $line = Get-Content '.env' | Where-Object { $_ -match '^APP_PORT=' } | Select-Object -Last 1
    if ($line) { $port = $line.Substring('APP_PORT='.Length) }
}
Write-Host "URL: http://127.0.0.1:$port"
