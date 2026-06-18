"""
Authentication Routes - Proxy to AINative Studio

DotHack uses AINative Studio as its identity provider. These routes proxy
authentication requests so devs can log in with their existing AINative
credentials. No separate registration is needed.

Supported auth methods:
- Email/password login (proxied to AINative)
- JWT Bearer token (verified against AINative /v1/auth/me)
- API key (X-API-Key header, verified against AINative /v1/auth/me)
- Token refresh (proxied to AINative)
"""

import logging
from typing import Any, Optional

import httpx
from api.dependencies import get_current_user
from config import settings
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

AINATIVE_API_URL = getattr(settings, "AINATIVE_API_URL", "https://api.ainative.studio")


# --- Request/Response Models ---


class LoginRequest(BaseModel):
    """Login with existing AINative credentials."""
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Refresh an expired access token."""
    refresh_token: str


class AuthTokens(BaseModel):
    """JWT token pair returned on login."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class TokenResponse(BaseModel):
    """Login/refresh response with tokens and user info."""
    tokens: AuthTokens
    user: dict

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "tokens": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer"
            },
            "user": {
                "id": "user-uuid",
                "email": "dev@example.com",
                "name": "Dev User"
            }
        }
    })


class UserResponse(BaseModel):
    """Current authenticated user info."""
    id: str
    email: str
    name: Optional[str] = None
    email_verified: Optional[bool] = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "dev@example.com",
            "name": "Dev User",
            "email_verified": True
        }
    })


# --- Routes ---


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with AINative credentials",
    description="""
    Authenticate using your existing AINative Studio email and password.
    No separate registration needed - if you have an AINative account, you can log in.

    Returns JWT tokens (access + refresh) and user profile.
    Use the access_token as `Authorization: Bearer <token>` on subsequent requests.
    """,
)
async def login(credentials: LoginRequest):
    """Proxy login to AINative Studio."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AINATIVE_API_URL}/v1/auth/login",
                json={
                    "email": credentials.email,
                    "password": credentials.password,
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()

                if "access_token" not in data:
                    logger.error("AINative login response missing access_token")
                    raise HTTPException(
                        status_code=502,
                        detail="Invalid response from authentication service",
                    )

                return TokenResponse(
                    tokens=AuthTokens(
                        access_token=data["access_token"],
                        refresh_token=data.get("refresh_token"),
                        token_type=data.get("token_type", "bearer"),
                    ),
                    user=data.get("user", {}),
                )
            elif response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid email or password",
                )
            else:
                detail = response.text
                try:
                    detail = response.json().get("detail", detail)
                except Exception:
                    pass
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Authentication failed: {detail}",
                )

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Authentication service timeout")
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to authentication service: {str(e)}",
            )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="""
    Exchange an expired access token for a new one using your refresh token.
    The refresh token is returned from the login endpoint.
    """,
)
async def refresh_token(body: RefreshRequest):
    """Proxy token refresh to AINative Studio."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AINATIVE_API_URL}/v1/auth/refresh",
                json={"refresh_token": body.refresh_token},
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()

                if "access_token" not in data:
                    raise HTTPException(
                        status_code=502,
                        detail="Invalid response from authentication service",
                    )

                return TokenResponse(
                    tokens=AuthTokens(
                        access_token=data["access_token"],
                        refresh_token=data.get("refresh_token"),
                        token_type=data.get("token_type", "bearer"),
                    ),
                    user=data.get("user", {}),
                )
            elif response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Refresh token is invalid or expired. Please log in again.",
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Token refresh failed",
                )

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Authentication service timeout")
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to authentication service: {str(e)}",
            )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="""
    Returns the profile of the currently authenticated user.
    Requires a valid `Authorization: Bearer <token>` or `X-API-Key` header.
    """,
)
async def get_me(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse(
        id=current_user.get("id", ""),
        email=current_user.get("email", ""),
        name=current_user.get("name"),
        email_verified=current_user.get("email_verified"),
    )
