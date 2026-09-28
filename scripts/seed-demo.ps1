$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
New-Item -ItemType Directory -Force data | Out-Null
uv run --project apps/api python -m lead_factory.demo_seed
