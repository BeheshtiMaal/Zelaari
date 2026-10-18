$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    uv run python -m PyInstaller --noconfirm --onedir --name sidecar --hidden-import=uvicorn.logging --hidden-import=uvicorn.loops --hidden-import=uvicorn.protocols.http --hidden-import=uvicorn.lifespan sidecar.py
    if ($LASTEXITCODE -ne 0) { throw 'Sidecar packaging failed' }
    uv run python -m PyInstaller --noconfirm --onedir --name job_launcher job_launcher.py
    if ($LASTEXITCODE -ne 0) { throw 'Watchdog packaging failed' }
}
finally { Pop-Location }
