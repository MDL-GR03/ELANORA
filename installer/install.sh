#!/usr/bin/env sh
# Install ELANORA for one institution.
#
# Everything that can be derived or generated is. Setup asks only for what an
# institution alone can decide: where this installation will be reached, who it
# belongs to, and who its first administrator is. Re-running is safe: existing
# secrets are kept, and an installation that is already bootstrapped is left
# alone.
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compose_file="$repository_root/website/docker/website-prod/docker-compose.yml"
env_file="$repository_root/website/env/.env.prod"
env_example="$repository_root/website/env/.env.prod.example"
compose_project="elanora"
check_only=0

hostname_url=""
institution_name=""
admin_email=""
admin_username="admin"
admin_first_name=""
admin_last_name=""
timezone="UTC"

usage() {
  cat <<'USAGE'
Usage: installer/install.sh [options]

  --url URL                 Where researchers will reach this installation,
                            for example https://elanora.example.org
  --institution NAME        The institution this installation belongs to
  --admin-email EMAIL       First administrator's email address
  --admin-username NAME     First administrator's username (default: admin)
  --admin-first-name NAME   First administrator's given name
  --admin-last-name NAME    First administrator's family name
  --timezone ZONE           Institution timezone (default: UTC)
  --check                   Verify prerequisites and configuration, change nothing
  -h, --help                Show this message

Anything not given is asked for, when a terminal is available. Every secret is
generated; none is ever asked for.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --url) hostname_url="$2"; shift 2 ;;
    --institution) institution_name="$2"; shift 2 ;;
    --admin-email) admin_email="$2"; shift 2 ;;
    --admin-username) admin_username="$2"; shift 2 ;;
    --admin-first-name) admin_first_name="$2"; shift 2 ;;
    --admin-last-name) admin_last_name="$2"; shift 2 ;;
    --timezone) timezone="$2"; shift 2 ;;
    --check) check_only=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

fail() {
  echo "Setup stopped: $1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is required but was not found."
}

ask() {
  # ask VARIABLE "Question" [default]
  variable=$1
  question=$2
  default=${3:-}
  current=$(eval "printf '%s' \"\${$variable}\"")
  [ -n "$current" ] && return 0
  [ -t 0 ] || fail "$question must be given with a command-line option when setup is not interactive."
  if [ -n "$default" ]; then
    printf '%s [%s]: ' "$question" "$default"
  else
    printf '%s: ' "$question"
  fi
  read -r answer
  [ -z "$answer" ] && answer=$default
  [ -z "$answer" ] && fail "$question is required."
  eval "$variable=\$answer"
}

echo "== Checking prerequisites"
require_command docker
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required."
docker info >/dev/null 2>&1 || fail "Docker is installed but not running, or this account cannot use it."
[ -f "$compose_file" ] || fail "Composition not found at $compose_file."
echo "   Docker and the composition are available."

if [ "$check_only" -eq 1 ]; then
  echo "== Configuration"
  if [ -f "$env_file" ]; then
    echo "   $env_file exists; its secrets would be kept."
  else
    echo "   $env_file would be created from the example, with generated secrets."
  fi
  echo "Check complete. Nothing was changed."
  exit 0
fi

echo "== Answering what only this institution knows"
ask hostname_url "Where will researchers reach this installation?" "https://localhost"
ask institution_name "Which institution does this installation belong to?"
ask admin_email "First administrator's email address"
ask admin_first_name "First administrator's given name"
ask admin_last_name "First administrator's family name"

domain=$(printf '%s' "$hostname_url" | sed -e 's#^[a-zA-Z]*://##' -e 's#[:/].*##')
[ -n "$domain" ] || fail "Could not read a hostname from $hostname_url."

echo "== Preparing configuration"
if [ ! -f "$env_file" ]; then
  mkdir -p "$(dirname "$env_file")"
  cp "$env_example" "$env_file"
  chmod 600 "$env_file"
  echo "   Created $env_file from the example."
fi

set_value() {
  key=$1
  value=$2
  if grep -q "^${key}=" "$env_file"; then
    tmp=$(mktemp)
    grep -v "^${key}=" "$env_file" > "$tmp"
    printf '%s=%s\n' "$key" "$value" >> "$tmp"
    cat "$tmp" > "$env_file"
    rm -f "$tmp"
  else
    printf '%s=%s\n' "$key" "$value" >> "$env_file"
  fi
}

set_value ENVIRONMENT prod
set_value FRONTEND_HOST "$hostname_url"
set_value BACKEND_HOST "$hostname_url"
set_value VITE_API_URL "$hostname_url/api/v1"
echo "   Recorded where this installation is reached."

echo "== Generating secrets"
# Generated inside the image so the host needs no Python environment.
docker compose -p "$compose_project" -f "$compose_file" run --rm --no-deps \
  --volume "$repository_root/website/env:/app/website/env" \
  backend python -m app.cli.setup_installation --env-file /app/website/env/.env.prod
chmod 600 "$env_file"

echo "== Starting ELANORA"
docker compose -p "$compose_project" -f "$compose_file" up --build --wait

echo "== Creating the institution and its first administrator"
if docker compose -p "$compose_project" -f "$compose_file" exec -T backend \
  python -c "
import asyncio
from sqlalchemy import func, select
from app.db.database import close_database, get_session_maker, init_database
from app.model.instance import Instance

async def main():
    init_database()
    try:
        async with get_session_maker()() as db:
            print(int(await db.scalar(select(func.count()).select_from(Instance)) or 0))
    finally:
        await close_database()

asyncio.run(main())
" | tail -1 | grep -q '^0$'; then
  admin_password=$(docker compose -p "$compose_project" -f "$compose_file" exec -T backend \
    python -c "import secrets; print(secrets.token_urlsafe(18))" | tr -d '\r\n')
  printf '%s\n' "$admin_password" | docker compose -p "$compose_project" -f "$compose_file" \
    exec -T backend python -m app.cli.bootstrap \
      --instance-name "$institution_name" \
      --institution-name "$institution_name" \
      --contact-email "$admin_email" \
      --domain "$domain" \
      --timezone "$timezone" \
      --admin-username "$admin_username" \
      --admin-email "$admin_email" \
      --admin-first-name "$admin_first_name" \
      --admin-last-name "$admin_last_name" \
      --admin-affiliation "$institution_name" \
      --admin-department "$institution_name" \
      --password-stdin
  echo
  echo "   Sign in as '$admin_username' with this password, then change it:"
  echo
  echo "       $admin_password"
  echo
else
  echo "   An institution already exists; leaving it as it is."
fi

cat <<SUMMARY

ELANORA is running at $hostname_url

It maintains itself from here: it backs itself up every day, verifies the
newest backup weekly, applies each project's retention policy, and watches its
disk. The administrator operations page reports what it actually did.

Backups are written to $repository_root/backups by default, which is on this
machine. Point that at storage elsewhere before trusting it with research data
that cannot be re-collected; see docs/DISASTER_RECOVERY.md.
SUMMARY
