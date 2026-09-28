if (Test-Path .env) {
    foreach ($Line in Get-Content .env) {
        if ($Line -match '^\s*#' -or $Line -notmatch '=') { continue }
        $Name, $Value = $Line -split '=', 2
        [Environment]::SetEnvironmentVariable($Name.Trim(), $Value.Trim(), "Process")
    }
}
