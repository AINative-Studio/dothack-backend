"""
FastAPI application entry point.

Initializes the FastAPI app with:
- CORS configuration
- Global exception handlers
- Structured logging
- API versioning
- Health check endpoint
"""

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from api.routes import (
    analytics,
    auth,
    dashboard,
    export,
    featured_hackathons,
    files,
    hackathons,
    hackathon_themes,
    invitations,
    judging,
    participants,
    prizes,
    projects,
    recommendations,
    rubrics,
    search,
    submissions,
    teams,
    tracks,
)
from config import settings
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


# Configure structured logging
def setup_logging() -> None:
    """
    Configure structured logging with JSON format.

    Logs include:
    - Timestamp
    - Log level
    - Message
    - Module name
    - Request ID (when available)
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info("=" * 60)
    logger.info("DotHack Backend API Starting")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Version: {settings.API_VERSION}")
    logger.info(f"Log Level: {settings.LOG_LEVEL}")
    logger.info("=" * 60)
    yield
    # Shutdown
    logger.info("DotHack Backend API Shutting Down")


# Initialize FastAPI app
app = FastAPI(
    title="DotHack Backend API",
    description="Lead enrichment and outreach automation platform",
    version=settings.API_VERSION,
    docs_url=f"/{settings.API_VERSION}/docs",
    redoc_url=f"/{settings.API_VERSION}/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# CORS Configuration
allowed_origins = (
    settings.ALLOWED_ORIGINS
    if isinstance(settings.ALLOWED_ORIGINS, list)
    else [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "Accept"],
)

# Rate limiting on auth endpoints (100 req/min per IP)
from middleware.rate_limit import RateLimitMiddleware

app.add_middleware(RateLimitMiddleware, limit=100, window=60)

logger.info(f"CORS configured with allowed origins: {settings.ALLOWED_ORIGINS}")
logger.info("Rate limiting middleware enabled (100 req/min per IP)")


# Register API Routes
app.include_router(auth.router)
app.include_router(hackathons.router)
app.include_router(hackathon_themes.router)
app.include_router(tracks.router)
app.include_router(prizes.router)
app.include_router(participants.router)
app.include_router(teams.router)
app.include_router(projects.router)
app.include_router(submissions.router)
app.include_router(judging.router)
app.include_router(rubrics.router)
app.include_router(invitations.router)
app.include_router(featured_hackathons.router)
app.include_router(dashboard.router)
app.include_router(analytics.router)
app.include_router(export.router)
app.include_router(search.router)
app.include_router(recommendations.router)
app.include_router(files.router)

logger.info("Registered hackathon CRUD routes")
logger.info("Registered hackathon theme routes")
logger.info("Registered tracks routes")
logger.info("Registered prizes routes")
logger.info("Registered participant management routes")
logger.info("Registered team management routes")
logger.info("Registered project management routes")
logger.info("Registered submission routes")
logger.info("Registered judging routes")
logger.info("Registered rubrics routes")
logger.info("Registered invitations routes")
logger.info("Registered featured hackathons routes")
logger.info("Registered dashboard routes")
logger.info("Registered analytics routes")
logger.info("Registered export routes")
logger.info("Registered search routes")
logger.info("Registered recommendations routes")
logger.info("Registered file upload routes")


# Global Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions with consistent JSON response format.

    Args:
        request: The incoming request
        exc: The HTTP exception

    Returns:
        JSONResponse with error details
    """
    logger.error(f"HTTP exception: {exc.status_code} - {exc.detail} - " f"Path: {request.url.path}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "status_code": exc.status_code,
                "message": exc.detail,
                "path": str(request.url.path),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle request validation errors with detailed error messages.

    Args:
        request: The incoming request
        exc: The validation error

    Returns:
        JSONResponse with validation error details
    """
    logger.error(f"Validation error on {request.url.path}: {exc.errors()}")

    # Sanitize errors to ensure JSON serializability
    sanitized_errors = []
    for error in exc.errors():
        sanitized = {k: v for k, v in error.items() if k != "ctx"}
        if "ctx" in error and error["ctx"]:
            sanitized["ctx"] = {k: str(v) for k, v in error["ctx"].items()}
        sanitized_errors.append(sanitized)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "status_code": 422,
                "message": "Validation error",
                "details": sanitized_errors,
                "path": str(request.url.path),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Handle ZeroDB rate limit errors with 429 instead of 500
    from integrations.zerodb.exceptions import ZeroDBRateLimitError
    if isinstance(exc, ZeroDBRateLimitError):
        logger.warning(f"Rate limited on {request.url.path}")
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "status_code": 429,
                    "message": "Too many requests. Please wait a moment and try again.",
                    "path": str(request.url.path),
                    "retry_after": 10,
                }
            },
            headers={"Retry-After": "10"},
        )
    """
    Handle unexpected exceptions with generic error response.

    Args:
        request: The incoming request
        exc: The exception

    Returns:
        JSONResponse with generic error message
    """
    logger.exception(f"Unhandled exception on {request.url.path}: {str(exc)}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "status_code": 500,
                "message": "Internal server error",
                "path": str(request.url.path),
            }
        },
    )


# Root Endpoint
@app.get("/", tags=["Root"])
async def root() -> dict[str, Any]:
    """
    API root endpoint.

    Returns:
        Dictionary with API information and available endpoints

    Response Schema:
        {
            "name": "DotHack Backend API",
            "version": "v1",
            "status": "running",
            "docs": "/v1/docs"
        }
    """
    return {
        "name": "DotHack Backend API",
        "version": settings.API_VERSION,
        "status": "running",
        "docs": f"/{settings.API_VERSION}/docs",
        "openapi": "/openapi.json",
    }


# Health Check Endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint.

    Returns:
        Dictionary with health status and timestamp

    Response Schema:
        {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00.000000"
        }
    """
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
    )
