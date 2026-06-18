"""
Authentication Routes - Proxy to AINative Studio

This module provides authentication endpoints that proxy to AINative Studio.
DotHack does not implement its own authentication system.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
import httpx
from typing import Optional
import os

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

AINATIVE_API_URL = os.getenv("AINATIVE_API_URL", "https://api.ainative.studio")


class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Registration request model"""
    email: EmailStr
    password: str
    name: Optional[str] = None


class AuthTokens(BaseModel):
    """Authentication tokens"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class TokenResponse(BaseModel):
    """Token response model"""
    tokens: AuthTokens
    user: dict


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    """
    Proxy login request to AINative Studio

    Args:
        credentials: User email and password

    Returns:
        TokenResponse with access_token and user info

    Raises:
        HTTPException: If authentication fails
    """
    async with httpx.AsyncClient() as client:
        try:
            # Forward login request to AINative Studio
            response = await client.post(
                f"{AINATIVE_API_URL}/v1/public/auth/login-json",
                json={
                    "email": credentials.email,
                    "password": credentials.password
                },
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()

                # Ensure we have the required fields
                if "access_token" not in data:
                    raise HTTPException(
                        status_code=500,
                        detail="Invalid response from authentication service"
                    )

                return TokenResponse(
                    tokens=AuthTokens(
                        access_token=data["access_token"],
                        refresh_token=data.get("refresh_token"),
                        token_type=data.get("token_type", "bearer")
                    ),
                    user=data.get("user", {})
                )
            elif response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid email or password"
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Authentication failed: {response.text}"
                )

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Authentication service timeout"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to authentication service: {str(e)}"
            )


@router.post("/register", response_model=TokenResponse)
async def register(user_data: RegisterRequest):
    """
    Proxy registration request to AINative Studio

    Args:
        user_data: User registration information

    Returns:
        TokenResponse with access_token and user info

    Raises:
        HTTPException: If registration fails
    """
    async with httpx.AsyncClient() as client:
        try:
            # Forward registration request to AINative Studio
            payload = {
                "email": user_data.email,
                "password": user_data.password
            }
            if user_data.name:
                payload["name"] = user_data.name

            response = await client.post(
                f"{AINATIVE_API_URL}/v1/public/auth/register",
                json=payload,
                timeout=10.0
            )

            if response.status_code == 201:
                data = response.json()

                # Ensure we have the required fields
                if "access_token" not in data:
                    raise HTTPException(
                        status_code=500,
                        detail="Invalid response from authentication service"
                    )

                return TokenResponse(
                    tokens=AuthTokens(
                        access_token=data["access_token"],
                        refresh_token=data.get("refresh_token"),
                        token_type=data.get("token_type", "bearer")
                    ),
                    user=data.get("user", {})
                )
            elif response.status_code == 400:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid registration data or email already exists"
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Registration failed: {response.text}"
                )

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Authentication service timeout"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to authentication service: {str(e)}"
            )


@router.get("/me")
async def get_me(token: str = Depends(lambda: None)):
    """
    Get current user info from token
    This endpoint is handled by the authentication dependency in dependencies.py

    Returns:
        User information
    """
    # This is handled by the get_current_user dependency
    # which is already implemented in api/dependencies.py
    pass
