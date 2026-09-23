# Restore database from SQL dump
# Usage: .\dev-db-restore.ps1 -Path <path-to-dump-file>

param(
    [Parameter(Mandatory=$true)]
    [string]$Path
)

$ErrorActionPreference = "Stop"

function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Error { Write-Host $args -ForegroundColor Red }

# Find repository root (go up from scripts/windows to repo root)
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))

# Validate file exists
if (-not (Test-Path $Path)) {
    Write-Error "File not found: $Path"
    exit 1
}

$absolutePath = (Resolve-Path $Path).Path
$composeFile = Join-Path $repoRoot "website" "docker" "website-dev" "docker-compose.yml"

Write-Info "Restoring database from $absolutePath..."
Write-Info "WARNING: This will replace all database data."

# Get user confirmation
$response = Read-Host "Are you sure? (yes/no)"
if ($response -ne "yes") {
    Write-Info "Cancelled."
    exit 0
}

# Restore database
Get-Content $absolutePath | docker compose -f $composeFile exec -T db psql -U elanora -d elanora

if ($LASTEXITCODE -eq 0) {
    Write-Success "Database restored successfully!"
    Write-Info "The backend will pick up the new data on the next request."
} else {
    Write-Error "Error restoring database"
    exit 1
}
