# ELANORA Development on Windows

**TL;DR**: Use PowerShell scripts in `scripts/windows/` instead of `make` commands.

```powershell
cd scripts/windows
.\dev-up.ps1          # Start everything
.\dev-bootstrap.ps1   # First time: create admin user
.\dev-logs.ps1        # View logs
.\dev-down.ps1        # Stop
```

## Why Not Use `make` on Windows?

The `Makefile` contains development commands that are standard on Linux/Mac but don't work natively on Windows. While you can install `make` via Cygwin, Chocolatey, or WSL, that adds friction for Windows developers.

## Project Structure

```text
ELANORA/
├── Makefile                 ← Development commands (Linux/Mac)
├── WINDOWS_DEVELOPMENT.md   ← This file
└── scripts/
    └── windows/            ← PowerShell equivalents (Windows development)
        ├── dev-up.ps1
        ├── dev-down.ps1
        ├── dev-logs.ps1
        ├── dev-bootstrap.ps1
        ├── dev-db-*.ps1
        ├── help.ps1
        └── README.md
```

## For Different Developers

| You are... | Use this |
| --- | --- |
| Developing on **Linux/Mac** with `make` | `make dev-up`, `make dev-logs`, etc. (Makefile) |
| Developing on **Windows** with PowerShell | `.\dev-up.ps1`, `.\dev-logs.ps1`, etc. (scripts/windows/) |
| Developing on **Windows with WSL2** | `make dev-up`, etc. (same as Linux) |
| **Deploying** ELANORA to production | Use web-based setup at `/setup` after starting containers |

## Getting Started

See [scripts/windows/README.md](scripts/windows/README.md) for:

- Prerequisites (Docker Desktop, PowerShell)
- Detailed commands
- Troubleshooting
- Running frontend/backend without Docker

## Questions?

Check the appropriate guide:

- **Windows development**: [scripts/windows/README.md](scripts/windows/README.md)
- **Linux/Mac development**: Run `make help` or see the Makefile
- **Production deployment**: Start containers, then use the web-based setup UI
