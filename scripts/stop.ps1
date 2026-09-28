$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

foreach ($Name in @("api", "web")) {
    $PidFile = ".run/$Name.pid"
    if (Test-Path $PidFile) {
        $ProcessId = [int](Get-Content $PidFile)
        $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($Process) {
            taskkill /PID $ProcessId /T /F | Out-Null
            Write-Host "Stopped $Name (PID $ProcessId)."
        }
        Remove-Item -LiteralPath $PidFile
    }
}
