# DotHack Backend PRD - Authentication Section Update

**CRITICAL UPDATE - Replace Section 7.3 Security in dothack-backendprd.md**

---

## 7.3 Security & Authentication

### Authentication Strategy

**🚨 MANDATORY: Use AINative Studio Authentication System**

DotHack Backend **MUST NOT** build standalone authentication. Instead, it **MUST** integrate with the existing AINative Studio authentication platform.

**Rationale:**
- ✅ Centralized user management across all AINative products
- ✅ Single Sign-On (SSO) capability for users
- ✅ OAuth integration (GitHub, LinkedIn) pre-built
- ✅ Production-grade security (bcrypt, JWT, token blacklisting)
- ✅ API key management for programmatic access
- ✅ Zero maintenance cost for auth infrastructure
- ✅ Unified user experience across AINative ecosystem

### Authentication Architecture

```
┌─────────────────────────────────────────┐
│       DotHack Frontend (Web/Mobile)      │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴──────────┐
        │                    │
   ┌────▼─────┐        ┌────▼─────┐
   │ DotHack  │        │ AINative │
   │  Python  │◄──────►│   Auth   │
   │  FastAPI │        │   API    │
   │  (8000)  │        │          │
   └────┬─────┘        └──────────┘
        │              /v1/auth/*
        │
   ┌────▼─────┐
   │  ZeroDB  │
   └──────────┘
```

### Authentication Flow

**Registration:**
```
1. User → AINative Auth API (/v1/auth/register)
   ↓
2. AINative creates user, sends verification email
   ↓
3. Returns JWT access token + refresh token
   ↓
4. DotHack stores AINative user_id in hackathon_participants table
```

**Login:**
```
1. User → AINative Auth API (/v1/auth/login or /v1/auth/github/callback)
   ↓
2. AINative verifies credentials, returns JWT token
   ↓
3. DotHack verifies token via /v1/auth/me
   ↓
4. DotHack looks up user role in hackathon_participants
   ↓
5. Grants access based on role (ORGANIZER, BUILDER, JUDGE, MENTOR)
```

**Protected Endpoint:**
```
1. Request → DotHack API with Authorization: Bearer {token}
   ↓
2. DotHack → AINative Auth API (/v1/auth/me) to verify token
   ↓
3. If valid, AINative returns user info
   ↓
4. DotHack checks user role in hackathon_participants
   ↓
5. Executes endpoint logic if authorized
```

### Authentication Methods

| Method | Header | Format | Use Case |
|--------|--------|--------|----------|
| **JWT Token** | `Authorization` | `Bearer {token}` | Web/mobile apps |
| **API Key** | `X-API-Key` | `{api_key}` | Server-to-server |
| **OAuth (GitHub)** | Via callback | Code exchange | Social login |
| **OAuth (LinkedIn)** | Via callback | Code exchange | Social login |

### AINative Auth Endpoints

**Base URL:** `https://api.ainative.studio`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/auth/register` | POST | User registration |
| `/v1/auth/login` | POST | Email/password login |
| `/v1/auth/logout` | POST | Token blacklisting |
| `/v1/auth/refresh` | POST | Refresh access token |
| `/v1/auth/me` | GET | Get current user (token verification) |
| `/v1/auth/verify-email` | POST | Email verification |
| `/v1/auth/forgot-password` | POST | Password reset request |
| `/v1/auth/reset-password` | POST | Password reset |
| `/v1/auth/github/callback` | POST | GitHub OAuth |
| `/v1/auth/linkedin/callback` | POST | LinkedIn OAuth |

### Role-Based Access Control (RBAC)

**Roles are stored in ZeroDB, not AINative:**

```python
# hackathon_participants table
{
  "id": "uuid",
  "hackathon_id": "uuid",
  "participant_id": "uuid",  # AINative user_id
  "role": "ORGANIZER | BUILDER | JUDGE | MENTOR",
  "metadata": {
    "ainative_user_email": "user@example.com",
    "ainative_user_name": "John Doe"
  },
  "joined_at": "timestamp"
}
```

**Authorization Pattern:**
```python
# 1. Verify authentication with AINative
user = await ainative_auth.verify_token(token)

