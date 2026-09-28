$ErrorActionPreference = "Stop"
$env:LF_DATABASE_URL = "sqlite+pysqlite:///./data/e2e.db"
$env:LF_WEB_ORIGIN = "http://127.0.0.1:3010"
New-Item -ItemType Directory -Force data | Out-Null
uv run --project apps/api python -m lead_factory.demo_seed
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run --project apps/api uvicorn lead_factory.main:app --app-dir apps/api/src --host 127.0.0.1 --port 8010
