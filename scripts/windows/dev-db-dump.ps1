# Dump database to SQL file
# Usage: .\dev-db-dump.ps1

$ErrorActionPreference = "Stop"

function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Success { Write-Host $args -ForegroundColor Green }

Write-Info "Dumping database..."

# Create dumps directory if it doesn't exist
if (-not (Test-Path "website/dumps")) {
    New-Item -ItemType Directory -Path "website/dumps" -Force | Out-Null
}

# Dump database
docker compose -f website/docker/website-dev/docker-compose.yml exec -T db `
    pg_dump --no-owner --no-privileges --clean --if-exists -U elanora -d elanora `
    | Out-File -FilePath "website/dumps/elanora-dump.sql" -Encoding UTF8

if ($LASTEXITCODE -eq 0) {
    $fileSize = (Get-Item "website/dumps/elanora-dump.sql").Length / 1MB
    Write-Success "Database dumped to website/dumps/elanora-dump.sql ({0:F2} MB)" -f $fileSize
    Write-Info "Share this file. Recipient loads it with: .\dev-db-restore.ps1 -Path <file>"
} else {
    Write-Host "Error dumping database" -ForegroundColor Red
    exit 1
}
