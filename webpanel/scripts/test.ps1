$ErrorActionPreference = "Stop"

function Assert-ProjectRoot {
    foreach ($folder in @("backend", "frontend", "agent")) {
        if (-not (Test-Path -LiteralPath $folder -PathType Container)) {
            throw "Run this script from the webpanel project root. Missing folder: $folder"
        }
    }
}

function Invoke-Check {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string] $WorkingDirectory,
        [Parameter(Mandatory = $true)][scriptblock] $Command
    )

    Write-Host ""
    Write-Host "Running $Name..."

    Push-Location $WorkingDirectory
    try {
        try {
            $output = & $Command 2>&1
            $exitCode = $LASTEXITCODE
        }
        catch {
            $output = $_
            $exitCode = 1
        }

        if ($output) {
            $output | ForEach-Object { Write-Host $_ }
        }
    }
    finally {
        Pop-Location
    }

    return [pscustomobject]@{
        Name = $Name
        Passed = ($exitCode -eq 0)
    }
}

Assert-ProjectRoot

$projectRoot = (Get-Location).Path
$results = @()

$results += Invoke-Check -Name "Backend tests" -WorkingDirectory (Join-Path $projectRoot "backend") -Command {
    python -m pytest
}

$results += Invoke-Check -Name "Agent tests" -WorkingDirectory (Join-Path $projectRoot "agent") -Command {
    python -m pytest
}

$results += Invoke-Check -Name "Frontend install and build" -WorkingDirectory (Join-Path $projectRoot "frontend") -Command {
    npm ci
    if ($LASTEXITCODE -ne 0) {
        throw "npm ci failed with exit code $LASTEXITCODE"
    }

    npm run build
}

Write-Host ""
Write-Host "Summary"
Write-Host "-------"

foreach ($result in $results) {
    if ($result.Passed) {
        Write-Host ("PASS {0}" -f $result.Name)
    }
    else {
        Write-Host ("FAIL {0}" -f $result.Name)
    }
}

if ($results | Where-Object { -not $_.Passed }) {
    exit 1
}

Write-Host ""
Write-Host "All checks passed."
