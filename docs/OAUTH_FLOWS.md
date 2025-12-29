# OAuth Authentication Flows

**Project:** DotHack Backend
**Version:** 1.0
**Last Updated:** 2025-12-28

---

## Overview

This document provides comprehensive documentation for OAuth authentication flows integrated with AINative Studio. DotHack supports two OAuth providers:

- **GitHub OAuth** - Standard OAuth 2.0 flow
- **LinkedIn OAuth** - OpenID Connect (OIDC) flow

Both flows are handled by AINative's authentication system at `https://api.ainative.studio/v1/auth/*`.

---

## GitHub OAuth Flow

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    DotHack Frontend                          │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ 1. User clicks "Login with GitHub"
                            │    Redirect to GitHub OAuth
                            │
                    ┌───────▼────────┐
                    │     GitHub     │
                    │  OAuth Server  │
                    └───────┬────────┘
                            │
                            │ 2. User authorizes app
                            │    GitHub redirects with code
                            │
┌───────────────────────────▼──────────────────────────────────┐
│                    DotHack Frontend                          │
│                                                              │
│  Receives: ?code=abc123&state=xyz                           │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ 3. POST /v1/auth/github/callback
                            │    { code, redirect_uri }
                            │
                    ┌───────▼────────┐
                    │   AINative     │
                    │   Auth API     │
                    │                │
                    │ ┌────────────┐ │
                    │ │ Exchange   │ │ 4. POST to GitHub
                    │ │ code for   │ │    token endpoint
                    │ │ token      │ │
                    │ └─────┬──────┘ │
                    │       │        │
                    │ ┌─────▼──────┐ │ 5. GET GitHub user info
                    │ │ Fetch user │ │    /user and /user/emails
                    │ │ profile    │ │
                    │ └─────┬──────┘ │
                    │       │        │
                    │ ┌─────▼──────┐ │ 6. Create/update user
                    │ │ Upsert     │ │    in PostgreSQL
                    │ │ user in DB │ │    Link GitHub ID
                    │ └─────┬──────┘ │
                    │       │        │
                    │ ┌─────▼──────┐ │ 7. Generate JWT tokens
                    │ │ Create JWT │ │    (access + refresh)
                    │ │ tokens     │ │
                    │ └────────────┘ │
                    └───────┬────────┘
                            │
                            │ 8. Return { access_token, user }
                            │
┌───────────────────────────▼──────────────────────────────────┐
│                    DotHack Frontend                          │
│                                                              │
│  localStorage.setItem('access_token', token)                │
│  → User authenticated, redirect to dashboard                │
└──────────────────────────────────────────────────────────────┘
```

### Step-by-Step Implementation

#### Step 1: Initiate GitHub OAuth

**Frontend redirects user to GitHub:**

```javascript
const GITHUB_CLIENT_ID = process.env.VITE_GITHUB_CLIENT_ID;
const REDIRECT_URI = 'https://dothack.ainative.studio/auth/callback';
const STATE = generateRandomState(); // Generate CSRF token

const githubAuthUrl = `https://github.com/login/oauth/authorize?${new URLSearchParams({
  client_id: GITHUB_CLIENT_ID,
  redirect_uri: REDIRECT_URI,
  scope: 'user:email',
  state: STATE
})}`;

// Store state in sessionStorage for verification
sessionStorage.setItem('oauth_state', STATE);

// Redirect user
window.location.href = githubAuthUrl;
```

**GitHub Authorization URL:**
```
https://github.com/login/oauth/authorize?
  client_id=Ov23liU7x20VoRInkAiq&
  redirect_uri=https://dothack.ainative.studio/auth/callback&
  scope=user:email&
  state=random_csrf_token_xyz
```

#### Step 2: GitHub Redirects to Callback

After user authorizes, GitHub redirects to:
```
https://dothack.ainative.studio/auth/callback?
  code=abc123def456&
  state=random_csrf_token_xyz
