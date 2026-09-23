# Display available ELANORA development commands for Windows
# Usage: .\help.ps1

$commands = @(
    @{
        Category = "Core Commands"
        Items = @(
            @{
                Name = "dev-up.ps1"
                Description = "Build and start all containers (website, database, mail)"
            },
            @{
                Name = "dev-down.ps1"
                Description = "Stop containers (database data is preserved)"
            },
            @{
                Name = "dev-status.ps1"
                Description = "Show running container status"
            },
            @{
                Name = "dev-logs.ps1"
                Description = "Follow container logs (open in new PowerShell window)"
            }
        )
    },
    @{
        Category = "Database Commands"
        Items = @(
            @{
                Name = "dev-bootstrap.ps1"
                Description = "Create first administrator user (run once after dev-up)"
            },
            @{
                Name = "dev-db-status.ps1"
                Description = "Show current database migration version"
            },
            @{
                Name = "dev-db-dump.ps1"
                Description = "Export database to SQL file"
            },
            @{
                Name = "dev-db-restore.ps1 -Path <file>"
                Description = "Import database from SQL file"
            }
        )
    }
)

Write-Host "ELANORA Development Commands (Windows)" -ForegroundColor Cyan -BackgroundColor Black
Write-Host ""

foreach ($section in $commands) {
    Write-Host $section.Category -ForegroundColor Yellow
    foreach ($item in $section.Items) {
        Write-Host "  .\$($item.Name)" -ForegroundColor Green -NoNewline
        Write-Host " - $($item.Description)" -ForegroundColor White
    }
    Write-Host ""
}

Write-Host "First Time Setup" -ForegroundColor Yellow
Write-Host "  1. .\dev-up.ps1" -ForegroundColor Green
Write-Host "  2. .\dev-bootstrap.ps1" -ForegroundColor Green
Write-Host "  3. Visit http://localhost:8777" -ForegroundColor Green
Write-Host ""

Write-Host "For more details, see: README.md" -ForegroundColor Cyan
