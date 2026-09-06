from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.effective_naming_standard import (
    router as effective_naming_standard_router,
)
from app.api.v1.file_type import router as file_type_router
from app.api.v1.git import router as git_router
from app.api.v1.instance import router as instance_router
from app.api.v1.invitation import router as invitation_router
from app.api.v1.location import router as location_router
from app.api.v1.notification import router as notification_router
from app.api.v1.project_associations import router as project_associations_router
from app.api.v1.project_location_file_type import (
    router as project_location_file_type_router,
)
from app.api.v1.project_naming_standard import router as project_naming_standard_router
from app.api.v1.protocol import router as protocol_router
from app.api.v1.review import router as review_router
from app.api.v1.setup import router as setup_router
from app.api.v1.tier import router as tier_router
from app.api.v1.user import router as user_router
from app.core.centralized_logging import get_logger
from app.core.config import ENVIRONMENT, FRONTEND_HOST, TRUSTED_HOSTS
from app.core.exception_handler import (
    add_general_exception_handler,
    rate_limit_exception_handler,
    validation_exception_handler,
)
from app.core.limiter import limiter
from app.db.database import close_database, init_database
from app.middleware.csrf import CSRFMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.utils.project_backup import create_hidden_folder_in_root

# Get logger (this will automatically call setup_application_logging)
logger = get_logger()

API_V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and dispose shared infrastructure with the ASGI process."""
    init_database()
    backup_root = create_hidden_folder_in_root()
    logger.info(f"Backup folder created at: {backup_root}")

    yield
    await close_database()


app = FastAPI(
    title="ELANORA - ELAN Collaboration Platform",
    description="API for collaborative ELAN annotation projects",
    version="1.0.0",
    # Disable documentation for production
    docs_url="/docs" if ENVIRONMENT != "server" else None,
    redoc_url="/redoc" if ENVIRONMENT != "server" else None,
    openapi_url="/openapi.json" if ENVIRONMENT != "server" else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, add_general_exception_handler())

# API version prefix constant
API_V1_PREFIX = "/api/v1"

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_HOST],
    allow_credentials=True,  # Allow cookies (essential for HTTP-only cookies)
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers (including cookies)
)

# Add the CSRF middleware
app.add_middleware(CSRFMiddleware)

# Add your own security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# GZip middleware configuration (for compression)
app.add_middleware(GZipMiddleware, minimum_size=500)

# TrustedHostMiddleware configuration
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=TRUSTED_HOSTS,
)

# Include API routers
app.include_router(git_router, prefix=f"{API_V1_PREFIX}/git", tags=["GIT"])
app.include_router(review_router, prefix=f"{API_V1_PREFIX}/review", tags=["REVIEW"])
app.include_router(tier_router, prefix=f"{API_V1_PREFIX}/tier", tags=["TIER"])
app.include_router(user_router, prefix=f"{API_V1_PREFIX}/user", tags=["USER"])
app.include_router(auth_router, prefix=f"{API_V1_PREFIX}/auth", tags=["AUTHENTICATION"])
app.include_router(
    invitation_router, prefix=f"{API_V1_PREFIX}/invitation", tags=["INVITATION"]
)
app.include_router(
    location_router, prefix=f"{API_V1_PREFIX}/location", tags=["LOCATION"]
)
app.include_router(
    instance_router, prefix=f"{API_V1_PREFIX}/instance", tags=["INSTANCE"]
)
app.include_router(
    project_associations_router,
    prefix=f"{API_V1_PREFIX}/project-associations",
    tags=["PROJECT ASSOCIATIONS"],
)
app.include_router(
    project_naming_standard_router,
    prefix=f"{API_V1_PREFIX}/project-naming-standard",
    tags=["PROJECT NAMING STANDARD"],
)
app.include_router(protocol_router, prefix=API_V1_PREFIX, tags=["PROTOCOL"])
app.include_router(setup_router, prefix=f"{API_V1_PREFIX}/setup", tags=["SETUP"])
app.include_router(
    file_type_router, prefix=f"{API_V1_PREFIX}/file-type", tags=["FILE TYPE"]
)
app.include_router(
    effective_naming_standard_router,
    prefix=f"{API_V1_PREFIX}/effective-naming-standard",
    tags=["EFFECTIVE NAMING STANDARD"],
)

app.include_router(
    project_location_file_type_router,
    prefix=f"{API_V1_PREFIX}/project-location-file-type",
    tags=["PROJECT LOCATION FILE TYPE"],
)

app.include_router(
    notification_router, prefix=f"{API_V1_PREFIX}/notifications", tags=["NOTIFICATION"]
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint for API health check."""
    return {
        "message": "ELANORA API is running",
        "version": "1.0.0",
        "status": "healthy",
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