```

#### Step 3: Frontend Handles Callback

**Frontend OAuth callback page:**

```javascript
// /auth/callback route handler
import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

export default function OAuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const handleOAuthCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const storedState = sessionStorage.getItem('oauth_state');

      // Verify CSRF token
      if (state !== storedState) {
        console.error('CSRF token mismatch');
        navigate('/login?error=csrf_failed');
        return;
      }

      if (!code) {
        navigate('/login?error=no_code');
        return;
      }

      try {
        // Send code to AINative Auth API
        const response = await fetch('https://api.ainative.studio/v1/auth/github/callback', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            code: code,
            redirect_uri: 'https://dothack.ainative.studio/auth/callback',
            state: state
          })
        });

        if (!response.ok) {
          throw new Error('GitHub OAuth failed');
        }

        const data = await response.json();

        // Store access token
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));

        // Clean up
        sessionStorage.removeItem('oauth_state');

        // Redirect to dashboard
        navigate('/dashboard');

      } catch (error) {
        console.error('OAuth error:', error);
        navigate('/login?error=oauth_failed');
      }
    };

    handleOAuthCallback();
  }, [searchParams, navigate]);

  return <div>Authenticating with GitHub...</div>;
}
```

#### Step 4-5: AINative Exchanges Code for Token

**AINative backend handles token exchange:**

```python
# AINative Auth API - GitHub OAuth handler
@router.post("/github/callback", response_model=GitHubUserResponse)
async def github_oauth_callback(request: GitHubOAuthRequest):
    # Exchange authorization code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": request.code
            }
        )

        token_data = token_response.json()
        github_access_token = token_data.get("access_token")

        # Fetch user info
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {github_access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )

        github_user = user_response.json()

        # Fetch email if not public
        if not github_user.get("email"):
            email_response = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {github_access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            emails = email_response.json()
            primary_email = next((e["email"] for e in emails if e["primary"]), None)
            if primary_email:
                github_user["email"] = primary_email
```

#### Step 6: Create/Update User in Database

```python
# Upsert user in PostgreSQL
conn = await get_db_connection()
user = await conn.fetchrow(
    """
    INSERT INTO users (email, name, github_id, email_verified, password_hash)
    VALUES ($1, $2, $3, TRUE, $4)
    ON CONFLICT (email) DO UPDATE
    SET github_id = EXCLUDED.github_id,
        name = EXCLUDED.name,
        email_verified = TRUE
    RETURNING id, email, name, github_id, created_at
    """,
    github_user["email"],
    github_user["name"],
    str(github_user["id"]),
    get_password_hash(secrets.token_urlsafe(32))  # Random password for OAuth users
)
```

#### Step 7-8: Generate JWT and Return Response

```python
# Create AINative JWT tokens
user_id = str(user['id'])
access_token = create_access_token({"sub": user_id})
refresh_token = create_refresh_token(user_id)

# Return response
return GitHubUserResponse(
    access_token=access_token,
    token_type="bearer",
    user={
        "id": user_id,
        "email": user['email'],
        "name": user['name'],
        "email_verified": True,
        "github_id": user['github_id'],
        "created_at": user['created_at'].isoformat()
    }
)
```

**Response to Frontend:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "user-uuid-123",
    "email": "john@example.com",
    "name": "John Doe",
    "email_verified": true,
    "github_id": "12345678",
    "created_at": "2025-12-28T10:00:00Z"
  }
}
```

### API Reference

**Request Schema:**
```python
class GitHubOAuthRequest(BaseModel):
    code: str              # Authorization code from GitHub
    state: Optional[str]   # CSRF token for verification
    redirect_uri: Optional[str]  # Must match registered redirect URI
```

**Response Schema:**
```python
class GitHubUserResponse(BaseModel):
    access_token: str      # AINative JWT access token
    token_type: str        # "bearer"
    user: Dict[str, Any]   # User object with GitHub details
```

---

## LinkedIn OAuth Flow

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    DotHack Frontend                          │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ 1. User clicks "Login with LinkedIn"
                            │    Redirect to LinkedIn OAuth
                            │
                    ┌───────▼────────┐
                    │   LinkedIn     │
                    │  OAuth Server  │
                    │ (OpenID Connect)│
                    └───────┬────────┘
                            │
                            │ 2. User authorizes app
                            │    LinkedIn redirects with code
                            │
┌───────────────────────────▼──────────────────────────────────┐
│                    DotHack Frontend                          │
│                                                              │
│  Receives: ?code=xyz789&state=abc                           │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ 3. POST /v1/auth/linkedin/callback
                            │    { code, redirect_uri }
                            │
                    ┌───────▼────────┐
                    │   AINative     │
                    │   Auth API     │
                    │                │
                    │ ┌────────────┐ │
                    │ │ Exchange   │ │ 4. POST to LinkedIn
                    │ │ code for   │ │    /oauth/v2/accessToken
                    │ │ token      │ │    (OIDC flow)
                    │ └─────┬──────┘ │
                    │       │        │
                    │ ┌─────▼──────┐ │ 5. GET LinkedIn userinfo
                    │ │ Fetch user │ │    /v2/userinfo (OIDC)
                    │ │ profile    │ │
                    │ └─────┬──────┘ │
                    │       │        │
                    │ ┌─────▼──────┐ │ 6. Create/update user
                    │ │ Upsert     │ │    in PostgreSQL
                    │ │ user in DB │ │    Link LinkedIn ID
                    │ └─────┬──────┘ │
                    │       │        │
                    │ ┌─────▼──────┐ │ 7. Generate JWT tokens
                    │ │ Create JWT │ │    (access + refresh)
                    │ │ tokens     │ │
                    │ └────────────┘ │
                    └───────┬────────┘
                            │
                            │ 8. Return { access_token, user, expires_in }
                            │
┌───────────────────────────▼──────────────────────────────────┐
│                    DotHack Frontend                          │
│                                                              │
│  localStorage.setItem('access_token', token)                │
│  → User authenticated, redirect to dashboard                │
└──────────────────────────────────────────────────────────────┘
```

### Step-by-Step Implementation

#### Step 1: Initiate LinkedIn OAuth

**Frontend redirects user to LinkedIn:**

```javascript
const LINKEDIN_CLIENT_ID = process.env.VITE_LINKEDIN_CLIENT_ID;
const REDIRECT_URI = 'https://dothack.ainative.studio/auth/callback';
const STATE = generateRandomState();

const linkedInAuthUrl = `https://www.linkedin.com/oauth/v2/authorization?${new URLSearchParams({
  response_type: 'code',
  client_id: LINKEDIN_CLIENT_ID,
  redirect_uri: REDIRECT_URI,
  scope: 'openid profile email',
  state: STATE
})}`;

sessionStorage.setItem('oauth_state', STATE);
window.location.href = linkedInAuthUrl;
```

**LinkedIn Authorization URL:**
```
https://www.linkedin.com/oauth/v2/authorization?
  response_type=code&
  client_id=YOUR_LINKEDIN_CLIENT_ID&
  redirect_uri=https://dothack.ainative.studio/auth/callback&
  scope=openid%20profile%20email&
  state=random_csrf_token_abc
```

**Note:** LinkedIn uses OpenID Connect (OIDC), which provides standardized scopes:
- `openid` - Required for OIDC
- `profile` - Access to name, picture
- `email` - Access to email address

#### Step 2: LinkedIn Redirects to Callback

After authorization:
```
https://dothack.ainative.studio/auth/callback?
  code=xyz789abc&
  state=random_csrf_token_abc
```

#### Step 3: Frontend Handles Callback

**Same callback handler as GitHub, but detect provider:**

```javascript
const handleLinkedInCallback = async () => {
  const code = searchParams.get('code');
  const state = searchParams.get('state');

  // Send to LinkedIn endpoint
  const response = await fetch('https://api.ainative.studio/v1/auth/linkedin/callback', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      code: code,
      redirect_uri: 'https://dothack.ainative.studio/auth/callback',
      state: state
    })
  });

  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('user', JSON.stringify(data.user));

  navigate('/dashboard');
};
```

#### Step 4-5: AINative Exchanges Code for Token (OIDC)

**AINative backend handles OIDC token exchange:**

```python
@router.post("/linkedin/callback", response_model=LinkedInUserResponse)
async def linkedin_oauth_callback(request: LinkedInOAuthRequest):
    async with httpx.AsyncClient() as client:
        # Exchange code for access token (OIDC)
        token_response = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": request.code,
                "redirect_uri": request.redirect_uri,
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": LINKEDIN_CLIENT_SECRET
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )

        token_data = token_response.json()
        linkedin_access_token = token_data.get("access_token")
        token_expires_in = token_data.get("expires_in", 5183999)

        # Fetch user info via OIDC userinfo endpoint
        profile_response = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={
                "Authorization": f"Bearer {linkedin_access_token}"
            }
        )

        linkedin_user = profile_response.json()
        # linkedin_user contains: sub, name, email, picture, etc.
