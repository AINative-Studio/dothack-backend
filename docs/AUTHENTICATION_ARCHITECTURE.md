# DotHack Backend - Authentication Architecture

**Status:** ✅ MANDATORY ARCHITECTURE DECISION
**Version:** 1.0
**Last Updated:** 2025-12-28

---

## Executive Summary

**DotHack Backend MUST use the existing AINative Studio authentication system.**

**DO NOT build standalone authentication.** All user registration, login, OAuth, and session management is handled by the centralized AINative Auth API at `https://api.ainative.studio/v1/auth/*`.

---

## Why Use AINative Authentication?

### ✅ Benefits

| Benefit | Impact |
|---------|--------|
| **Centralized User Management** | Users have ONE account across all AINative products (DotHack, ZeroDB, QNN, etc.) |
| **Single Sign-On (SSO)** | Users login once, access all AINative services |
| **OAuth Pre-Built** | GitHub and LinkedIn OAuth already implemented and tested |
| **Production Security** | bcrypt password hashing, JWT tokens, token blacklisting |
| **API Key Management** | Server-to-server authentication built-in |
| **Zero Maintenance** | No need to maintain auth infrastructure, security updates, or password reset flows |
| **Unified UX** | Consistent authentication experience across AINative platform |

### ❌ Risks of Standalone Auth

| Risk | Consequence |
|------|-------------|
| **User Fragmentation** | Users need separate accounts for DotHack vs other AINative products |
| **Security Burden** | DotHack team responsible for password security, OAuth, token management |
| **Duplicate Work** | Re-implementing features that already exist in production |
| **Maintenance Cost** | Ongoing security patches, password reset emails, OAuth updates |
| **Poor UX** | Users frustrated by separate login systems |

---

## Architecture Overview

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DotHack Ecosystem                               │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐         ┌──────────────┐
│  Web Frontend    │         │  Mobile App      │         │  CLI Tools   │
│  (React/Next.js) │         │  (React Native)  │         │  (Python)    │
└────────┬─────────┘         └────────┬─────────┘         └──────┬───────┘
         │                            │                           │
         └────────────────────────────┼───────────────────────────┘
                                      │
                        1. User Authentication Flow
                                      │
                  ┌───────────────────▼───────────────────┐
                  │     AINative Authentication API       │
                  │    https://api.ainative.studio        │
                  │                                       │
                  │  ┌─────────────────────────────────┐ │
                  │  │  /v1/auth/register             │ │
                  │  │  /v1/auth/login                │ │
                  │  │  /v1/auth/me (verify token)    │ │
                  │  │  /v1/auth/refresh              │ │
                  │  │  /v1/auth/github/callback      │ │
                  │  │  /v1/auth/linkedin/callback    │ │
                  │  └─────────────────────────────────┘ │
                  │                                       │
                  │  Returns: JWT Token + User Info       │
                  └───────────────────┬───────────────────┘
                                      │
                        2. JWT Token Response
                                      │
         ┌────────────────────────────▼────────────────────────────┐
         │                DotHack Backend API                      │
         │              (Python FastAPI + ZeroDB)                  │
         │                                                         │
         │  ┌──────────────────────────────────────────────────┐  │
         │  │          Authentication Middleware                │  │
         │  │                                                   │  │
         │  │  Step 1: Extract token from:                     │  │
         │  │    • Authorization: Bearer {token}               │  │
         │  │    • X-API-Key: {api_key}                        │  │
         │  │                                                   │  │
         │  │  Step 2: Verify with AINative                    │  │
         │  │    GET /v1/auth/me                               │  │
         │  │    → Returns user: {id, email, name}             │  │
         │  │                                                   │  │
         │  │  Step 3: Check role in ZeroDB                    │  │
         │  │    Query hackathon_participants                  │  │
         │  │    WHERE participant_id = user.id                │  │
         │  │                                                   │  │
         │  │  Step 4: Grant/Deny Access                       │  │
         │  │    ✓ Role matches requirement                    │  │
         │  │    ✗ Return 403 Forbidden                        │  │
         │  └──────────────────────────────────────────────────┘  │
         │                                                         │
         │  ┌──────────────────────────────────────────────────┐  │
         │  │            Protected Endpoints                    │  │
         │  │                                                   │  │
         │  │  • POST /api/v1/hackathons                       │  │
         │  │  • POST /api/v1/hackathons/{id}/join             │  │
         │  │  • PATCH /api/v1/hackathons/{id}                 │  │
         │  │  • POST /api/v1/projects/{id}/submit             │  │
         │  │  • POST /api/v1/submissions/{id}/score           │  │
         │  └──────────────────────────────────────────────────┘  │
         └─────────────────────────┬───────────────────────────────┘
                                   │
                     3. Query/Store Role Data
                                   │
                  ┌────────────────▼────────────────┐
                  │         ZeroDB Storage          │
                  │  (NoSQL + Vector + PostgreSQL)  │
                  │                                 │
                  │  Table: hackathon_participants  │
                  │  {                              │
                  │    hackathon_id: uuid,          │
                  │    participant_id: uuid,  ◄─────┼─── AINative user.id
                  │    role: ORGANIZER|BUILDER|     │
                  │          JUDGE|MENTOR,          │
                  │    metadata: {                  │
                  │      ainative_user_email,       │
                  │      ainative_user_name         │
                  │    }                            │
                  │  }                              │
                  └─────────────────────────────────┘
