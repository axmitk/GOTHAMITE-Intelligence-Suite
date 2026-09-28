$ErrorActionPreference = 'Stop'
$appRoot = Join-Path $PSScriptRoot 'gothamite'
$pythonExe = Join-Path $appRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw 'Run .\SETUP_GOTHAMITE.ps1 first.'
}
if (-not (Test-Path -LiteralPath (Join-Path $appRoot 'frontend-react\dist\index.html'))) {
    throw 'Frontend build is missing. Run .\SETUP_GOTHAMITE.ps1 first.'
}
Push-Location $appRoot
try {
    Write-Host 'GOTHAMITE local synthetic workbench. Open http://127.0.0.1:8042 (default port). Ctrl+C stops the server.'
    & $pythonExe scripts/run_workbench.py
    if ($LASTEXITCODE -ne 0) { throw 'Server stopped with an error. Review the output above.' }
} finally {
    Pop-Location
}
