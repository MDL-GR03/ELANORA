# Show current database migration status
# Usage: .\dev-db-status.ps1

$ErrorActionPreference = "Stop"

function Write-Info { Write-Host $args -ForegroundColor Cyan }

Write-Info "Database migration status:"

# Find repository root (go up from scripts/windows to repo root)
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$composeFile = Join-Path $repoRoot "website" "docker" "website-dev" "docker-compose.yml"

docker compose -f $composeFile exec backend alembic current