```

#### Step 6: Create/Update User in Database

```python
conn = await get_db_connection()
user = await conn.fetchrow(
    """
    INSERT INTO users (email, name, linkedin_id, email_verified, password_hash)
    VALUES ($1, $2, $3, TRUE, $4)
    ON CONFLICT (email) DO UPDATE
    SET linkedin_id = EXCLUDED.linkedin_id,
        name = EXCLUDED.name,
        email_verified = TRUE
    RETURNING id, email, name, linkedin_id, created_at
    """,
    linkedin_user["email"],
    linkedin_user["name"],
    linkedin_user["sub"],  # LinkedIn unique ID
    get_password_hash(secrets.token_urlsafe(32))
)
```

#### Step 7-8: Generate JWT and Return Response

```python
user_id = str(user['id'])
access_token = create_access_token({"sub": user_id})

return LinkedInUserResponse(
    access_token=access_token,
    token_type="bearer",
    expires_in=token_expires_in,
    user={
        "id": user_id,
        "email": user['email'],
        "name": user['name'],
        "email_verified": True,
        "linkedin_id": user['linkedin_id'],
        "created_at": user['created_at'].isoformat()
    }
)
```

**Response to Frontend:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 5183999,
  "user": {
    "id": "user-uuid-456",
    "email": "jane@example.com",
    "name": "Jane Smith",
    "email_verified": true,
    "linkedin_id": "linkedin-unique-id-123",
    "created_at": "2025-12-28T10:00:00Z"
  }
}
```