```

### Detailed Authentication Flow

```
┌─────────────┐
│   Client    │
│ (Frontend)  │
└──────┬──────┘
       │
       │ 1. POST /v1/auth/login
       │    { email, password }
       │
       ▼
┌─────────────────────────┐
│  AINative Auth API      │
│                         │
│  1. Validate password   │
│  2. Generate JWT token  │
│  3. Create session      │
└────────┬────────────────┘
         │
         │ 2. Response
         │    { access_token, refresh_token, user }
         │
         ▼
┌─────────────┐
│   Client    │
│  Stores:    │
│  - JWT      │
│  - Refresh  │
└──────┬──────┘
       │
       │ 3. POST /api/v1/hackathons
       │    Authorization: Bearer {JWT}
       │    { name: "My Hackathon" }
       │
       ▼
┌─────────────────────────────────┐
│  DotHack Backend                │
│                                 │
│  get_current_user() dependency: │
│                                 │
│  1. Extract JWT from header     │
│  2. GET /v1/auth/me (AINative)  │
│     Authorization: Bearer {JWT} │
└────────┬────────────────────────┘
         │
         │ 4. Response
         │    { id: "uuid", email: "user@example.com", ... }
         │
         ▼
┌─────────────────────────────────┐
│  DotHack Backend                │
│                                 │
│  1. Create hackathon in ZeroDB  │
│  2. Add user as ORGANIZER       │
│     INSERT INTO                 │
│     hackathon_participants      │
│     {                           │
│       hackathon_id,             │
│       participant_id: user.id   │
│       role: "ORGANIZER"         │
│     }                           │
└────────┬────────────────────────┘
         │
         │ 5. Response
         │    { hackathon_id, name, status, ... }
         │
         ▼
┌─────────────┐
│   Client    │
│  Displays   │
│  Hackathon  │
└─────────────┘
```

---

## Data Model

### Users (Managed by AINative)

**Table:** `users` (PostgreSQL @ AINative)

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT NOT NULL,
  email_verified BOOLEAN DEFAULT FALSE,
  github_id TEXT UNIQUE,
  linkedin_id TEXT UNIQUE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

**DotHack does NOT manage this table. It's read-only via AINative API.**

### Hackathon Participants (Managed by DotHack)

**Table:** `hackathon_participants` (ZeroDB @ DotHack)

```json
{
  "id": "uuid",
  "hackathon_id": "uuid",
  "participant_id": "uuid",  // AINative user.id
  "role": "ORGANIZER | BUILDER | JUDGE | MENTOR",
  "metadata": {
    "ainative_user_email": "user@example.com",
    "ainative_user_name": "John Doe",
    "joined_via": "github_oauth | linkedin_oauth | email_password"
  },
  "joined_at": "2025-12-28T10:00:00Z"
}
```

**DotHack manages this table via ZeroDB.**

---

## Implementation Steps

### Step 1: Install AINative SDK (Optional)

```bash
cd python-api
pip install ainative-sdk
```

Or implement HTTP client wrapper (recommended for full control):

```python
# python-api/integrations/ainative/auth_client.py
import httpx
from typing import Optional, Dict, Any

