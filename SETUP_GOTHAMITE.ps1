$ErrorActionPreference = 'Stop'
$appRoot = Join-Path $PSScriptRoot 'gothamite'
$pythonExe = Join-Path $appRoot '.venv\Scripts\python.exe'
$previousCext = $env:DISABLE_SQLALCHEMY_CEXT
Push-Location $appRoot
try {
    if (-not (Test-Path -LiteralPath $pythonExe)) {
        & python -c 'import sys; assert sys.version_info >= (3, 12), "Python 3.12+ is required"'
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12+ and put python on PATH.' }
        & python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
    }
    & $pythonExe -c 'import sys; assert sys.version_info >= (3, 12), "Python 3.12+ is required"'
    if ($LASTEXITCODE -ne 0) { throw 'The existing .venv needs Python 3.12+. Preserve it before replacing it.' }
    # Official pure-Python SQLAlchemy avoids this machine's native DLL restriction.
    $env:DISABLE_SQLALCHEMY_CEXT = '1'
    & $pythonExe -m pip install --no-binary sqlalchemy -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    Set-Location (Join-Path $appRoot 'frontend-react')
    & npm ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    Write-Host 'Setup complete. Run .\START_GOTHAMITE.ps1 from the repository root.'
} finally {
    $env:DISABLE_SQLALCHEMY_CEXT = $previousCext
    Pop-Location
}
