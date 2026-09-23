# Stop ELANORA development environment on Windows
# Usage: .\dev-down.ps1

$ErrorActionPreference = "Stop"

function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Success { Write-Host $args -ForegroundColor Green }

Write-Info "Stopping ELANORA development environment..."

docker compose -f website/docker/website-dev/docker-compose.yml down

if ($LASTEXITCODE -eq 0) {
    Write-Success "Containers stopped (database data preserved)"
} else {
    Write-Host "Error stopping containers" -ForegroundColor Red
    exit 1
}
