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
from datetime import datetime
from typing import Any

from api.routes import analytics, hackathons, judging, participants, search, submissions, teams
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


# Initialize FastAPI app
app = FastAPI(
    title="DotHack Hackathon Platform API",
    description="""
# DotHack Hackathon Platform Backend API

A comprehensive REST API for managing hackathons, teams, submissions, and judging.

## Features

- **Hackathon Management**: Create and manage hackathons with full lifecycle support
- **Team Collaboration**: Form teams, manage members, and track team progress
- **Submission System**: Submit projects with file uploads and metadata
- **Judging Platform**: Score submissions with rubric-based evaluation
- **Participant Management**: Join hackathons, invite judges, and track participation

## Authentication

All endpoints require authentication via:
- **JWT Bearer Token**: Include in Authorization header as `Bearer <token>`
- **API Key**: Include in X-API-Key header

## Rate Limiting

API requests are rate-limited to ensure fair usage. Default limits:
- 100 requests per minute per API key
- 1000 requests per hour per API key

## Support

For questions or issues, contact: hello@ainative.studio
    """,
    version=settings.API_VERSION,
    docs_url=f"/{settings.API_VERSION}/docs",
    redoc_url=f"/{settings.API_VERSION}/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "AINative Studio Support",
        "url": "https://ainative.studio",
        "email": "hello@ainative.studio",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "Health",
            "description": "System health check and status endpoints",
        },
        {
            "name": "Hackathons",
            "description": "Hackathon CRUD operations - Create, read, update, and delete hackathons. Manage lifecycle from draft to completion.",
        },
        {
            "name": "Teams",
            "description": "Team management - Form teams, add/remove members, and manage team details for hackathon participation.",
        },
        {
            "name": "Submissions",
            "description": "Project submission management - Submit projects, upload files, and track submission status.",
        },
        {
            "name": "Judging",
            "description": "Judging and scoring - Submit scores, view leaderboards, and manage judging assignments.",
        },
        {
            "name": "Participants",
            "description": "Participant operations - Join hackathons, invite judges, and manage participant roles (BUILDER, JUDGE, ORGANIZER, MENTOR).",
        },
        {
            "name": "Analytics",
            "description": "Analytics and data export - Get hackathon statistics and export data in JSON or CSV format (ORGANIZER only).",
        },
        {
            "name": "Search",
            "description": "Semantic search - Search submissions using natural language queries and find similar projects using AI-powered vector similarity.",
        },
    ],
)


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info(f"CORS configured with allowed origins: {settings.ALLOWED_ORIGINS}")


# Register API Routes
app.include_router(hackathons.router)
logger.info("Registered hackathon management routes")

app.include_router(teams.router)
logger.info("Registered team management routes")

app.include_router(submissions.router)
logger.info("Registered submission management routes")

app.include_router(judging.router)
logger.info("Registered judging and scoring routes")

app.include_router(participants.router)
logger.info("Registered participant management routes")

app.include_router(analytics.router)
logger.info("Registered analytics and export routes")

app.include_router(search.router)
logger.info("Registered semantic search routes")


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

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "status_code": 422,
                "message": "Validation error",
                "details": exc.errors(),
                "path": str(request.url.path),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
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
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# Startup event
@app.on_event("startup")
async def startup_event() -> None:
    """
    Execute tasks on application startup.

    Logs:
    - Application started message
    - Environment configuration
    - API version
    """
    logger.info("=" * 60)
    logger.info("DotHack Backend API Starting")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Version: {settings.API_VERSION}")
    logger.info(f"Log Level: {settings.LOG_LEVEL}")
    logger.info("=" * 60)


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Execute cleanup tasks on application shutdown.
    """
    logger.info("DotHack Backend API Shutting Down")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
    )