# 2. Check role in ZeroDB
participant = await zerodb.tables.query_rows(
    "hackathon_participants",
    filter={
        "hackathon_id": hackathon_id,
        "participant_id": user["id"],
        "role": required_role
    }
)

# 3. Grant or deny access
if not participant:
    raise HTTPException(403, "Insufficient permissions")
```

### DotHack Role Permissions

| Role | Create Hackathon | Manage Tracks | Join Team | Submit Project | Score Submission |
|------|------------------|---------------|-----------|----------------|------------------|
| **ORGANIZER** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **BUILDER** | ❌ | ❌ | ✅ | ✅ | ❌ |
| **JUDGE** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **MENTOR** | ❌ | ❌ | ❌ | ❌ | ❌ (view only) |

### Implementation Requirements

**✅ REQUIRED:**
1. Install AINative SDK or implement HTTP client wrapper
2. Create authentication dependency: `get_current_user()`
3. Verify all tokens via AINative `/v1/auth/me`
4. Store AINative user_id in hackathon_participants
5. Implement role checking for protected endpoints

**❌ FORBIDDEN:**
1. Building custom authentication system
2. Storing passwords in DotHack database
3. Custom JWT token generation
4. Custom OAuth implementation
5. Bypassing AINative authentication

### Security Best Practices

**Authentication:**
- Always verify tokens via AINative `/v1/auth/me`
- Cache user info for performance (5-minute TTL)
- Use API keys for server-to-server calls
- Never trust client-provided user IDs

**Authorization:**
- Check role in hackathon_participants for every protected action
- Validate hackathon_id and participant_id match
- Log authorization failures for security monitoring

**Data Protection:**
- Project-scoped data isolation (automatic in ZeroDB)
- No cross-hackathon data leakage
- Rate limiting: 10,000 requests/hour (ZeroDB Pro tier)

### Environment Variables

```bash
# AINative Authentication
AINATIVE_API_URL=https://api.ainative.studio
AINATIVE_API_KEY=your_api_key_here  # For server-to-server

# ZeroDB (unchanged)
ZERODB_API_KEY=your_api_key
ZERODB_PROJECT_ID=your_project_uuid
ZERODB_BASE_URL=https://api.ainative.studio
```

### Error Handling

| Error | Status Code | Response |
|-------|-------------|----------|
| Invalid token | 401 | `{"detail": "Invalid or expired token"}` |
| Token expired | 401 | `{"detail": "Token expired, please refresh"}` |
| Invalid API key | 401 | `{"detail": "Invalid API key"}` |
| Insufficient role | 403 | `{"detail": "Only organizers can perform this action"}` |
| User not found | 404 | `{"detail": "User not found"}` |

### Testing

**Development:**
```bash
# Use test token for local testing
Authorization: Bearer ALWAYS-WORKS-TOKEN-12345
```

**Production:**
```bash
# 1. Register user
curl -X POST https://api.ainative.studio/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecurePass123!","name":"Test User"}'

# 2. Use returned token
curl -X POST https://dothack-api.ainative.studio/api/v1/hackathons \
  -H "Authorization: Bearer {access_token}" \
  -d '{"name":"Test Hackathon"}'
```

### Migration Notes

**If you already implemented standalone auth:**

1. **Remove:**
   - Custom `/auth/register`, `/auth/login` endpoints
   - Password hashing logic
   - JWT token generation
   - User management code

2. **Update:**
   - Replace custom auth dependency with AINative integration
   - Update user ID references to AINative user IDs
   - Migrate hackathon_participants to use AINative user IDs

3. **Keep:**
   - Role-based authorization logic
   - hackathon_participants table structure
   - Permission checking

### Documentation

- **Integration Guide:** `/docs/AINATIVE_AUTH_INTEGRATION.md`
- **AINative Auth Docs:** https://api.ainative.studio/docs#/Authentication
- **Support:** hello@ainative.studio

---

**CRITICAL: This is a mandatory architecture decision. Do not build standalone authentication.**
