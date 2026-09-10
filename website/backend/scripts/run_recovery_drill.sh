#!/usr/bin/env sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
compose_file="$repository_root/website/docker/website-test/docker-compose.yml"
source_database_url="postgresql+asyncpg://elanora_test:elanora-test-only@127.0.0.1:5418/elanora_test"
restored_database_url="postgresql+asyncpg://elanora_test:elanora-test-only@127.0.0.1:5418/elanora_restore_drill"
drill_root=$(mktemp -d "${TMPDIR:-/tmp}/elanora-recovery-drill.XXXXXX")

cleanup() {
  docker compose -f "$compose_file" down --volumes --remove-orphans >/dev/null 2>&1 || true
  rm -rf -- "$drill_root"
}
trap cleanup EXIT HUP INT TERM

cd "$repository_root"
make test-db-reset
mkdir -p "$drill_root/source/projects" "$drill_root/source/assets"

cd "$repository_root/website/backend"
ENVIRONMENT=test \
DATABASE_URL="$source_database_url" \
ELAN_PROJECTS_BASE_PATH="$drill_root/source/projects" \
INSTANCE_ASSETS_BASE_PATH="$drill_root/source/assets" \
poetry run python scripts/seed_recovery_drill.py \
  --database-url "$source_database_url" \
  --projects "$drill_root/source/projects" \
  --assets "$drill_root/source/assets"

docker compose -f "$compose_file" exec -T db \
  pg_dump --no-owner --no-privileges --serializable-deferrable \
  -U elanora_test -d elanora_test > "$drill_root/elanora.sql"

ELANORA_BACKUP_PASSPHRASE=$(poetry run python -c 'import secrets; print(secrets.token_urlsafe(32))')
export ELANORA_BACKUP_PASSPHRASE
poetry run python -m app.cli.disaster_recovery create \
  --database-dump "$drill_root/elanora.sql" \
  --projects "$drill_root/source/projects" \
  --assets "$drill_root/source/assets" \
  --output "$drill_root/elanora.elanora" >/dev/null
poetry run python -m app.cli.disaster_recovery verify \
  "$drill_root/elanora.elanora" >/dev/null

docker compose -f "$compose_file" exec -T db dropdb -U elanora_test elanora_test
docker compose -f "$compose_file" exec -T db \
  createdb -U elanora_test elanora_restore_drill
poetry run python -m app.cli.disaster_recovery extract "$drill_root/elanora.elanora" \
  --destination "$drill_root/restored" >/dev/null
docker compose -f "$compose_file" exec -T db \
  psql -v ON_ERROR_STOP=1 -U elanora_test -d elanora_restore_drill \
  < "$drill_root/restored/database.sql" >/dev/null

ENVIRONMENT=test \
DATABASE_URL="$restored_database_url" \
ELAN_PROJECTS_BASE_PATH="$drill_root/restored/projects" \
INSTANCE_ASSETS_BASE_PATH="$drill_root/restored/instance-assets" \
poetry run python -m app.cli.check_integrity --project recovery-corpus

counts=$(docker compose -f "$compose_file" exec -T db \
  psql -At -U elanora_test -d elanora_restore_drill -c \
  'SELECT (SELECT count(*) FROM "PROJECT"), (SELECT count(*) FROM "PROJECT_REVISION"), (SELECT count(*) FROM "PROJECT_REVISION_EAF"), (SELECT count(*) FROM "INSTANCE_ASSET");')
test "$counts" = "1|1|1|1"
test -f "$drill_root/restored/instance-assets/logos/recovery-drill.bin"

echo "Disposable recovery drill passed: database, revision ledger, EAF repository, and instance asset restored."
