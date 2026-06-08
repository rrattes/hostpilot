$ErrorActionPreference = "Stop"

function Assert-ProjectRoot {
    foreach ($folder in @("backend", "frontend", "agent")) {
        if (-not (Test-Path -LiteralPath $folder -PathType Container)) {
            throw "Run this script from the webpanel project root. Missing folder: $folder"
        }
    }
}

function Assert-Command {
    param([Parameter(Mandatory = $true)][string] $Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

Assert-ProjectRoot
Assert-Command -Name "python"
Assert-Command -Name "npm"

$projectRoot = (Get-Location).Path
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"
$logDir = Join-Path $projectRoot ".dev\logs"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$backendVenv = Join-Path $backendDir ".venv"
$backendPython = Join-Path $backendVenv "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $backendVenv -PathType Container)) {
    Write-Host "Creating backend virtual environment..."
    python -m venv $backendVenv
}

Write-Host "Installing backend requirements..."
& $backendPython -m pip install -r (Join-Path $backendDir "requirements.txt")

Write-Host "Running backend migrations..."
Push-Location $backendDir
try {
    & $backendPython -m alembic upgrade head
}
finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath (Join-Path $frontendDir "node_modules") -PathType Container)) {
    Write-Host "Installing frontend dependencies..."
    Push-Location $frontendDir
    try {
        npm install
    }
    finally {
        Pop-Location
    }
}

$backendOut = Join-Path $logDir "backend.out.log"
$backendErr = Join-Path $logDir "backend.err.log"
$frontendOut = Join-Path $logDir "frontend.out.log"
$frontendErr = Join-Path $logDir "frontend.err.log"

Write-Host "Starting backend on 127.0.0.1:8000..."
$backendProcess = Start-Process `
    -FilePath $backendPython `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") `
    -WorkingDirectory $backendDir `
    -RedirectStandardOutput $backendOut `
    -RedirectStandardError $backendErr `
    -PassThru `
    -WindowStyle Hidden

Write-Host "Starting frontend on 127.0.0.1:5173..."
$frontendProcess = Start-Process `
    -FilePath "npm.cmd" `
    -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "5173") `
    -WorkingDirectory $frontendDir `
    -RedirectStandardOutput $frontendOut `
    -RedirectStandardError $frontendErr `
    -PassThru `
    -WindowStyle Hidden

Write-Host ""
Write-Host "HostPilot development environment"
Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "API docs: http://127.0.0.1:8000/docs"
Write-Host "Frontend: http://127.0.0.1:5173"
Write-Host "Logs:     $logDir"
Write-Host ""
Write-Host "Press Ctrl+C to stop backend and frontend."

try {
    while ($true) {
        Start-Sleep -Seconds 1

        if ($backendProcess.HasExited) {
            throw "Backend process exited. Check logs in $logDir."
        }

        if ($frontendProcess.HasExited) {
            throw "Frontend process exited. Check logs in $logDir."
        }
    }
}
finally {
    Write-Host ""
    Write-Host "Stopping HostPilot development processes..."

    if ($backendProcess -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force
    }

    if ($frontendProcess -and -not $frontendProcess.HasExited) {
        Stop-Process -Id $frontendProcess.Id -Force
    }
}
