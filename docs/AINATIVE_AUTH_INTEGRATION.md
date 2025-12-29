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

**See `/docs/OAUTH_FLOWS.md` for comprehensive OAuth implementation guide with:**
- Detailed flow diagrams for GitHub and LinkedIn
- Step-by-step frontend integration code
- Complete React components for OAuth buttons and callbacks
- Security best practices and CSRF protection
- Error handling and troubleshooting guide

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

## Code Examples for Common Patterns

### Pattern 1: Protected Endpoint with Role Check

```python
# python-api/api/routes/hackathons.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from api.dependencies import get_current_user
from services.hackathon_service import HackathonService

router = APIRouter(prefix="/api/v1/hackathons", tags=["Hackathons"])

@router.post("/{hackathon_id}/tracks")
async def create_track(
    hackathon_id: str,
    track_data: TrackCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create hackathon track (requires ORGANIZER role)

    Args:
        hackathon_id: UUID of the hackathon
        track_data: Track creation data
        current_user: Authenticated user from AINative

    Returns:
        Created track object

    Raises:
        HTTPException: 403 if user is not an ORGANIZER
    """
    user_id = current_user["id"]

    # Check organizer role
    await HackathonService.check_organizer_role(hackathon_id, user_id)

    # Create track
    track = await HackathonService.create_track(hackathon_id, track_data)

    return track
```

---

### Pattern 2: Optional Authentication

```python
# python-api/api/routes/hackathons.py
from api.dependencies import get_current_user_optional

@router.get("/{hackathon_id}")
async def get_hackathon(
    hackathon_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Get hackathon (public endpoint with optional auth)

    If authenticated, returns user-specific data (e.g., user's role).
    If not authenticated, returns public data only.
    """
    hackathon = await HackathonService.get_hackathon(hackathon_id)

    if current_user:
        # Add user-specific data
        user_role = await HackathonService.get_user_role(
            hackathon_id,
            current_user["id"]
        )
        hackathon["user_role"] = user_role

    return hackathon
```

---

### Pattern 3: Error Handling with Retry Logic

```python
# python-api/integrations/ainative/auth_client.py
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AINativeAuthClient:
    def __init__(self, base_url: str = "https://api.ainative.studio"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(10.0, connect=5.0)
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token with retry logic

        Retries up to 3 times with exponential backoff:
        - 1st retry: wait 2 seconds
        - 2nd retry: wait 4 seconds
        - 3rd retry: wait 8 seconds
        """
        try:
            response = await self.client.get(
                "/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                user = response.json()
                logger.info(f"Token verified for user: {user['email']}")
                return user

            elif response.status_code == 401:
                logger.warning("Token verification failed: Invalid or expired token")
                return None

            else:
                # Unexpected status code - log and return None
                logger.error(f"Unexpected status code from auth API: {response.status_code}")
                return None

        except httpx.TimeoutException as e:
            logger.error(f"Token verification timeout: {str(e)}")
            raise  # Retry will catch this

        except httpx.ConnectError as e:
            logger.error(f"Connection error to auth API: {str(e)}")
            raise  # Retry will catch this

        except Exception as e:
            logger.exception(f"Unexpected error during token verification: {str(e)}")
            return None
```

---

### Pattern 4: Token Caching for Performance

```python
# python-api/api/dependencies.py
from cachetools import TTLCache
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Cache user data for 5 minutes (300 seconds)
user_cache = TTLCache(maxsize=1000, ttl=300)

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get current user with caching

    Caches user data for 5 minutes to reduce calls to AINative API.
    Cache key is the JWT token itself.
    """
    token = credentials.credentials

    # Check cache first
    if token in user_cache:
        logger.debug("User data retrieved from cache")
        return user_cache[token]

    # Verify token with AINative
    user = await auth_client.verify_token(token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Cache user data
    user_cache[token] = user
    logger.debug(f"User data cached for: {user['email']}")

    return user
```

---

### Pattern 5: Custom Role Dependency

```python
# python-api/api/dependencies.py
from functools import wraps
from typing import List

def require_role(allowed_roles: List[str]):
    """
    Decorator to require specific role for endpoint

    Usage:
        @router.post("/hackathons/{id}/publish")
        @require_role(["ORGANIZER"])
        async def publish_hackathon(hackathon_id: str, ...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            hackathon_id = kwargs.get("hackathon_id")
            current_user = kwargs.get("current_user")

            if not hackathon_id or not current_user:
                raise HTTPException(500, "Missing hackathon_id or current_user")

            # Check role
            participant = await zerodb.tables.query_rows(
                "hackathon_participants",
                filter={
                    "hackathon_id": hackathon_id,
                    "participant_id": current_user["id"]
                }
            )

            if not participant or participant[0]["role"] not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Only {', '.join(allowed_roles)} can perform this action"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@router.post("/{hackathon_id}/publish")
@require_role(["ORGANIZER"])
async def publish_hackathon(
    hackathon_id: str,
    current_user: Dict = Depends(get_current_user)
):
    # Only ORGANIZER can reach here
    pass
```

