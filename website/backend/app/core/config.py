"""Compatibility exports for validated settings.

Prefer injecting ``Settings`` into new services. These constants keep existing
modules stable while the remaining legacy code is migrated incrementally.
"""

from app.core.settings import get_settings

settings = get_settings()

ENVIRONMENT = settings.environment

# Mail configuration
MAIL_USERNAME = settings.mail_username
MAIL_PASSWORD = settings.mail_password.get_secret_value()
MAIL_FROM = settings.mail_from
MAIL_PORT = settings.mail_port
MAIL_SERVER = settings.mail_server
MAIL_STARTTLS = settings.mail_starttls
MAIL_SSL_TLS = settings.mail_ssl_tls
MAIL_USE_CREDENTIALS = settings.mail_use_credentials

# Get the frontend host from the environment variables
FRONTEND_HOST = settings.frontend_host
BACKEND_HOST = settings.backend_host
TRUSTED_HOSTS = settings.trusted_hosts
COOKIE_SECURE = settings.cookie_secure


# Get JWT secret key from environment variables
JWT_SECRET_KEY = (
    settings.jwt_secret_key.get_secret_value() if settings.jwt_secret_key else None
)

# Get JWT algorithm from environment variables
JWT_ALGORITHM = settings.jwt_algorithm

# Get JWT expiration times from environment variables
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days

# Cookie name constants
ACCESS_TOKEN_COOKIE_NAME = "elanora_session"  # noqa: S105
REFRESH_TOKEN_COOKIE_NAME = "elanora_refresh"  # noqa: S105
REFRESH_TOKEN_PATH = "/api/v1/auth/refresh"  # noqa: S105
CSRF_TOKEN_NAME = "elanora_csrf"  # noqa: S105

# ELAN Projects configuration
ELAN_PROJECTS_BASE_PATH = str(settings.elan_projects_base_path)
ELAN_BACKUPS_BASE_PATH = str(settings.elan_backups_base_path)
ELAN_MAX_FILE_SIZE_MB = settings.elan_max_file_size_mb
ELAN_MAX_BATCH_SIZE_MB = settings.elan_max_batch_size_mb

# Vite configuration
VITE_API_URL = settings.vite_api_url

# Logging configuration
LOG_LEVEL = settings.log_level
CONSOLE_LOG_LEVEL = settings.console_log_level or LOG_LEVEL
ROOT_LOG_LEVEL = settings.root_log_level
EXCEPTION_LOG_LEVEL = settings.exception_log_level
APP_NAME = settings.app_name
