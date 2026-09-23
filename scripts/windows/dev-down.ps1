# Stop ELANORA development environment on Windows
# Usage: .\dev-down.ps1

$ErrorActionPreference = "Stop"

function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Success { Write-Host $args -ForegroundColor Green }

Write-Info "Stopping ELANORA development environment..."

# Find repository root (go up from scripts/windows to repo root)
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$composeFile = Join-Path $repoRoot "website" "docker" "website-dev" "docker-compose.yml"

docker compose -f $composeFile down

if ($LASTEXITCODE -eq 0) {
    Write-Success "Containers stopped (database data preserved)"
} else {
    Write-Host "Error stopping containers" -ForegroundColor Red
    exit 1
}
