# Show current database migration status
# Usage: .\dev-db-status.ps1

$ErrorActionPreference = "Stop"

function Write-Info { Write-Host $args -ForegroundColor Cyan }

Write-Info "Database migration status:"
docker compose -f website/docker/website-dev/docker-compose.yml exec backend alembic current
