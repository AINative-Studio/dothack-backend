# AINative Authentication Integration Guide

**Project:** DotHack Backend
**Version:** 1.0
**Last Updated:** 2025-12-28

---

## Overview

DotHack Backend **MUST USE** the existing AINative Studio authentication system instead of building standalone authentication. This ensures:
- ✅ Centralized user management across all AINative products
- ✅ Single sign-on (SSO) capability
- ✅ OAuth integration (GitHub, LinkedIn) out-of-the-box
- ✅ Production-grade security (bcrypt, JWT, token blacklisting)
- ✅ API key management for programmatic access
- ✅ Zero maintenance cost for auth infrastructure

---

## AINative Authentication System

### Base URL
```
Production: https://api.ainative.studio
Development: http://localhost:8000
```

### Authentication Methods

| Method | Header | Format | Use Case |
|--------|--------|--------|----------|
| **JWT Token** | `Authorization` | `Bearer {token}` | Web/mobile apps |
| **API Key** | `X-API-Key` | `{api_key}` | Server-to-server |
| **API Key (Bearer)** | `Authorization` | `Bearer {api_key}` | Alternative format |

---

## Available Endpoints

### 1. User Registration
```http
POST /v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "name": "John Doe"
}
```

**Response:**
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

### 2. User Login
```http
POST /v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:** Same as registration

### 3. Get Current User
```http
GET /v1/auth/me
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "email_verified": true,
  "created_at": "2025-12-28T10:00:00Z"
}
```

### 4. Refresh Token
```http
POST /v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 5. Logout
```http
POST /v1/auth/logout
Authorization: Bearer {access_token}
```

### 6. OAuth Login (GitHub)
```http
POST /v1/auth/github/callback
Content-Type: application/json

{
  "code": "authorization_code_from_github",
  "redirect_uri": "https://dothack.ainative.studio/auth/callback"
}
```

### 7. OAuth Login (LinkedIn)
```http
POST /v1/auth/linkedin/callback
Content-Type: application/json

{
  "code": "authorization_code_from_linkedin",
  "redirect_uri": "https://dothack.ainative.studio/auth/callback"
}
```

---

## Integration Pattern for DotHack

### Step 1: Install AINative SDK (Python)

```bash
pip install ainative-sdk
```

Or use the HTTP client wrapper:

```python
# python-api/integrations/ainative/auth_client.py
import httpx
from typing import Optional, Dict, Any

class AINativeAuthClient:
    """
    Client for AINative Studio authentication
    """

    def __init__(self, base_url: str = "https://api.ainative.studio"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token and get user info

        Args:
            token: JWT access token

        Returns:
            User object if valid, None if invalid
        """
        try:
            response = await self.client.get(
                "/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                return response.json()
            return None

        except Exception:
            return None

    async def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Verify API key and get user info

        Args:
            api_key: AINative API key

        Returns:
            User object if valid, None if invalid
        """
        try:
            response = await self.client.get(
                "/v1/auth/me",
                headers={"X-API-Key": api_key}
            )

            if response.status_code == 200:
                return response.json()
            return None

        except Exception:
            return None
```

### Step 2: Create Authentication Dependency

```python
# python-api/api/dependencies.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any

from integrations.ainative.auth_client import AINativeAuthClient

security = HTTPBearer()
auth_client = AINativeAuthClient()

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get current authenticated user from AINative

    Supports:
    - JWT token (Authorization: Bearer {token})
    - API key (X-API-Key: {key} or Authorization: Bearer {key})
    """
    # Check for API key in X-API-Key header
    api_key = request.headers.get("x-api-key")

    if api_key:
        user = await auth_client.verify_api_key(api_key)
        if user:
            return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Verify JWT token
    token = credentials.credentials
    user = await auth_client.verify_token(token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user

async def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    """
    Optional authentication - returns None if not authenticated
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
```

### Step 3: Use in Endpoints

```python
# python-api/api/routes/hackathons.py
from fastapi import APIRouter, Depends
from api.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/hackathons", tags=["Hackathons"])

@router.post("/")
async def create_hackathon(
    hackathon_data: HackathonCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create hackathon (requires authentication)

    User is automatically authenticated via AINative
    """
    user_id = current_user["id"]
    user_email = current_user["email"]

    # Create hackathon with authenticated user
    # ...

@router.get("/{hackathon_id}")
async def get_hackathon(
    hackathon_id: str,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Get hackathon (public endpoint, optional auth)
    """
    # If current_user is None, user is not authenticated
    # If current_user is dict, user is authenticated
    # ...
```

---

## Role-Based Access Control

### Participant Roles in DotHack

| Role | Description | Permissions |
|------|-------------|-------------|
| **ORGANIZER** | Hackathon creator | Create hackathon, manage tracks, assign judges |
| **BUILDER** | Participant | Join teams, submit projects |
| **JUDGE** | Evaluator | Score submissions, provide feedback |
| **MENTOR** | Advisor | View projects, provide guidance |

### Storing Roles in ZeroDB

