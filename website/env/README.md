# Environment configuration

Only `*.example` files belong in Git. Copy the example for the environment you
need, keep the resulting `.env.*` file local, and replace every production or
server placeholder with a secret from the deployment platform's secret store.

For local Docker development, no environment file is required:

```bash
make dev-up
```

For host-based Poetry/Vite development, create the ignored local file once:

```bash
cp website/env/.env.dev.example website/env/.env.dev
```

Production Compose interpolation must explicitly use the matching file:

```bash
docker compose --env-file website/env/.env.prod \
  -f website/docker/website-prod/docker-compose.yml up -d
```

Never commit credentials. Rotate any value that has been pasted into an issue,
chat, terminal transcript, or shared log.

`SETUP_TOKEN` protects the browser-based first-run installer. Generate a unique
high-entropy value for every production or server installation. Give it to the
responsible installation administrator through a secure channel. The endpoint
becomes unusable after the institution and first administrator have been
created, but the token should still remain private.

Production and server deployments must set `OUTBOX_ENCRYPTION_KEYS` to an
independently generated Fernet key. Generate one locally with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

For rotation, prepend the new key and retain the previous key after a comma
until all events encrypted by it have been delivered or deliberately discarded.
Never reuse the JWT signing key for outbox encryption.
