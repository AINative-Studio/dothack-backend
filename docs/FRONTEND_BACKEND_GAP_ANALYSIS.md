# Frontend-Backend GAP Analysis
**Date:** 2025-12-30
**Analysis Scope:** DotHack Frontend vs Backend Integration

---

## Executive Summary

This document provides a comprehensive gap analysis between the DotHack frontend (Next.js) and backend (FastAPI) implementations, identifying:
1. Mocked/hardcoded data in frontend
2. Supabase schema migration needs
3. Missing backend endpoints
4. Frontend integration requirements

---

## 1. Frontend Technology Stack

**Framework:** Next.js 13 (App Router) + TypeScript 5.2.2
**Database:** Supabase (public data only) + In-memory React Context (app data)
**UI:** Tailwind CSS + shadcn/ui (Radix primitives)
**State:** React Context API (no persistence)
**Deployment:** Netlify

**Critical Finding:** Frontend is currently a demonstration-only application with NO data persistence beyond Supabase for featured content. All hackathon management data exists only in browser memory.

---

## 2. Supabase Schema Migration to ZeroDB

### 2.1 Current Supabase Tables

**Table 1: `featured_hackathons`**
```sql
CREATE TABLE featured_hackathons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    logo_url TEXT,
    days_left INTEGER,
    is_online BOOLEAN DEFAULT false,
    prize_amount NUMERIC,
    participant_count INTEGER DEFAULT 0,
    is_featured BOOLEAN DEFAULT false,
    display_order INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index
CREATE INDEX idx_featured_hackathons_display_order
ON featured_hackathons(display_order);

-- RLS Policy (Public Read)
ALTER TABLE featured_hackathons ENABLE ROW LEVEL SECURITY;
CREATE POLICY featured_hackathons_public_read
ON featured_hackathons FOR SELECT
USING (is_featured = true);
```

**Table 2: `hackathon_themes`**
```sql
CREATE TABLE hackathon_themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    theme_name TEXT UNIQUE NOT NULL,
    hackathon_count INTEGER DEFAULT 0,
    total_prizes NUMERIC DEFAULT 0,
    display_order INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index
CREATE INDEX idx_hackathon_themes_display_order
ON hackathon_themes(display_order);

-- RLS Policy (Public Read)
ALTER TABLE hackathon_themes ENABLE ROW LEVEL SECURITY;
CREATE POLICY hackathon_themes_public_read
ON hackathon_themes FOR SELECT
USING (true);
```

### 2.2 ZeroDB Migration Plan

**Action Required:** Create two new tables in ZeroDB

**Migration Script Needed:**
```python
# /scripts/migrate_supabase_to_zerodb.py

import asyncio
from integrations.zerodb.client import ZeroDBClient

async def create_featured_hackathons_table():
    """Create featured_hackathons table in ZeroDB"""
    async with ZeroDBClient() as client:
        schema = {
            "fields": {
                "title": {"type": "string", "required": True},
                "logo_url": {"type": "string"},
                "days_left": {"type": "integer"},
                "is_online": {"type": "boolean", "default": False},
                "prize_amount": {"type": "number"},
                "participant_count": {"type": "integer", "default": 0},
                "is_featured": {"type": "boolean", "default": False},
                "display_order": {"type": "integer"},
                "created_at": {"type": "timestamp"}
            },
            "indexes": ["display_order", "is_featured"]
        }

        await client.tables.create_table(
            table_name="featured_hackathons",
            schema=schema,
            description="Featured hackathons for homepage"
        )

async def create_hackathon_themes_table():
    """Create hackathon_themes table in ZeroDB"""
    async with ZeroDBClient() as client:
        schema = {
            "fields": {
                "theme_name": {"type": "string", "required": True, "unique": True},
                "hackathon_count": {"type": "integer", "default": 0},
                "total_prizes": {"type": "number", "default": 0},
                "display_order": {"type": "integer"},
                "created_at": {"type": "timestamp"}
            },
            "indexes": ["display_order", "theme_name"]
        }

        await client.tables.create_table(
            table_name="hackathon_themes",
            schema=schema,
            description="Hackathon themes with statistics"
        )
```

