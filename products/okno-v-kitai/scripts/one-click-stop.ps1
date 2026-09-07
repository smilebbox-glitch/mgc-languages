$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker is not installed or is not in PATH.' }
& docker compose down
if ($LASTEXITCODE -ne 0) { throw 'docker compose down failed.' }
Write-Host 'Okno v Kitai stopped. Persistent data volume was preserved.' -ForegroundColor Green
