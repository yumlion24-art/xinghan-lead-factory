$ErrorActionPreference = "Stop"
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8010/api/v1"
npm --prefix apps/web run dev -- --hostname 127.0.0.1 --port 3010
