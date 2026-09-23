# Bootstrap ELANORA with first administrator user on Windows
# Usage: .\dev-bootstrap.ps1

$ErrorActionPreference = "Stop"

function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Success { Write-Host $args -ForegroundColor Green }

Write-Info "Creating first administrator user..."

docker compose -f website/docker/website-dev/docker-compose.yml exec backend elanora-bootstrap `
    --instance-name "Local ELANORA" `
    --institution-name "Development Institute" `
    --contact-email "admin@example.org" `
    --domain "example.org" `
    --timezone "Europe/Paris" `
    --default-language "en" `
    --admin-username "administrator" `
    --admin-email "administrator@example.org" `
    --admin-first-name "Local" `
    --admin-last-name "Administrator" `
    --admin-affiliation "Development Institute" `
    --admin-department "Research IT"

if ($LASTEXITCODE -eq 0) {
    Write-Success "Bootstrap complete! You can now sign in at http://localhost:8777"
} else {
    Write-Host "Error during bootstrap" -ForegroundColor Red
    exit 1
}
