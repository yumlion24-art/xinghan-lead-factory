$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install it from https://docs.astral.sh/uv/ and retry."
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js 20+ is required."
}
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env from .env.example (rules-only mode)."
}
New-Item -ItemType Directory -Force data, logs, .run | Out-Null
uv sync --project apps/api
npm ci
Write-Host "Setup complete. Run: powershell -ExecutionPolicy Bypass -File scripts/seed-demo.ps1"
