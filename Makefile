COMPOSE := docker compose -f website/docker/website-dev/docker-compose.yml
LEGACY_COMPOSE := docker compose -f website/docker/legacy-migration/docker-compose.yml
TEST_COMPOSE := docker compose -f website/docker/website-test/docker-compose.yml
TEST_DATABASE_URL := postgresql+asyncpg://elanora_test:elanora-test-only@127.0.0.1:5418/elanora_test
ELANORA_USER ?= MDL
export ELANORA_DEV_UID ?= $(shell id -u)
export ELANORA_DEV_GID ?= $(shell id -g)

.DEFAULT_GOAL := help

.PHONY: help dev-up dev-down dev-logs dev-status dev-health dev-db-current dev-db-history dev-db-schema dev-bootstrap dev-reset-password dev-dispatch-outbox dev-email-smoke dev-check-integrity recovery-verify test-db-up test-db-reset test-db-down test-integration test-e2e legacy-validate legacy-status legacy-down backend-check frontend-check check

help:
	@echo "ELANORA development commands"
	@echo "  make dev-up         Build, migrate, and start the local website"
	@echo "  make dev-bootstrap  Create the first local institution administrator"
	@echo "  make dev-reset-password  Set a new password for ELANORA_USER (default: MDL)"
	@echo "  make dev-dispatch-outbox  Immediately retry queued outbound messages"
	@echo "  make dev-email-smoke  Send a test message to Mailpit at localhost:8025"
	@echo "  make dev-check-integrity  Scan accepted project data without repairing it"
	@echo "  make recovery-verify RECOVERY_BUNDLE=/path/file.elanora"
	@echo "  make dev-logs       Follow development container logs"
	@echo "  make dev-status     Show container status"
	@echo "  make dev-health     Check frontend and backend URLs"
	@echo "  make dev-db-current Show the migration applied to development PostgreSQL"
	@echo "  make dev-db-history Show the complete versioned schema history"
	@echo "  make dev-db-schema  Print the current PostgreSQL schema (no table data)"
	@echo "  make dev-down       Stop containers without deleting database data"
	@echo "  make test-db-up     Start and migrate disposable PostgreSQL"
	@echo "  make test-db-reset  Recreate and migrate disposable PostgreSQL"
	@echo "  make test-db-down   Destroy the disposable test database"
	@echo "  make test-integration  Run database tests against PostgreSQL"
	@echo "  make test-e2e        Run browser workflow tests with Playwright"
	@echo "  make legacy-validate  Import the MySQL-era dataset into isolated PostgreSQL"
	@echo "  make legacy-status    Show the isolated migration services"
	@echo "  make legacy-down      Stop migration services; keep validation data"
	@echo "  make check          Run backend and frontend quality checks"

dev-up:
	$(COMPOSE) up --build --wait -d
	@echo "ELANORA: http://localhost:8777"
	@echo "First-run setup token: elanora-local-setup"
	@echo "API docs: http://localhost:8018/docs"

dev-down:
	$(COMPOSE) down

dev-logs:
	$(COMPOSE) logs -f

dev-status:
	$(COMPOSE) ps

dev-health:
	curl --fail --silent --show-error http://localhost:8018/health
	@echo
	curl --fail --silent --show-error --output /dev/null http://localhost:8777
	@echo "Frontend is reachable"

dev-db-current:
	$(COMPOSE) exec backend alembic current

dev-db-history:
	$(COMPOSE) exec backend alembic history --verbose

dev-db-schema:
	$(COMPOSE) exec -T db pg_dump --schema-only --no-owner --no-privileges -U elanora -d elanora

dev-bootstrap:
	$(COMPOSE) exec backend elanora-bootstrap \
		--instance-name "Local ELANORA" \
		--institution-name "Development Institute" \
		--contact-email "admin@example.org" \
		--domain "example.org" \
		--timezone "Europe/Paris" \
		--default-language "en" \
		--admin-username "administrator" \
		--admin-email "administrator@example.org" \
		--admin-first-name "Local" \
		--admin-last-name "Administrator" \
		--admin-affiliation "Development Institute" \
		--admin-department "Research IT"

dev-reset-password:
	$(COMPOSE) exec backend elanora-reset-password --username "$(ELANORA_USER)"

dev-dispatch-outbox:
	$(COMPOSE) exec backend python -m app.cli.dispatch_outbox --once

dev-email-smoke:
	$(COMPOSE) exec backend python -m app.cli.queue_test_account_emails
	curl --fail --silent --show-error --retry 8 --retry-all-errors "http://localhost:8025/view/latest.txt?query=to:verification-smoke@dev.elanora.example.org" | rg --quiet "VERIFY-OUTBOX-123"
	curl --fail --silent --show-error --retry 8 --retry-all-errors "http://localhost:8025/view/latest.txt?query=to:reset-smoke@dev.elanora.example.org" | rg --quiet "RESET-OUTBOX-456"
	@echo "Mailpit captured encrypted-outbox verification and password-reset messages."
	@echo "Open Mailpit: http://localhost:8025"

dev-check-integrity:
	$(COMPOSE) exec backend elanora-check-integrity

recovery-verify:
	test -n "$(RECOVERY_BUNDLE)"
	cd website/backend && poetry run elanora-disaster-recovery verify "$(abspath $(RECOVERY_BUNDLE))"

test-db-up:
	$(TEST_COMPOSE) up --wait -d
	cd website/backend && ENVIRONMENT=test DATABASE_URL="$(TEST_DATABASE_URL)" poetry run alembic upgrade head

test-db-reset:
	$(TEST_COMPOSE) down --volumes --remove-orphans
	$(MAKE) test-db-up

test-db-down:
	$(TEST_COMPOSE) down --volumes --remove-orphans

test-integration: test-db-reset
	cd website/backend && ENVIRONMENT=test DATABASE_URL="$(TEST_DATABASE_URL)" poetry run alembic downgrade -1
	cd website/backend && ENVIRONMENT=test DATABASE_URL="$(TEST_DATABASE_URL)" poetry run alembic upgrade head
	cd website/backend && ENVIRONMENT=test DATABASE_URL="$(TEST_DATABASE_URL)" poetry run alembic check
	cd website/backend && ENVIRONMENT=test TEST_DATABASE_URL="$(TEST_DATABASE_URL)" poetry run pytest tests/integration
	$(TEST_COMPOSE) down --volumes --remove-orphans

test-e2e:
	cd website/frontend && npm run test:e2e

legacy-validate:
	$(LEGACY_COMPOSE) build importer
	$(LEGACY_COMPOSE) up --wait -d db
	$(LEGACY_COMPOSE) run --rm importer

legacy-status:
	$(LEGACY_COMPOSE) ps -a

legacy-down:
	$(LEGACY_COMPOSE) down

backend-check:
	cd website/backend && poetry run ruff format --check .
	cd website/backend && poetry run ruff check .
	cd website/backend && poetry run mypy --config-file mypy.ini
	cd website/backend && poetry run pytest tests/unit
	$(MAKE) test-integration

frontend-check:
	cd website/frontend && npm run lint
	cd website/frontend && npm run stylelint
	cd website/frontend && npm run format
	cd website/frontend && npm run i18n:check
	cd website/frontend && npm run test
	cd website/frontend && npm run build

check: backend-check frontend-check