**Backend API Endpoints Needed:**
- `GET /api/v1/featured-hackathons` - List featured hackathons (public)
- `POST /api/v1/featured-hackathons` - Create featured hackathon (ORGANIZER only)
- `PUT /api/v1/featured-hackathons/{id}` - Update featured hackathon
- `DELETE /api/v1/featured-hackathons/{id}` - Remove from featured

- `GET /api/v1/hackathon-themes` - List themes with stats (public)
- `POST /api/v1/hackathon-themes` - Create theme (ORGANIZER only)
- `PUT /api/v1/hackathon-themes/{id}` - Update theme stats

---

## 3. Frontend Data Models vs Backend Schema

### 3.1 Model Comparison

| Frontend Model | Backend Schema | Status | Gaps |
|----------------|----------------|--------|------|
| `Hackathon` | `HackathonResponse` | ⚠️ Partial | Missing: `logo_url`, `is_online`, `participant_count` |
| `Track` | Not implemented | ❌ Missing | Need Track CRUD endpoints |
| `Participant` | Not implemented | ❌ Missing | Need Participant CRUD endpoints |
| `HackathonParticipant` | Not implemented | ❌ Missing | Need role assignment endpoints |
| `Team` | `TeamResponse` | ✅ Exists | - |
| `TeamMember` | `TeamMemberResponse` | ✅ Exists | - |
| `Project` | Not implemented | ❌ Missing | Need Project CRUD endpoints |
| `Submission` | `SubmissionResponse` | ✅ Exists | - |
| `Rubric` | Not implemented | ❌ Missing | Need Rubric CRUD endpoints |
| `Score` | `ScoreResponse` | ✅ Exists | - |
| `Prize` | Not implemented | ❌ Missing | Need Prize CRUD endpoints |
| `Invitation` | Not implemented | ❌ Missing | Need Invitation system |

### 3.2 Frontend Type Definitions

**From `/frontend/lib/types.ts`:**

```typescript
// MISSING IN BACKEND
type Track = {
  track_id: string
  hackathon_id: string
  name: string
  description: string
}

// MISSING IN BACKEND
type Participant = {
  participant_id: string
  name: string
  email: string
  org?: string
}

// MISSING IN BACKEND
type HackathonParticipant = {
  hackathon_id: string
  participant_id: string
  role: 'BUILDER' | 'JUDGE' | 'MENTOR' | 'ORGANIZER' | 'SPONSOR'
}

// MISSING IN BACKEND
type Project = {
  project_id: string
  hackathon_id: string
  team_id: string
  title: string
  one_liner: string
  status: 'IDEA' | 'BUILDING' | 'SUBMITTED'
  repo_url?: string
  demo_url?: string
}

// MISSING IN BACKEND
type Rubric = {
  rubric_id: string
  hackathon_id: string
  title: string
  criteria_json: string  // JSON string of criteria
}

// MISSING IN BACKEND
type Prize = {
  prize_id: string
  hackathon_id: string
  title: string
  description: string
  amount: number
  rank: number
  track_id?: string
}

// MISSING IN BACKEND
type Invitation = {
  invitation_id: string
  hackathon_id: string
  email: string
  role: UserRole
  status: 'PENDING' | 'ACCEPTED' | 'DECLINED'
  message?: string
  created_at: string
}
```

---

## 4. Missing Backend Endpoints

### 4.1 High Priority (Core Functionality)

**Tracks API** (Currently MISSING)
```
POST   /api/v1/hackathons/{id}/tracks          - Create track
GET    /api/v1/hackathons/{id}/tracks          - List tracks
GET    /api/v1/hackathons/{id}/tracks/{track_id} - Get track
PUT    /api/v1/hackathons/{id}/tracks/{track_id} - Update track
DELETE /api/v1/hackathons/{id}/tracks/{track_id} - Delete track
```

**Participants API** (Currently MISSING)
```
POST   /api/v1/participants                    - Create participant profile
GET    /api/v1/participants/{id}              - Get participant
PUT    /api/v1/participants/{id}              - Update participant
GET    /api/v1/hackathons/{id}/participants   - List participants in hackathon
POST   /api/v1/hackathons/{id}/participants   - Add participant to hackathon
DELETE /api/v1/hackathons/{id}/participants/{participant_id} - Remove participant
PUT    /api/v1/hackathons/{id}/participants/{participant_id}/role - Update role
```

