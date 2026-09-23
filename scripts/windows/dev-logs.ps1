# Follow ELANORA development container logs on Windows
# Usage: .\dev-logs.ps1

$ErrorActionPreference = "Stop"

docker compose -f website/docker/website-dev/docker-compose.yml logs -f