---

### Pattern 6: Frontend Integration (React/TypeScript)

```typescript
// frontend/src/services/authService.ts
import axios from 'axios';

const AINATIVE_API_URL = 'https://api.ainative.studio';
const DOTHACK_API_URL = 'https://api.dothack.ainative.studio';

export interface User {
  id: string;
  email: string;
  name: string;
  email_verified: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  user: User;
}

class AuthService {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    // Load tokens from localStorage on init
    this.accessToken = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
  }

  /**
   * Login with email and password
   */
  async login(email: string, password: string): Promise<User> {
    const response = await axios.post<AuthTokens>(
      `${AINATIVE_API_URL}/v1/auth/login`,
      { email, password }
    );

    this.setTokens(response.data.access_token, response.data.refresh_token);
    return response.data.user;
  }

  /**
   * GitHub OAuth login
   */
  async loginWithGitHub(code: string, redirectUri: string): Promise<User> {
    const response = await axios.post<AuthTokens>(
      `${AINATIVE_API_URL}/v1/auth/github/callback`,
      { code, redirect_uri: redirectUri }
    );

    this.setTokens(response.data.access_token, response.data.refresh_token);
    return response.data.user;
  }

  /**
   * Refresh access token
   */
  async refreshAccessToken(): Promise<string> {
    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await axios.post<{ access_token: string }>(
      `${AINATIVE_API_URL}/v1/auth/refresh`,
      { refresh_token: this.refreshToken }
    );

    this.accessToken = response.data.access_token;
    localStorage.setItem('access_token', this.accessToken);

    return this.accessToken;
  }

  /**
   * Make authenticated API call to DotHack backend
   */
  async apiCall<T>(endpoint: string, options?: RequestInit): Promise<T> {
    try {
      const response = await fetch(`${DOTHACK_API_URL}${endpoint}`, {
        ...options,
        headers: {
          'Authorization': `Bearer ${this.accessToken}`,
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      });

      if (response.status === 401) {
        // Token expired - try refreshing
        await this.refreshAccessToken();

        // Retry request with new token
        const retryResponse = await fetch(`${DOTHACK_API_URL}${endpoint}`, {
          ...options,
          headers: {
            'Authorization': `Bearer ${this.accessToken}`,
            'Content-Type': 'application/json',
            ...options?.headers,
          },
        });

        return retryResponse.json();
      }

      return response.json();
    } catch (error) {
      console.error('API call failed:', error);
      throw error;
    }
  }

  /**
   * Logout user
   */
  async logout(): Promise<void> {
    if (this.accessToken) {
      try {
        await axios.post(
          `${AINATIVE_API_URL}/v1/auth/logout`,
          {},
          { headers: { Authorization: `Bearer ${this.accessToken}` } }
        );
      } catch (error) {
        console.error('Logout API call failed:', error);
      }
    }

    this.clearTokens();
  }

  /**
   * Get current user
   */
  async getCurrentUser(): Promise<User | null> {
    if (!this.accessToken) {
      return null;
    }

    try {
      const response = await axios.get<User>(
        `${AINATIVE_API_URL}/v1/auth/me`,
        { headers: { Authorization: `Bearer ${this.accessToken}` } }
      );
      return response.data;
    } catch (error) {
      return null;
    }
  }

  private setTokens(accessToken: string, refreshToken: string): void {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }

  private clearTokens(): void {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  isAuthenticated(): boolean {
    return !!this.accessToken;
  }
}

export const authService = new AuthService();
```

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

# CORS Settings (comma-separated)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,https://dothack.ainative.studio

# AINative Authentication
AINATIVE_API_URL=https://api.ainative.studio
AINATIVE_API_KEY=your_api_key_here  # Optional: For server-to-server calls

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

### Loading Environment Variables

Create `.env` file in `python-api/` directory:

```bash
# python-api/.env
ENVIRONMENT=development
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

AINATIVE_API_URL=https://api.ainative.studio

ZERODB_API_KEY=your_actual_api_key
ZERODB_PROJECT_ID=your_actual_project_id
ZERODB_BASE_URL=https://api.ainative.studio
```

**IMPORTANT:** Add `.env` to `.gitignore` to prevent committing secrets:

```bash
# .gitignore
.env
.env.local
.env.*.local
```

### Accessing Environment Variables in Code

```python
# python-api/config.py uses Pydantic Settings for validation
from config import settings

# Access validated settings
api_url = settings.AINATIVE_API_URL  # Type: str
log_level = settings.LOG_LEVEL  # Type: str (validated)
origins = settings.ALLOWED_ORIGINS  # Type: List[str] (auto-parsed)

# Use in code
import logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
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