**hackathon_participants table:**
```json
{
  "id": "uuid",
  "hackathon_id": "uuid",
  "participant_id": "uuid",  // This is the AINative user_id
  "role": "ORGANIZER | BUILDER | JUDGE | MENTOR",
  "metadata": {
    "ainative_user_email": "user@example.com",
    "ainative_user_name": "John Doe"
  },
  "joined_at": "2025-12-28T10:00:00Z"
}
```

### Role Checking Pattern

```python
# python-api/services/hackathon_service.py
from fastapi import HTTPException, status

async def check_organizer_role(hackathon_id: str, user_id: str, zerodb_client):
    """
    Verify user is an organizer for the hackathon
    """
    # Query hackathon_participants table
    participant = await zerodb_client.tables.query_rows(
        "hackathon_participants",
        filter={
            "hackathon_id": hackathon_id,
            "participant_id": user_id,
            "role": "ORGANIZER"
        }
    )

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organizers can perform this action"
        )

    return True

# In endpoint
@router.patch("/{hackathon_id}")
async def update_hackathon(
    hackathon_id: str,
    update_data: HackathonUpdate,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]

    # Check organizer role
    await check_organizer_role(hackathon_id, user_id, zerodb_client)

    # Update hackathon
    # ...
```

---

## User Flow Examples

### Flow 1: Builder Submits Project

```
1. Builder logs in via AINative (GitHub OAuth)
   POST /v1/auth/github/callback → Returns JWT token

2. Builder joins hackathon
   POST /api/v1/hackathons/{id}/join
   Authorization: Bearer {jwt_token}
   → Creates entry in hackathon_participants with role=BUILDER

3. Builder creates team
   POST /api/v1/hackathons/{id}/teams
   Authorization: Bearer {jwt_token}
   → Creates team, adds builder as team lead

4. Builder submits project
   POST /api/v1/projects/{id}/submit
   Authorization: Bearer {jwt_token}
   → Verifies builder is team member
   → Creates submission
   → Generates embeddings
```

### Flow 2: Judge Scores Submission

```
1. Judge logs in via AINative (email/password)
   POST /v1/auth/login → Returns JWT token

2. Judge is assigned to hackathon (by organizer)
   → Entry in hackathon_participants with role=JUDGE

3. Judge views submissions
   GET /api/v1/hackathons/{id}/submissions
   Authorization: Bearer {jwt_token}
   → Verifies judge role
   → Returns submissions for assigned track

4. Judge scores submission
   POST /api/v1/submissions/{id}/score
   Authorization: Bearer {jwt_token}
   → Verifies judge role
   → Creates score entry
   → Updates leaderboard
```

### Flow 3: Organizer Creates Hackathon

```
1. Organizer logs in via AINative (LinkedIn OAuth)
   POST /v1/auth/linkedin/callback → Returns JWT token

2. Organizer creates hackathon
   POST /api/v1/hackathons
   Authorization: Bearer {jwt_token}
   → Creates hackathon
   → Adds organizer to hackathon_participants with role=ORGANIZER

3. Organizer creates tracks
   POST /api/v1/hackathons/{id}/tracks
   Authorization: Bearer {jwt_token}
   → Verifies organizer role
   → Creates tracks

4. Organizer invites judges
   POST /api/v1/hackathons/{id}/invite-judges
   Authorization: Bearer {jwt_token}
   → Verifies organizer role
   → Sends invites via AINative email service
```

---

## Environment Variables

```bash
# AINative Authentication
AINATIVE_API_URL=https://api.ainative.studio
AINATIVE_API_KEY=your_api_key_here  # For server-to-server calls

# DotHack specific
ZERODB_API_KEY=your_zerodb_api_key
ZERODB_PROJECT_ID=your_project_uuid
```

---

## Security Considerations

### ✅ DO:
- Always verify tokens via AINative `/v1/auth/me` endpoint
- Cache user info for performance (with TTL)
- Use API keys for server-to-server communication
- Store AINative user_id in hackathon_participants table

### ❌ DON'T:
- Build custom authentication system
- Store passwords in DotHack database
- Bypass AINative authentication
- Trust client-provided user IDs without verification

---

## Testing

### Development Mode

Use the test token for local development:
```bash
Authorization: Bearer ALWAYS-WORKS-TOKEN-12345
```

This returns the admin@ainative.studio user for testing.

### Production Mode

Use real AINative credentials:
1. Register user via `/v1/auth/register`
2. Verify email via `/v1/auth/verify-email`
3. Login via `/v1/auth/login`
4. Use returned JWT token

---

## Migration from Standalone Auth

If you already implemented standalone authentication:

1. **Remove standalone auth code:**
   - Delete custom auth endpoints
   - Delete user management code
   - Delete password hashing logic

2. **Update endpoints:**
   - Replace custom auth dependency with `get_current_user`
   - Update user ID references to AINative user IDs

3. **Migrate user data:**
   - No migration needed - AINative handles all user data
   - Update hackathon_participants to use AINative user IDs

---

## Support

- **AINative Docs:** https://api.ainative.studio/docs
- **Auth Endpoints:** https://api.ainative.studio/docs#/Authentication
- **Support:** hello@ainative.studio
