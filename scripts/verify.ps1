$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

uv run --project apps/api pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run --project apps/api ruff check apps/api/src apps/api/tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run --project apps/api pyright apps/api/src
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
npm --prefix apps/web test -- --run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
npm --prefix apps/web run lint
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
npm --prefix apps/web run build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "All unit, type, lint, and production-build checks passed."
