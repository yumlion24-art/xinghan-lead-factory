$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
New-Item -ItemType Directory -Force data, logs, .run | Out-Null

$Api = Start-Process powershell -WindowStyle Hidden -PassThru -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
    "Set-Location '$Root'; uv run --project apps/api uvicorn lead_factory.main:app --app-dir apps/api/src --host 127.0.0.1 --port 8000 *>> logs/api.log"
)
$Web = Start-Process powershell -WindowStyle Hidden -PassThru -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
    "Set-Location '$Root'; npm --prefix apps/web run dev -- --hostname 127.0.0.1 *>> logs/web.log"
)
$Api.Id | Set-Content .run/api.pid
$Web.Id | Set-Content .run/web.pid
Write-Host "Xinghan Lead Factory is starting: http://127.0.0.1:3000"
Write-Host "API health: http://127.0.0.1:8000/api/v1/health"
Write-Host "Stop it with: powershell -ExecutionPolicy Bypass -File scripts/stop.ps1"