**Projects API** (Currently MISSING)
```
POST   /api/v1/hackathons/{id}/projects       - Create project
GET    /api/v1/hackathons/{id}/projects       - List projects
GET    /api/v1/hackathons/{id}/projects/{project_id} - Get project
PUT    /api/v1/hackathons/{id}/projects/{project_id} - Update project
DELETE /api/v1/hackathons/{id}/projects/{project_id} - Delete project
PATCH  /api/v1/hackathons/{id}/projects/{project_id}/status - Update status
```

**Rubrics API** (Currently MISSING)
```
POST   /api/v1/hackathons/{id}/rubrics        - Create rubric
GET    /api/v1/hackathons/{id}/rubrics        - List rubrics
GET    /api/v1/hackathons/{id}/rubrics/{rubric_id} - Get rubric
PUT    /api/v1/hackathons/{id}/rubrics/{rubric_id} - Update rubric
DELETE /api/v1/hackathons/{id}/rubrics/{rubric_id} - Delete rubric
```

**Prizes API** (Currently MISSING)
```
POST   /api/v1/hackathons/{id}/prizes         - Create prize
GET    /api/v1/hackathons/{id}/prizes         - List prizes
GET    /api/v1/hackathons/{id}/prizes/{prize_id} - Get prize
PUT    /api/v1/hackathons/{id}/prizes/{prize_id} - Update prize
DELETE /api/v1/hackathons/{id}/prizes/{prize_id} - Delete prize
```

**Invitations API** (Currently MISSING)
```
POST   /api/v1/hackathons/{id}/invitations    - Send invitation
GET    /api/v1/hackathons/{id}/invitations    - List invitations
GET    /api/v1/invitations/{token}            - Get invitation by token
PUT    /api/v1/invitations/{token}/accept     - Accept invitation
PUT    /api/v1/invitations/{token}/decline    - Decline invitation
DELETE /api/v1/hackathons/{id}/invitations/{invitation_id} - Delete invitation
```

### 4.2 Medium Priority (Enhanced Functionality)

**Hackathon Extensions** (Partial gaps in existing API)
```
PATCH  /api/v1/hackathons/{id}/logo           - Upload hackathon logo
GET    /api/v1/hackathons/featured            - Get featured hackathons
GET    /api/v1/hackathons/public              - List public hackathons
GET    /api/v1/hackathons/themes              - Get hackathon themes
```

**Dashboard Statistics** (Currently MISSING)
```
GET    /api/v1/hackathons/{id}/stats          - Get hackathon statistics
GET    /api/v1/hackathons/{id}/overview       - Get overview dashboard data
GET    /api/v1/dashboard/organizer            - Organizer dashboard data
GET    /api/v1/dashboard/builder              - Builder dashboard data
GET    /api/v1/dashboard/judge                - Judge dashboard data
```

---

## 5. Hardcoded Data & Mock Values

### 5.1 Marketing Content (Hardcoded)

**Location:** `/frontend/app/(marketing)/page.tsx`

```typescript
// Community stats (hardcoded)
{
  title: "4 million+",
  description: "Developers in our community"
}

// Company logos (hardcoded text)
const companies = [
  "Microsoft", "Google", "Meta", "AWS", "Atlassian"
]

// Testimonials (hardcoded)
{
  quote: "DotHack helped us run our largest hackathon...",
  author: "John Smith",
  role: "Innovation Manager, Microsoft"
}
```

**Recommendation:** Move to CMS or backend API for dynamic content management.

### 5.2 Role-Based Navigation (Hardcoded)

**Location:** `/frontend/app/(app)/layout.tsx`

```typescript
const navLinks = [
  {
    href: '/hackathons',
    label: 'Hackathons',
    icon: Code2,
    roles: ['ORGANIZER', 'BUILDER', 'JUDGE']
  },
  {
    href: '/api-settings',
    label: 'API',
    icon: Key,
    roles: ['ORGANIZER']
  },
]
```

**Recommendation:** Keep client-side for performance. No API needed.

### 5.3 Status Color Mapping (Hardcoded)