class AINativeAuthClient:
    def __init__(self, base_url: str = "https://api.ainative.studio"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token via AINative /v1/auth/me"""
        try:
            response = await self.client.get(
                "/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            return response.json() if response.status_code == 200 else None
        except Exception:
            return None
```

### Step 2: Create Authentication Dependency

```python
# python-api/api/dependencies.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer

from integrations.ainative.auth_client import AINativeAuthClient

security = HTTPBearer()
auth_client = AINativeAuthClient()

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Authenticate user via AINative

    Returns user dict:
    {
      "id": "uuid",
      "email": "user@example.com",
      "name": "John Doe",
      "email_verified": true
    }
    """
    token = credentials.credentials
    user = await auth_client.verify_token(token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    return user
```

### Step 3: Protect Endpoints

```python
# python-api/api/routes/hackathons.py
from fastapi import APIRouter, Depends
from api.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/hackathons")

@router.post("/")
async def create_hackathon(
    hackathon_data: HackathonCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create hackathon (requires authentication)
    """
    user_id = current_user["id"]
    user_email = current_user["email"]

    # Create hackathon
    hackathon = await zerodb.tables.create_row(
        "hackathons",
        data={
            "hackathon_id": str(uuid.uuid4()),
            "name": hackathon_data.name,
            "status": "DRAFT"
        }
    )

    # Add organizer to participants
    await zerodb.tables.create_row(
        "hackathon_participants",
        data={
            "hackathon_id": hackathon["hackathon_id"],
            "participant_id": user_id,  # AINative user.id
            "role": "ORGANIZER",
            "metadata": {
                "ainative_user_email": user_email,
                "ainative_user_name": current_user["name"]
            }
        }
    )

    return hackathon
```

### Step 4: Implement Role Checking

```python
# python-api/services/authorization.py
from fastapi import HTTPException, status

async def check_role(
    hackathon_id: str,
    user_id: str,
    required_role: str,
    zerodb_client
):
    """
    Verify user has required role for hackathon
    """
    participant = await zerodb_client.tables.query_rows(
        "hackathon_participants",
        filter={
            "hackathon_id": hackathon_id,
            "participant_id": user_id,
            "role": required_role
        }
    )

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only {required_role}s can perform this action"
        )

# Usage in endpoint
@router.patch("/{hackathon_id}")
async def update_hackathon(
    hackathon_id: str,
    update_data: HackathonUpdate,
    current_user: dict = Depends(get_current_user)
):
    # Check organizer role
    await check_role(hackathon_id, current_user["id"], "ORGANIZER", zerodb_client)

    # Update hackathon
    # ...
```

---

## User Flows

### Flow 1: User Registration

```
1. Frontend → AINative Auth API
   POST /v1/auth/register
   {
     "email": "builder@example.com",
     "password": "SecurePass123!",
     "name": "Alice Builder"
   }

2. AINative → Response
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "user": {
       "id": "user-uuid-123",
       "email": "builder@example.com",
       "name": "Alice Builder",
       "email_verified": false
     }
   }

3. Frontend stores tokens
   localStorage.setItem("access_token", token)

4. User verifies email (click link in email)
   POST /v1/auth/verify-email
   { "token": "verification-token" }
```

### Flow 2: User Joins Hackathon

```
1. Frontend → DotHack Backend
   POST /api/v1/hackathons/{id}/join
   Authorization: Bearer {access_token}

2. DotHack verifies token
   GET /v1/auth/me (AINative)
   → Returns user info

3. DotHack creates participant entry
   INSERT INTO hackathon_participants (ZeroDB)
   {
     "hackathon_id": "hack-123",
     "participant_id": "user-uuid-123",  // From AINative
     "role": "BUILDER"
   }

4. Response to frontend
   { "message": "Successfully joined hackathon" }
```

### Flow 3: OAuth Login (GitHub)

```
1. Frontend → GitHub OAuth
   https://github.com/login/oauth/authorize?client_id=...

2. GitHub → Callback to frontend
   ?code=authorization_code_from_github

3. Frontend → AINative Auth API
   POST /v1/auth/github/callback
   {
     "code": "authorization_code_from_github",
     "redirect_uri": "https://dothack.ainative.studio/auth/callback"
   }

4. AINative exchanges code for GitHub access token
   → Fetches GitHub user info
   → Creates or updates user in AINative database
   → Returns JWT token

5. Frontend stores token and uses it for subsequent requests
```

---

## API Reference

### AINative Auth Endpoints

**Base URL:** `https://api.ainative.studio`

#### 1. Register User
```http
POST /v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "name": "John Doe"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "John Doe",
    "email_verified": false,
    "created_at": "2025-12-28T10:00:00Z"
  }
}
```

**Errors:**
- `400`: Validation error (weak password, invalid email)
- `409`: Email already registered

---

#### 2. Login
```http
POST /v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (200 OK):** Same as registration

**Errors:**
- `401`: Invalid credentials
- `403`: Email not verified

---

#### 3. Get Current User (Token Verification)
```http
GET /v1/auth/me
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "email_verified": true,
  "created_at": "2025-12-28T10:00:00Z"
}
```

**Errors:**
- `401`: Invalid or expired token

---

#### 4. Refresh Token
```http
POST /v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "access_token": "new_access_token...",
  "token_type": "bearer"
}
```

**Errors:**
- `401`: Invalid or expired refresh token

---

#### 5. Logout
```http
POST /v1/auth/logout
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "message": "Successfully logged out"
}
```

---

#### 6. GitHub OAuth Callback
```http
POST /v1/auth/github/callback
Content-Type: application/json

{
  "code": "authorization_code_from_github",
  "redirect_uri": "https://dothack.ainative.studio/auth/callback"
}
```

**Response (200 OK):** Same as login response

**Errors:**
- `400`: Invalid authorization code
- `500`: GitHub API error

---

#### 7. LinkedIn OAuth Callback
```http
POST /v1/auth/linkedin/callback
Content-Type: application/json

{
  "code": "authorization_code_from_linkedin",
  "redirect_uri": "https://dothack.ainative.studio/auth/callback"
}
```

**Response (200 OK):** Same as login response

**Errors:**
- `400`: Invalid authorization code
- `500`: LinkedIn API error

---

### DotHack Endpoints (with AINative Auth)

All DotHack endpoints accept **two authentication methods**:

1. **JWT Token:** `Authorization: Bearer {token}`
2. **API Key:** `X-API-Key: {api_key}` or `Authorization: Bearer {api_key}`

#### Health Check
```http
GET /health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-28T10:00:00.000000"
}
```

#### Protected Endpoints (Coming Soon)

| Endpoint | Method | Auth | Role Required | Description |
|----------|--------|------|---------------|-------------|
| `POST /api/v1/hackathons` | POST | Bearer | None | Create hackathon (auto ORGANIZER) |
| `POST /api/v1/hackathons/{id}/join` | POST | Bearer | None | Join hackathon (creates BUILDER) |
| `PATCH /api/v1/hackathons/{id}` | PATCH | Bearer | ORGANIZER | Update hackathon |
| `POST /api/v1/hackathons/{id}/tracks` | POST | Bearer | ORGANIZER | Create tracks |
| `POST /api/v1/projects/{id}/submit` | POST | Bearer | BUILDER | Submit project |
| `POST /api/v1/submissions/{id}/score` | POST | Bearer | JUDGE | Score submission |

---

## Environment Variables

### Required Variables

```bash
# Application Settings
ENVIRONMENT=development|staging|production
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
API_VERSION=v1

# Server Configuration
HOST=0.0.0.0
PORT=8000

# CORS Settings
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# AINative Authentication
AINATIVE_API_URL=https://api.ainative.studio
AINATIVE_API_KEY=your_api_key_here  # For server-to-server calls (optional)

# ZeroDB Configuration
ZERODB_API_KEY=your_zerodb_api_key
ZERODB_PROJECT_ID=your_project_uuid
ZERODB_BASE_URL=https://api.ainative.studio
ZERODB_TIMEOUT=30.0
```

### Optional Variables (External Services)

```bash
# HubSpot Integration
HUBSPOT_API_URL=https://api.hubapi.com
HUBSPOT_API_KEY=your_hubspot_key

# Clearbit Integration
CLEARBIT_API_URL=https://person.clearbit.com
CLEARBIT_API_KEY=your_clearbit_key

# Apollo Integration
APOLLO_API_URL=https://api.apollo.io
APOLLO_API_KEY=your_apollo_key

# Resend Email
RESEND_API_URL=https://api.resend.com
RESEND_API_KEY=your_resend_key
```

### Environment Variable Validation

The application validates all environment variables at startup using Pydantic:

```python
from config import settings

# Access validated settings
print(settings.AINATIVE_API_URL)  # https://api.ainative.studio
print(settings.LOG_LEVEL)  # INFO (validated against allowed levels)
print(settings.ALLOWED_ORIGINS)  # ['http://localhost:3000', ...]
```

**Validation Rules:**
- `LOG_LEVEL` must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `ALLOWED_ORIGINS` is comma-separated, automatically parsed into a list
- Missing required variables will cause startup failure
- Extra variables in `.env` are ignored (won't cause errors)

---

## Security Checklist

### ✅ Authentication
- [ ] All tokens verified via AINative `/v1/auth/me`
- [ ] User info cached with 5-minute TTL for performance
- [ ] API keys used for server-to-server calls
- [ ] Never trust client-provided user IDs without verification

### ✅ Authorization
- [ ] Role checked in hackathon_participants for every protected action
- [ ] hackathon_id and participant_id validated
- [ ] Authorization failures logged for security monitoring

### ✅ Data Protection
- [ ] Project-scoped data isolation (ZeroDB automatic)
- [ ] No cross-hackathon data leakage
- [ ] Rate limiting configured (10,000 req/hr on Pro tier)

---

## Testing

### Development Mode

```bash
# Use test token for local testing
Authorization: Bearer ALWAYS-WORKS-TOKEN-12345
```

This bypasses authentication and returns the `admin@ainative.studio` user.

### Production Mode

```bash
# 1. Register user
curl -X POST https://api.ainative.studio/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "name": "Test User"
  }'

# 2. Use returned token
curl -X POST https://dothack-api.ainative.studio/api/v1/hackathons \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Hackathon"}'
```

---

## Troubleshooting Guide

### Common Issues

#### 1. "Invalid or expired token" Error

**Symptoms:**
- HTTP 401 response when calling protected endpoints
- Error message: "Invalid or expired token"

**Possible Causes:**
1. **Expired Token:** JWT tokens expire after a set duration
2. **Invalid Token:** Token was manually modified or corrupted
3. **Logged Out:** User logged out, token is blacklisted
4. **Network Issues:** AINative API unreachable

**Solutions:**
```python
# Frontend: Implement automatic token refresh
async def api_call_with_retry(url, token):
    response = await http.get(url, headers={"Authorization": f"Bearer {token}"})

    if response.status == 401:
        # Try refreshing token
        new_token = await refresh_access_token(refresh_token)

        # Retry with new token
        response = await http.get(url, headers={"Authorization": f"Bearer {new_token}"})

    return response

# Backend: Implement token caching (5-minute TTL)
from cachetools import TTLCache

user_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes

async def get_current_user(token: str):
    if token in user_cache:
        return user_cache[token]

    user = await auth_client.verify_token(token)
    if user:
        user_cache[token] = user

    return user
```

---

#### 2. "Connection refused" to AINative API

**Symptoms:**
- Network errors when calling `/v1/auth/me`
- Timeout exceptions

**Possible Causes:**
1. **Wrong URL:** `AINATIVE_API_URL` points to incorrect environment
2. **Firewall:** Network blocks outbound HTTPS
3. **API Downtime:** AINative service temporarily unavailable

**Solutions:**
```bash
# 1. Check environment configuration
echo $AINATIVE_API_URL  # Should be https://api.ainative.studio

# 2. Test connectivity
curl https://api.ainative.studio/health

# 3. Check DNS resolution
nslookup api.ainative.studio

# 4. Implement retry with exponential backoff
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def verify_token_with_retry(token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.ainative.studio/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0
        )
        return response.json()
```

---

#### 3. CORS Errors in Frontend

**Symptoms:**
- Browser console: "CORS policy: No 'Access-Control-Allow-Origin' header"
- Requests blocked by browser

**Solutions:**
```python
# 1. Update ALLOWED_ORIGINS in .env
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,https://dothack.ainative.studio

# 2. Verify CORS middleware configuration in main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # Must match frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. For development, use wildcard (NOT for production)
ALLOWED_ORIGINS=*
```

---

#### 4. "X-API-Key header required" Error

**Symptoms:**
- HTTP 401 when using API key authentication
- Error message: "X-API-Key header required"

**Possible Causes:**
1. **Missing Header:** X-API-Key not included in request
2. **Wrong Header Name:** Using `Authorization` instead of `X-API-Key`
3. **Case Sensitivity:** Header name capitalization incorrect

**Solutions:**
```bash
# Correct usage (choose ONE method):

# Method 1: X-API-Key header
curl -H "X-API-Key: your_api_key" https://api.dothack.ainative.studio/api/v1/hackathons

# Method 2: Bearer token (API key as bearer)
curl -H "Authorization: Bearer your_api_key" https://api.dothack.ainative.studio/api/v1/hackathons

# Method 3: JWT token
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." https://api.dothack.ainative.studio/api/v1/hackathons
```

---

#### 5. Role Check Fails ("Only ORGANIZER can perform this action")

**Symptoms:**
- HTTP 403 Forbidden
- User authenticated but action denied

**Possible Causes:**
1. **User Not Assigned Role:** No entry in `hackathon_participants` table
2. **Wrong Role:** User has BUILDER role but needs ORGANIZER
3. **Wrong Hackathon:** Checking role for different hackathon

**Solutions:**
```python
# 1. Debug role checking
async def check_organizer_role(hackathon_id: str, user_id: str):
    # Query hackathon_participants
    participant = await zerodb.tables.query_rows(
        "hackathon_participants",
        filter={
            "hackathon_id": hackathon_id,
            "participant_id": user_id
        }
    )

    # Log for debugging
    print(f"User {user_id} role in hackathon {hackathon_id}: {participant}")

    if not participant:
        raise HTTPException(403, "User not a participant")

    if participant["role"] != "ORGANIZER":
        raise HTTPException(403, f"Only ORGANIZER can perform this action (user has {participant['role']})")

# 2. Grant organizer role when creating hackathon
await zerodb.tables.insert_rows(
    "hackathon_participants",
    rows=[{
        "hackathon_id": hackathon_id,
        "participant_id": user_id,
        "role": "ORGANIZER",  # Grant ORGANIZER role
        "metadata": {
            "ainative_user_email": user["email"],
            "ainative_user_name": user["name"]
        }
    }]
)
```

---

### Debugging Tools

#### 1. Test Token Verification
```bash
# Get user info from token
TOKEN="your_jwt_token_here"

curl -X GET https://api.ainative.studio/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" \
  -v  # Verbose output shows full response
```

#### 2. Check Logs
```bash
# Backend logs show authentication attempts
docker logs dothack-backend --tail 100 -f

# Look for:
# - "HTTP exception: 401" (auth failures)
# - "Validation error" (malformed requests)
# - "Unhandled exception" (bugs)
```

#### 3. Verify Environment Variables
```bash
# Print all environment variables
python3 -c "from config import settings; print(vars(settings))"

# Check specific variable
python3 -c "from config import settings; print(settings.AINATIVE_API_URL)"
```

---

## FAQ

**Q: Can we add custom authentication methods?**
A: No. All authentication MUST go through AINative Auth API.

**Q: Where do we store hackathon-specific roles?**
A: In ZeroDB `hackathon_participants` table, referencing AINative user IDs.

**Q: What about password reset?**
A: Handled by AINative `/v1/auth/forgot-password` and `/v1/auth/reset-password`.

**Q: Can users login with social accounts?**
A: Yes. GitHub and LinkedIn OAuth are already implemented in AINative.

**Q: What if AINative Auth API is down?**
A: Implement retry logic with exponential backoff. Cache user info to reduce API calls (5-minute TTL recommended).

**Q: Do we need to sync user data?**
A: No. DotHack only stores `participant_id` (AINative user.id) in hackathon_participants. User profile data lives in AINative.

**Q: How do I test authentication locally?**
A: Use the test token `ALWAYS-WORKS-TOKEN-12345` which returns `admin@ainative.studio` user (development mode only).

**Q: Can I use both JWT and API key authentication?**
A: Yes. The `get_current_user` dependency checks X-API-Key header first, then falls back to JWT Bearer token.

**Q: How long do tokens last?**
A: Access tokens expire after 15 minutes. Refresh tokens expire after 7 days. Use `/v1/auth/refresh` to get new access tokens.

**Q: Is email verification required?**
A: No for development. Yes for production (login will return 403 if email not verified).

---

## Documentation

- **Integration Guide:** `/docs/AINATIVE_AUTH_INTEGRATION.md`
- **PRD Auth Update:** `/docs/PRD_AUTH_UPDATE.md`
- **AINative Auth Docs:** https://api.ainative.studio/docs#/Authentication
- **Support:** hello@ainative.studio

---

**CRITICAL: This architecture is MANDATORY. Do not build standalone authentication.**
