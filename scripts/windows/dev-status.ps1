# Show ELANORA development container status on Windows
# Usage: .\dev-status.ps1

$ErrorActionPreference = "Stop"

docker compose -f website/docker/website-dev/docker-compose.yml ps