### API Reference

**Request Schema:**
```python
class LinkedInOAuthRequest(BaseModel):
    code: str              # Authorization code from LinkedIn
    state: Optional[str]   # CSRF token for verification
    redirect_uri: Optional[str]  # Must match registered redirect URI
```

**Response Schema:**
```python
class LinkedInUserResponse(BaseModel):
    access_token: str      # AINative JWT access token
    token_type: str        # "bearer"
    expires_in: int        # Token expiration in seconds (5183999 = ~60 days)
    user: Dict[str, Any]   # User object with LinkedIn details
```

---

## Frontend Integration Guide

### Complete OAuth Component

**Create `/src/components/OAuthButtons.tsx`:**

```typescript
import React from 'react';

interface OAuthButtonsProps {
  onLoading?: (isLoading: boolean) => void;
}

export default function OAuthButtons({ onLoading }: OAuthButtonsProps) {

  const generateState = (): string => {
    return Math.random().toString(36).substring(2, 15);
  };

  const handleGitHubLogin = () => {
    const state = generateState();
    sessionStorage.setItem('oauth_state', state);
    sessionStorage.setItem('oauth_provider', 'github');

    const githubUrl = `https://github.com/login/oauth/authorize?${new URLSearchParams({
      client_id: import.meta.env.VITE_GITHUB_CLIENT_ID,
      redirect_uri: `${window.location.origin}/auth/callback`,
      scope: 'user:email',
      state: state
    })}`;

    onLoading?.(true);
    window.location.href = githubUrl;
  };

  const handleLinkedInLogin = () => {
    const state = generateState();
    sessionStorage.setItem('oauth_state', state);
    sessionStorage.setItem('oauth_provider', 'linkedin');

    const linkedInUrl = `https://www.linkedin.com/oauth/v2/authorization?${new URLSearchParams({
      response_type: 'code',
      client_id: import.meta.env.VITE_LINKEDIN_CLIENT_ID,
      redirect_uri: `${window.location.origin}/auth/callback`,
      scope: 'openid profile email',
      state: state
    })}`;

    onLoading?.(true);
    window.location.href = linkedInUrl;
  };

  return (
    <div className="space-y-3">
      <button
        onClick={handleGitHubLogin}
        className="w-full flex items-center justify-center gap-3 px-4 py-2 border border-gray-300 rounded-md shadow-sm bg-white text-gray-700 hover:bg-gray-50"
      >
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 0C4.477 0 0 4.484 0 10.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0110 4.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.203 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.942.359.31.678.921.678 1.856 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0020 10.017C20 4.484 15.522 0 10 0z" clipRule="evenodd" />
        </svg>
        Continue with GitHub
      </button>

      <button
        onClick={handleLinkedInLogin}
        className="w-full flex items-center justify-center gap-3 px-4 py-2 border border-gray-300 rounded-md shadow-sm bg-blue-600 text-white hover:bg-blue-700"
      >
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path d="M4.98 3.5c0 1.381-1.11 2.5-2.48 2.5s-2.48-1.119-2.48-2.5c0-1.38 1.11-2.5 2.48-2.5s2.48 1.12 2.48 2.5zm.02 4.5h-5v16h5v-16zm7.982 0h-4.968v16h4.969v-8.399c0-4.67 6.029-5.052 6.029 0v8.399h4.988v-10.131c0-7.88-8.922-7.593-11.018-3.714v-2.155z"/>
        </svg>
        Continue with LinkedIn
      </button>
    </div>
  );
}
```

