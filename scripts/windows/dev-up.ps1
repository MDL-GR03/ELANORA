# Start ELANORA development environment on Windows
# Usage: .\dev-up.ps1

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }

Write-Info "Starting ELANORA development environment..."

# Find repository root (go up from scripts/windows to repo root)
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))

# Check if .env.dev.docker exists, if not copy from example
$envFile = Join-Path $repoRoot "website" "env" ".env.dev.docker"
$envExample = Join-Path $repoRoot "website" "env" ".env.dev.docker.example"
if (-not (Test-Path $envFile)) {
    Write-Info "Creating .env.dev.docker from example..."
    Copy-Item $envExample $envFile
}

# Start Docker Compose
Write-Info "Building and starting containers..."
$composeFile = Join-Path $repoRoot "website" "docker" "website-dev" "docker-compose.yml"
docker compose -f $composeFile up --build --wait -d

if ($LASTEXITCODE -eq 0) {
    Write-Success "`nELANORA is running!"
    Write-Info "  Website:    http://localhost:8777"
    Write-Info "  API docs:   http://localhost:8018/docs"
    Write-Info "  Setup token: elanora-local-setup"
    Write-Info ""
    Write-Info "Run '.\dev-logs.ps1' to follow container logs"
    Write-Info "Run '.\dev-down.ps1' to stop the environment"
} else {
    Write-Host "Error starting containers" -ForegroundColor Red
    exit 1
}