**Location:** Multiple pages

```typescript
const getStatusColor = (status: HackathonStatus) => {
  switch (status) {
    case 'DRAFT': return 'bg-slate-100 text-slate-800'
    case 'LIVE': return 'bg-emerald-100 text-emerald-800'
    case 'CLOSED': return 'bg-rose-100 text-rose-800'
  }
}
```

**Recommendation:** Keep client-side in UI utility function. No API needed.

### 5.4 Form Placeholders (Hardcoded)

**Examples:**
- "Spring Hackathon 2024" (hackathon name)
- "AI & Machine Learning" (track name)
- Sample JSON for rubric criteria

**Recommendation:** Keep as UX helpers. No backend required.

---

## 6. Frontend Integration Requirements

### 6.1 API Client Setup Needed

**Create:** `/frontend/lib/api-client.ts`

```typescript
import { env } from './env'

export const API_BASE_URL = env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export class ApiClient {
  private baseUrl: string
  private token: string | null = null

  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  setAuthToken(token: string) {
    this.token = token
  }

  async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers = {
      'Content-Type': 'application/json',
      ...(this.token && { Authorization: `Bearer ${this.token}` }),
      ...options.headers,
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`)
    }

    return response.json()
  }

  // Hackathons
  async getHackathons() {
    return this.request('/api/v1/hackathons')
  }

  async createHackathon(data: HackathonCreateRequest) {
    return this.request('/api/v1/hackathons', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  // ... more methods
}

export const apiClient = new ApiClient()
```

### 6.2 Environment Variables Required

**Add to `/frontend/.env.local`:**
```bash
# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_VERSION=v1

# AINative Authentication
NEXT_PUBLIC_AINATIVE_AUTH_URL=https://api.ainative.studio/v1/auth

# Feature Flags
NEXT_PUBLIC_ENABLE_ANALYTICS=true
NEXT_PUBLIC_ENABLE_RECOMMENDATIONS=true
```

### 6.3 Replace React Context with API Calls

**Current:** All data in `/frontend/lib/store.tsx` (in-memory)
**Target:** Replace with API calls + React Query for caching

**Migration Strategy:**
1. Install `@tanstack/react-query`
2. Create API hooks: `useHackathons()`, `useTeams()`, etc.
3. Replace Context provider with QueryClientProvider
4. Update components to use hooks instead of Context

**Example Hook:**
```typescript
// /frontend/hooks/use-hackathons.ts
import { useQuery, useMutation } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

export function useHackathons() {
  return useQuery({
    queryKey: ['hackathons'],
    queryFn: () => apiClient.getHackathons(),
  })
}

export function useCreateHackathon() {
  return useMutation({
    mutationFn: (data: HackathonCreateRequest) =>
      apiClient.createHackathon(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hackathons'] })
    },
  })
}
```

### 6.4 Authentication Integration

**Current:** No authentication (demo mode)
**Required:** AINative Auth integration

**Implementation:**
1. Add AINative Auth client
2. Create auth context/hooks
3. Protect routes with middleware
4. Pass JWT token to backend API

---

## 7. Schema Gap Summary

### 7.1 Tables Needed in ZeroDB

| Table Name | Priority | Purpose | Frontend Usage |
|------------|----------|---------|----------------|
| `featured_hackathons` | High | Homepage featured list | HackathonsForYou component |
| `hackathon_themes` | High | Homepage theme stats | TopHackathonThemes component |
| `tracks` | Critical | Hackathon categories | Setup page, team selection |
| `participants` | Critical | User profiles | All participant management |
| `hackathon_participants` | Critical | Role assignments | Access control, dashboards |
| `projects` | Critical | Project submissions | Projects page, leaderboard |
| `rubrics` | Critical | Judging criteria | Setup page, judging flow |
| `prizes` | High | Prize information | Prizes page, leaderboard |
| `invitations` | Medium | Team invites | Participant invitation flow |

### 7.2 Backend Endpoint Gaps

**Completely Missing:** 7 core resource types (see Section 4.1)
**Partially Implemented:** 2 resource types (hackathons, teams)
**Fully Implemented:** 2 resource types (submissions, scores)

---

## 8. Recommendations

### 8.1 Immediate Actions (Week 1)

1. **Create ZeroDB Tables**
   - Migrate Supabase schema to ZeroDB
   - Create Track, Participant, Project, Rubric, Prize, Invitation tables
   - Run `/scripts/setup-zerodb-tables.py`

2. **Implement Missing APIs**
   - Start with Tracks API (required for hackathon setup)
   - Then Participants API (required for role management)
   - Then Projects API (required for submissions)

3. **Update Frontend Environment**
   - Add API base URL configuration
   - Install React Query
   - Create API client wrapper

### 8.2 Short Term (Weeks 2-3)

1. **Replace In-Memory State**
   - Implement API hooks with React Query
   - Remove Context provider
   - Test data persistence

2. **Authentication Integration**
   - Integrate AINative Auth in frontend
   - Update backend auth middleware
   - Implement protected routes

3. **Dashboard APIs**
   - Create aggregated dashboard endpoints
   - Optimize queries for statistics

### 8.3 Medium Term (Weeks 4-6)

1. **Real-Time Features**
   - WebSocket integration for leaderboard
   - Live submission notifications
   - Real-time participant updates

2. **File Upload Flow**
   - Integrate ZeroDB Files API
   - Implement file upload UI
   - Handle presigned URLs

3. **Testing**
   - E2E tests with Playwright
   - API integration tests
   - Component tests with React Testing Library

---

## 9. Migration Checklist

### Backend (Python API)

- [ ] Create 7 missing ZeroDB tables
- [ ] Implement Tracks CRUD endpoints
- [ ] Implement Participants CRUD endpoints
- [ ] Implement HackathonParticipants endpoints
- [ ] Implement Projects CRUD endpoints
- [ ] Implement Rubrics CRUD endpoints
- [ ] Implement Prizes CRUD endpoints
- [ ] Implement Invitations endpoints
- [ ] Add featured hackathons endpoints
- [ ] Add hackathon themes endpoints
- [ ] Create dashboard aggregation endpoints
- [ ] Update Hackathon schema (add logo_url, is_online fields)
- [ ] Write integration tests for all new endpoints
- [ ] Update API documentation

### Frontend (Next.js)

- [ ] Install @tanstack/react-query
- [ ] Create API client wrapper
- [ ] Add environment variables for API URLs
- [ ] Create API hooks for all resources
- [ ] Replace Context with React Query
- [ ] Update all components to use API hooks
- [ ] Integrate AINative Auth client
- [ ] Implement protected routes
- [ ] Update form submissions to call APIs
- [ ] Add loading states and error handling
- [ ] Test all CRUD operations
- [ ] Implement WebSocket for real-time features

### Documentation

- [ ] Update integration guide
- [ ] Document API endpoints
- [ ] Create frontend setup guide
- [ ] Update deployment documentation

---

## Appendix A: Frontend File Structure

```
/frontend
├── app/
│   ├── (marketing)/          # Public pages
│   │   ├── page.tsx          # Landing (uses featured_hackathons)
│   │   └── public-hackathons/ # Browse hackathons
│   └── (app)/                # Authenticated app
│       ├── hackathons/
│       │   ├── page.tsx      # Dashboard (needs API)
│       │   └── [hackathonId]/
│       │       ├── setup/    # Tracks, Rubrics (needs API)
│       │       ├── participants/ # Participants (needs API)
│       │       ├── teams/    # Teams (has API)
│       │       ├── projects/ # Projects (needs API)
│       │       ├── submissions/ # Submissions (has API)
│       │       ├── judging/  # Scoring (has API)
│       │       ├── leaderboard/ # Leaderboard (has API)
│       │       └── prizes/   # Prizes (needs API)
│       └── api-settings/
├── components/
│   ├── homepage/
│   │   ├── HackathonsForYou.tsx  # Uses featured_hackathons
│   │   └── TopHackathonThemes.tsx # Uses hackathon_themes
│   └── ui/
├── lib/
│   ├── types.ts              # Type definitions
│   ├── store.tsx             # React Context (to be replaced)
│   └── supabase.ts           # Supabase client (to be migrated)
└── supabase/
    └── migrations/           # SQL migrations (to migrate to ZeroDB)
```

---

**End of Analysis**