### OAuth Callback Handler

**Create `/src/pages/OAuthCallback.tsx`:**

```typescript
import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

export default function OAuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const storedState = sessionStorage.getItem('oauth_state');
      const provider = sessionStorage.getItem('oauth_provider');

      // Verify CSRF token
      if (state !== storedState) {
        setError('Security validation failed');
        setTimeout(() => navigate('/login?error=csrf'), 2000);
        return;
      }

      if (!code || !provider) {
        setError('Invalid OAuth response');
        setTimeout(() => navigate('/login?error=invalid'), 2000);
        return;
      }

      try {
        // Determine endpoint based on provider
        const endpoint = provider === 'github'
          ? '/v1/auth/github/callback'
          : '/v1/auth/linkedin/callback';

        const response = await fetch(`https://api.ainative.studio${endpoint}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            code: code,
            redirect_uri: `${window.location.origin}/auth/callback`,
            state: state
          })
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Authentication failed');
        }

        const data = await response.json();

        // Store authentication data
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));

        // Clean up
        sessionStorage.removeItem('oauth_state');
        sessionStorage.removeItem('oauth_provider');

        // Redirect to dashboard
        navigate('/dashboard');

      } catch (err) {
        console.error('OAuth error:', err);
        setError(err instanceof Error ? err.message : 'Authentication failed');
        setTimeout(() => navigate('/login?error=auth_failed'), 2000);
      }
    };

    handleCallback();
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 text-center">
        {error ? (
          <>
            <div className="text-red-500 text-xl">❌ {error}</div>
            <div className="text-gray-600">Redirecting to login...</div>
          </>
        ) : (
          <>
            <div className="text-blue-500 text-xl">🔄 Authenticating...</div>
            <div className="text-gray-600">Please wait while we log you in</div>
          </>
        )}
      </div>
    </div>
  );
}
```

### Route Configuration

**Add to `/src/App.tsx`:**

```typescript
import OAuthCallback from './pages/OAuthCallback';

