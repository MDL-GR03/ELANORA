# Show ELANORA development container status on Windows
# Usage: .\dev-status.ps1

$ErrorActionPreference = "Stop"

# Find repository root (go up from scripts/windows to repo root)
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$composeFile = Join-Path $repoRoot "website" "docker" "website-dev" "docker-compose.yml"

docker compose -f $composeFile ps
