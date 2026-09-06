# ELANORA logging guide

ELANORA writes application logs to standard error. Docker, systemd, or the
institution's observability platform is responsible for collecting, rotating,
retaining, and exporting them. Application processes must not create log files
inside the source tree or mutable research-data directories.

## Application usage

Create one module logger at import time:

```python
from app.core.centralized_logging import get_logger

logger = get_logger()
```

Use parameterized messages so formatting only occurs when the level is active:

```python
logger.info("Revision %s accepted for project %s", revision_id, project_id)
```

Set `LOG_LEVEL` for ELANORA loggers, `CONSOLE_LOG_LEVEL` when the emitted level
must differ, and `ROOT_LOG_LEVEL` for third-party libraries. Production normally
uses `INFO` or `WARNING`; development may use `DEBUG` temporarily.

## Container operations

Follow development output with:

```bash
make dev-logs
```

Inspect a single process with:

```bash
docker compose -f website/docker/website-dev/docker-compose.yml logs backend
docker compose -f website/docker/website-dev/docker-compose.yml logs outbox-worker
```

Production retention belongs in the deployment platform. Configure limits and
off-host export there rather than adding a Python file handler. This prevents
root-owned bind-mount files, avoids competing rotation across worker processes,
and keeps container instances disposable.

## Security rules

- Never log passwords, bearer tokens, reset or verification codes, cookies,
  complete email payloads, EAF contents, or participant-identifying metadata.
- Prefer stable identifiers and event names over filenames or human names.
- Preserve the request correlation ID on errors.
- Use `logger.exception(...)` or `exc_info=True` for unexpected internal errors,
  while returning a generic response to the client.
- Treat IP addresses and user-agent strings as personal data in retention and
  access policies.