// In your routes:
<Route path="/auth/callback" element={<OAuthCallback />} />
```

---

## Environment Variables

### Backend (AINative)

```bash
# GitHub OAuth
GITHUB_CLIENT_ID=Ov23liU7x20VoRInkAiq
GITHUB_CLIENT_SECRET=your_github_client_secret

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_REDIRECT_URI=https://api.ainative.studio/v1/auth/linkedin/callback
```

### Frontend (DotHack)

```bash
# OAuth Client IDs (public, safe to expose)
VITE_GITHUB_CLIENT_ID=Ov23liU7x20VoRInkAiq
VITE_LINKEDIN_CLIENT_ID=your_linkedin_client_id

# API Base URL
VITE_API_BASE_URL=https://api.ainative.studio
```

---

## Security Considerations

### CSRF Protection

Both flows use the `state` parameter for CSRF protection:

1. Generate random state before redirect
2. Store in sessionStorage
3. Verify match on callback
4. Fail authentication if mismatch

### Token Storage

**Recommended:**
- Store access tokens in `localStorage` for persistence
- Store refresh tokens in secure httpOnly cookies (if available)
- Never store tokens in URL parameters or sessionStorage

### Redirect URI Validation

- Both GitHub and LinkedIn validate redirect_uri against registered URIs
- Must match exactly (including protocol, domain, port, path)
- AINative validates redirect_uri on callback endpoint

### Error Handling

**Common OAuth Errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| `access_denied` | User cancelled authorization | Redirect to login with message |
| `invalid_grant` | Code expired or invalid | Retry OAuth flow |
| `redirect_uri_mismatch` | Redirect URI doesn't match | Update OAuth app settings |
| `invalid_state` | CSRF token mismatch | Clear sessionStorage and retry |

---

## Testing

### Development Testing

**Test GitHub OAuth:**
```bash
# 1. Start frontend
npm run dev

# 2. Click "Login with GitHub"
# 3. Authorize app
# 4. Verify redirect and token storage
```

**Test LinkedIn OAuth:**
```bash
# Same process, click "Login with LinkedIn"
```

### Manual Testing Checklist

- [ ] GitHub OAuth initiates correctly
- [ ] LinkedIn OAuth initiates correctly
- [ ] CSRF state validation works
- [ ] User redirects to dashboard after auth
- [ ] Access token stored in localStorage
- [ ] User object contains OAuth provider ID
- [ ] Email verification bypassed for OAuth users
- [ ] Existing users can link OAuth accounts

---

## Troubleshooting

### GitHub OAuth Issues

**Issue:** "Email not found"
**Solution:** User must have public email or grant `user:email` scope

**Issue:** "Redirect URI mismatch"
**Solution:** Verify GitHub OAuth app settings match exactly

### LinkedIn OAuth Issues

**Issue:** "Invalid scope"
**Solution:** Ensure scopes are `openid profile email` (space-separated)

**Issue:** "Token exchange failed"
**Solution:** LinkedIn requires `application/x-www-form-urlencoded` format

---

## Additional Resources

- **GitHub OAuth Docs:** https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps
- **LinkedIn OIDC Docs:** https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2
- **AINative Auth API:** https://api.ainative.studio/docs#/Authentication
- **Support:** hello@ainative.studio
