# DotHack Backend Documentation

**Last Updated:** 2025-12-28

---

## 🚨 CRITICAL: Authentication Architecture

**READ THIS FIRST before implementing any authentication!**

DotHack Backend **MUST USE** the existing AINative Studio authentication system. Do **NOT** build standalone authentication.

### Start Here

1. **[AUTHENTICATION_ARCHITECTURE.md](AUTHENTICATION_ARCHITECTURE.md)** - Complete overview (START HERE!)
2. **[AINATIVE_AUTH_INTEGRATION.md](AINATIVE_AUTH_INTEGRATION.md)** - Implementation guide with code examples
3. **[PRD_AUTH_UPDATE.md](PRD_AUTH_UPDATE.md)** - Updated PRD section replacing standalone auth

### Quick Summary

```
✅ DO:
- Use AINative Auth API (https://api.ainative.studio/v1/auth/*)
- Verify tokens via /v1/auth/me
- Store AINative user_id in hackathon_participants
- Implement role-based authorization in DotHack

❌ DON'T:
- Build custom /auth/register, /auth/login endpoints
- Store passwords in DotHack database
- Generate JWT tokens in DotHack
- Implement OAuth flows in DotHack
```

---

## Why This Matters

| ✅ Using AINative Auth | ❌ Building Standalone Auth |
|------------------------|----------------------------|
| Users have ONE account across all AINative products | Users need separate accounts for each product |
| SSO works automatically | No SSO capability |
| GitHub/LinkedIn OAuth pre-built | Must implement OAuth from scratch |
| Production-grade security | Security burden on DotHack team |
| Zero maintenance cost | Ongoing security updates needed |
| Unified user experience | Fragmented UX |

---

## Implementation Checklist

### Backend Setup

- [ ] Read [AUTHENTICATION_ARCHITECTURE.md](AUTHENTICATION_ARCHITECTURE.md)
- [ ] Read [AINATIVE_AUTH_INTEGRATION.md](AINATIVE_AUTH_INTEGRATION.md)
- [ ] Create AINative auth client wrapper (`integrations/ainative/auth_client.py`)
- [ ] Create authentication dependency (`api/dependencies.py`)
- [ ] Implement role checking service (`services/authorization.py`)
- [ ] Protect all endpoints with `Depends(get_current_user)`
- [ ] Test with AINative test token: `ALWAYS-WORKS-TOKEN-12345`

### Frontend Setup

- [ ] Add "Login with GitHub" button → redirects to AINative OAuth
- [ ] Add "Login with LinkedIn" button → redirects to AINative OAuth
- [ ] Add "Login with Email" form → POSTs to AINative `/v1/auth/login`
- [ ] Store returned JWT token in localStorage
- [ ] Add `Authorization: Bearer {token}` header to all API requests

### Testing

- [ ] Register user via AINative `/v1/auth/register`
- [ ] Login via AINative `/v1/auth/login`
- [ ] Create hackathon with authenticated user
- [ ] Verify organizer role is created in `hackathon_participants`
- [ ] Test role-based authorization (ORGANIZER, BUILDER, JUDGE, MENTOR)

---

## Documentation Structure

```
docs/
├── README.md (this file)
│
├── AUTHENTICATION_ARCHITECTURE.md  ← START HERE
│   └── Complete auth architecture overview
│
├── AINATIVE_AUTH_INTEGRATION.md
│   └── Implementation guide with code examples
│
└── PRD_AUTH_UPDATE.md
    └── Updated PRD section (replace Section 7.3)
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────┐
│         DotHack Frontend                │
│      (Web App / Mobile App)             │
└─────────────────┬───────────────────────┘
                  │
                  │ 1. Login/Register
                  │
        ┌─────────▼──────────┐
        │   AINative Auth    │ ← ALL authentication here
        │   /v1/auth/*       │
        └─────────┬──────────┘
                  │
                  │ 2. Returns JWT token
                  │
┌─────────────────▼───────────────────────┐
│         DotHack Backend                 │
│        (Python FastAPI)                 │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  Auth Middleware                 │  │
│  │  1. Verify token via AINative    │  │
│  │  2. Get user info                │  │
│  │  3. Check role in ZeroDB         │  │
│  │  4. Grant/deny access            │  │
│  └──────────────────────────────────┘  │
│                                         │
└─────────────────┬───────────────────────┘
                  │
                  │ 3. Query roles
                  │
        ┌─────────▼──────────┐
        │      ZeroDB        │ ← Store roles here
        │ hackathon_         │
        │ participants       │
        └────────────────────┘
```

---

## Key Concepts

### Authentication vs Authorization

**Authentication (handled by AINative):**
- ✅ Who is the user?
- ✅ Is the token valid?
- ✅ Email/password verification
- ✅ OAuth (GitHub, LinkedIn)
- ✅ JWT token generation

**Authorization (handled by DotHack):**
- ✅ What can the user do?
- ✅ Is user an ORGANIZER for this hackathon?
- ✅ Can user score this submission?
- ✅ Role-based access control

### User ID Flow

```
1. User registers via AINative
   → AINative creates user with id="user-uuid-123"

2. User joins hackathon via DotHack
   → DotHack creates entry in hackathon_participants:
   {
     "participant_id": "user-uuid-123",  ← AINative user.id
     "hackathon_id": "hack-456",
     "role": "BUILDER"
   }

3. User submits project
   → DotHack verifies token via AINative /v1/auth/me
   → Gets user_id from response
   → Checks if user_id exists in hackathon_participants
   → Grants access if role=BUILDER and team member
```

---

## Environment Variables

```bash
# AINative Authentication (REQUIRED)
AINATIVE_API_URL=https://api.ainative.studio
AINATIVE_API_KEY=your_api_key_here  # For server-to-server calls

# ZeroDB (REQUIRED)
ZERODB_API_KEY=your_zerodb_api_key
ZERODB_PROJECT_ID=your_project_uuid
ZERODB_BASE_URL=https://api.ainative.studio
```

---

## Support

- **AINative Auth Docs:** https://api.ainative.studio/docs#/Authentication
- **DotHack PRD:** [/dothack-backendprd.md](../dothack-backendprd.md)
- **Support:** hello@ainative.studio

---

## Common Mistakes to Avoid

### ❌ Mistake 1: Building custom /auth endpoints

```python
# WRONG - Don't do this!
@router.post("/auth/register")
async def register_user(user_data: UserCreate):
    # This should NOT exist in DotHack
    pass
```

### ✅ Correct: Use AINative endpoints

```python
# CORRECT - Frontend calls AINative directly
# POST https://api.ainative.studio/v1/auth/register
```

### ❌ Mistake 2: Storing passwords

```python
# WRONG - Don't do this!
hackathon_user = {
    "email": "user@example.com",
    "password_hash": bcrypt.hash(password)  # NO!
}
```

### ✅ Correct: Store only AINative user_id

```python
# CORRECT
hackathon_participant = {
    "participant_id": "user-uuid-from-ainative",
    "role": "BUILDER"
}
```

### ❌ Mistake 3: Trusting client user_id

```python
# WRONG - Don't trust client!
@router.post("/hackathons")
async def create_hackathon(user_id: str):  # Client can fake this!
    pass
```

### ✅ Correct: Verify token

```python
# CORRECT
@router.post("/hackathons")
async def create_hackathon(
    current_user: dict = Depends(get_current_user)  # Verified via AINative
):
    user_id = current_user["id"]  # Trustworthy
    pass
```

---

**REMEMBER: Do NOT build standalone authentication. Use AINative Auth API.**
