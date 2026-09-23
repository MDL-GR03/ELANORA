# ELANORA Development on Windows

This directory contains PowerShell scripts to make ELANORA development easier on Windows. These scripts replace `make` commands, which don't work natively on Windows.

## Prerequisites

1. **Docker Desktop for Windows**
   - Install from https://www.docker.com/products/docker-desktop
   - Enable WSL 2 backend (recommended) for best performance
   - Verify: Run `docker --version` in PowerShell

2. **PowerShell 5.0+** (built into Windows 10+)
   - Verify: Run `$PSVersionTable.PSVersion` in PowerShell

## Quick Start

```powershell
# Start the development environment
.\dev-up.ps1

# Wait for containers to be ready, then bootstrap (first time only)
.\dev-bootstrap.ps1

# Follow logs in a new PowerShell window
.\dev-logs.ps1

# Stop when done
.\dev-down.ps1
```

Access the application:
- **Website**: http://localhost:8777
- **API Docs**: http://localhost:8018/docs
- **Setup token**: `elanora-local-setup`

## Available Scripts

### Core Commands

| Script | Purpose |
|--------|---------|
| `dev-up.ps1` | Build and start all containers |
| `dev-down.ps1` | Stop containers (preserves database) |
| `dev-logs.ps1` | Follow container logs (use new PowerShell window) |
| `dev-status.ps1` | Show running containers |

### Database Commands

| Script | Purpose |
|--------|---------|
| `dev-bootstrap.ps1` | Create first administrator (run once after `dev-up`) |
| `dev-db-status.ps1` | Show current database migration version |
| `dev-db-dump.ps1` | Export database to SQL file |
| `dev-db-restore.ps1 -Path <file>` | Import database from SQL file |

### Example Workflow

```powershell
# First time setup
.\dev-up.ps1              # Starts containers and runs migrations
.\dev-bootstrap.ps1       # Creates admin user

# Daily development
.\dev-up.ps1              # Resume from yesterday (preserves data)
# ... do development ...
.\dev-logs.ps1            # Debug issues
.\dev-down.ps1            # Stop when done

# Sharing database state with teammates
.\dev-db-dump.ps1                          # Export to website/dumps/elanora-dump.sql
# Share the .sql file via your normal channel
.\dev-db-restore.ps1 -Path path/to/dump.sql  # Teammate imports it
```

## Running Backend/Frontend Directly

If you need to work without Docker, or prefer native development:

### Backend (Python/FastAPI)

```powershell
cd website/backend
poetry install
poetry run pytest tests/unit              # Run unit tests
poetry run pytest tests/integration       # Run integration tests (needs PostgreSQL)
poetry run python -m app.main             # Run server
```

### Frontend (Node.js/Vue)

```powershell
cd website/frontend
npm install
npm run dev                                # Development server
npm run build                              # Production build
npm run test                               # Run tests
```

## Manual Docker Compose Commands

If you prefer direct `docker compose` commands:

```powershell
# Start containers
docker compose -f website/docker/website-dev/docker-compose.yml up --build --wait -d

# Follow logs
docker compose -f website/docker/website-dev/docker-compose.yml logs -f

# Execute commands in running container
docker compose -f website/docker/website-dev/docker-compose.yml exec backend alembic current

# Stop containers
docker compose -f website/docker/website-dev/docker-compose.yml down
```

## Troubleshooting

### Containers won't start
```powershell
# Check Docker is running
docker ps

# See error logs
.\dev-logs.ps1

# Try forcing a rebuild
docker compose -f website/docker/website-dev/docker-compose.yml down --volumes
.\dev-up.ps1
```

### Port 8777 already in use
Something else is running on port 8777. Stop it or check `docker ps` to see if containers are already running:
```powershell
.\dev-status.ps1
```

### Database connection errors
```powershell
# Check database is ready
.\dev-db-status.ps1

# Recreate database from scratch
docker compose -f website/docker/website-dev/docker-compose.yml down --volumes
.\dev-up.ps1
.\dev-bootstrap.ps1
```

### Performance issues
- If using WSL 1 instead of WSL 2, upgrade to WSL 2 for better performance
- Don't store the project in Windows system folders (C:\Windows\...), use your user folder
- Consider excluding the project from Windows Defender scanning

## Linux/Mac Users

If you have `make` available, you can still use the Makefile directly:
```bash
make dev-up
make dev-logs
make dev-down
```

These PowerShell scripts mirror the Makefile commands exactly, so switching between Windows and Linux is seamless.

## Support

See the main [ELANORA README](../../README.md) for additional documentation.
