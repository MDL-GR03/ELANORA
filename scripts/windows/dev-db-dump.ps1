# Dump database to SQL file
# Usage: .\dev-db-dump.ps1

$ErrorActionPreference = "Stop"

function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Success { Write-Host $args -ForegroundColor Green }

Write-Info "Dumping database..."

# Find repository root (go up from scripts/windows to repo root)
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$composeFile = Join-Path $repoRoot "website" "docker" "website-dev" "docker-compose.yml"
$dumpsDir = Join-Path $repoRoot "website" "dumps"
$dumpFile = Join-Path $dumpsDir "elanora-dump.sql"

# Create dumps directory if it doesn't exist
if (-not (Test-Path $dumpsDir)) {
    New-Item -ItemType Directory -Path $dumpsDir -Force | Out-Null
}

# Dump database
docker compose -f $composeFile exec -T db `
    pg_dump --no-owner --no-privileges --clean --if-exists -U elanora -d elanora `
    | Out-File -FilePath $dumpFile -Encoding UTF8

if ($LASTEXITCODE -eq 0) {
    $fileSize = (Get-Item $dumpFile).Length / 1MB
    Write-Success "Database dumped to website/dumps/elanora-dump.sql ({0:F2} MB)" -f $fileSize
    Write-Info "Share this file. Recipient loads it with: .\dev-db-restore.ps1 -Path <file>"
} else {
    Write-Host "Error dumping database" -ForegroundColor Red
    exit 1
}
