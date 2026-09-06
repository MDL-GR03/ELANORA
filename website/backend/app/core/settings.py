"""Validated application settings.

Environment variables are parsed once at process startup. Secrets use Pydantic's
secret type so accidental model representations cannot expose them.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus, urlparse

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.load_env import load_env

Environment = Literal["dev", "dev.docker", "test", "prod", "server"]
MINIMUM_PRODUCTION_SECRET_LENGTH = 32
DEVELOPMENT_OUTBOX_KEY = "svzSYyqHlCqGnZmcGdjsp3qNN6HvwqEAAkhiJCMdrtk="
DEVELOPMENT_SETUP_TOKEN = "elanora-local-setup"  # noqa: S105


class Settings(BaseSettings):
    """Strongly typed runtime configuration."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
        env_file_encoding="utf-8",
    )

    environment: Environment = "dev"
    database_url: SecretStr | None = None
    db_name: str | None = None
    db_user: str | None = None
    db_password: SecretStr | None = None
    db_host: str | None = None
    db_port: int | None = None
    db_echo: bool = False

    jwt_secret_key: SecretStr | None = None
    setup_token: SecretStr = SecretStr(DEVELOPMENT_SETUP_TOKEN)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=1440)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=90)

    frontend_host: str = "http://localhost:3000"
    backend_host: str = "http://localhost:8010"

    elan_projects_base_path: Path = Path("elanora_projects")
    elan_backups_base_path: Path = Path(".elanora_projects_backups")
    instance_assets_base_path: Path = Path("instance_assets")
    sync_staging_base_path: Path = Path(".elanora_sync_staging")
    elan_max_file_size_mb: int = Field(default=50, ge=1, le=2048)
    elan_max_batch_size_mb: int = Field(default=500, ge=1, le=8192)

    mail_username: str = ""
    mail_password: SecretStr = SecretStr("")
    mail_from: str = ""
    mail_port: int = Field(default=587, ge=1, le=65535)
    mail_server: str = ""
    mail_starttls: bool = True
    mail_ssl_tls: bool = False
    mail_use_credentials: bool = True
    outbox_encryption_keys: SecretStr = SecretStr(DEVELOPMENT_OUTBOX_KEY)

    vite_api_url: str = "http://localhost:8010/api/v1"
    log_level: str = "INFO"
    console_log_level: str | None = None
    root_log_level: str = "WARNING"
    exception_log_level: str = "WARNING"
    app_name: str = "elanora"

    @field_validator("frontend_host", "backend_host", mode="before")
    @classmethod
    def validate_http_origin(cls, value: object) -> str:
        """Require an absolute HTTP origin and normalize a trailing slash."""
        if not isinstance(value, str):
            raise ValueError("must be a string")
        if "://" not in value:
            value = f"http://{value}"
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("must be an absolute HTTP(S) origin")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_security_and_sizes(self) -> "Settings":
        """Reject unsafe production secrets and incoherent upload limits."""
        if self.elan_max_batch_size_mb < self.elan_max_file_size_mb:
            raise ValueError(
                "ELAN_MAX_BATCH_SIZE_MB must be at least ELAN_MAX_FILE_SIZE_MB"
            )
        if self.environment in {"prod", "server"}:
            secret = (
                self.jwt_secret_key.get_secret_value() if self.jwt_secret_key else ""
            )
            if len(secret) < MINIMUM_PRODUCTION_SECRET_LENGTH:
                raise ValueError(
                    "JWT_SECRET_KEY must contain at least 32 characters in production"
                )
            if self.setup_token.get_secret_value() == DEVELOPMENT_SETUP_TOKEN:
                raise ValueError("SETUP_TOKEN must be changed in production")
            if not self.frontend_host.startswith("https://"):
                raise ValueError("FRONTEND_HOST must use HTTPS in production")
            outbox_keys = self.outbox_encryption_keys.get_secret_value()
            if outbox_keys == DEVELOPMENT_OUTBOX_KEY:
                raise ValueError("OUTBOX_ENCRYPTION_KEYS must be changed in production")
        for key in self.outbox_encryption_keys.get_secret_value().split(","):
            try:
                Fernet(key.strip().encode("ascii"))
            except (ValueError, UnicodeEncodeError) as error:
                raise ValueError(
                    "OUTBOX_ENCRYPTION_KEYS must contain comma-separated Fernet keys"
                ) from error
        return self

    @property
    def resolved_database_url(self) -> str:
        """Return DATABASE_URL or build a PostgreSQL URL from legacy DB fields."""
        if self.database_url is not None:
            return self.database_url.get_secret_value()
        required = (
            self.db_user,
            self.db_password,
            self.db_host,
            self.db_port,
            self.db_name,
        )
        if not all(value is not None for value in required):
            raise RuntimeError("DATABASE_URL or all DB_* settings must be configured")
        if self.db_password is None:
            raise RuntimeError("DB_PASSWORD must be configured")
        password = quote_plus(self.db_password.get_secret_value())
        return (
            f"postgresql+asyncpg://{quote_plus(self.db_user or '')}:{password}"
            f"@{self.db_host}:{self.db_port}/{quote_plus(self.db_name or '')}"
        )

    @property
    def cookie_secure(self) -> bool:
        """Use secure cookies in every internet-facing environment."""
        return self.environment in {"prod", "server"}

    @property
    def trusted_hosts(self) -> list[str]:
        """Return hostnames suitable for TrustedHostMiddleware."""
        configured = urlparse(self.backend_host).hostname
        return list(dict.fromkeys(filter(None, [configured, "localhost", "127.0.0.1"])))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load dotenv compatibility files, then validate the environment once."""
    load_env()
    return Settings()
