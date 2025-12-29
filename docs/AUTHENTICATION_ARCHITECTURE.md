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

```
┌──────────────────────────────────────────────────────────────┐
│                    DotHack Frontend                          │
│              (Web App / Mobile App)                          │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ 1. User clicks "Login with GitHub"
                            │
                    ┌───────▼────────┐
                    │   AINative     │
                    │   Auth API     │ ← All authentication here
                    │ /v1/auth/*     │
                    └───────┬────────┘
                            │
                            │ 2. Returns JWT token
                            │
┌───────────────────────────▼──────────────────────────────────┐
│                    DotHack Backend                           │
│                   (Python FastAPI)                           │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Authentication Middleware                          │    │
│  │  1. Extract token from Authorization header        │    │
│  │  2. Verify token via AINative /v1/auth/me         │    │
│  │  3. Get user info (id, email, name)               │    │
│  │  4. Look up user role in hackathon_participants   │    │
│  │  5. Grant/deny access based on role               │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ 3. Query user role
                            │
                    ┌───────▼────────┐
                    │    ZeroDB      │
                    │  (Data Layer)  │ ← Store roles here
                    └────────────────┘
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

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/v1/auth/register` | POST | None | Register new user |
| `/v1/auth/login` | POST | None | Login with email/password |
| `/v1/auth/logout` | POST | Bearer | Logout (blacklist token) |
| `/v1/auth/refresh` | POST | None | Refresh access token |
| `/v1/auth/me` | GET | Bearer | Get current user (verify token) |
| `/v1/auth/github/callback` | POST | None | GitHub OAuth callback |
| `/v1/auth/linkedin/callback` | POST | None | LinkedIn OAuth callback |

### DotHack Endpoints (with AINative Auth)

| Endpoint | Method | Auth | Role Required |
|----------|--------|------|---------------|
| `POST /api/v1/hackathons` | POST | Bearer | None (creates ORGANIZER) |
| `POST /api/v1/hackathons/{id}/join` | POST | Bearer | None (creates BUILDER) |
| `PATCH /api/v1/hackathons/{id}` | PATCH | Bearer | ORGANIZER |
| `POST /api/v1/hackathons/{id}/tracks` | POST | Bearer | ORGANIZER |
| `POST /api/v1/projects/{id}/submit` | POST | Bearer | BUILDER (team member) |
| `POST /api/v1/submissions/{id}/score` | POST | Bearer | JUDGE |

---

## Environment Variables

```bash
# AINative Authentication
AINATIVE_API_URL=https://api.ainative.studio
AINATIVE_API_KEY=your_api_key_here  # For server-to-server calls (optional)

# ZeroDB
ZERODB_API_KEY=your_zerodb_api_key
ZERODB_PROJECT_ID=your_project_uuid
ZERODB_BASE_URL=https://api.ainative.studio
```

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
A: Implement retry logic with exponential backoff. Cache user info to reduce API calls.

**Q: Do we need to sync user data?**
A: No. DotHack only stores `participant_id` (AINative user.id) in hackathon_participants. User profile data lives in AINative.

---

## Documentation

- **Integration Guide:** `/docs/AINATIVE_AUTH_INTEGRATION.md`
- **PRD Auth Update:** `/docs/PRD_AUTH_UPDATE.md`
- **AINative Auth Docs:** https://api.ainative.studio/docs#/Authentication
- **Support:** hello@ainative.studio

---

**CRITICAL: This architecture is MANDATORY. Do not build standalone authentication.**
