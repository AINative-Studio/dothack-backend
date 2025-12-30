# Frontend GitHub Issues Summary - Integration & Migration
**Date:** 2025-12-30
**Repository:** dothack-frontend
**Created by:** GAP Analysis Automation

---

## Overview

Created **6 GitHub issues** for frontend integration work required to connect with the DotHack backend and migrate from demo mode to production-ready application.

**Key Changes:**
- Replace in-memory React Context with API calls
- Integrate real authentication (AINative Auth)
- Implement data persistence with React Query
- Add route protection and RBAC
- Real-time features via WebSocket

---

## Created Issues

### Critical Priority (Sprint 1-2)

**#1 - Create API Client for Backend Integration**
- **Story Points:** 5
- **Priority:** CRITICAL (Blocks all other work)
- **Scope:** HTTP client wrapper with error handling
- **Features:** Token injection, retry logic, type safety
- **Link:** https://github.com/AINative-Studio/dothack-frontend/issues/1

**#2 - Migrate from React Context to React Query**
- **Story Points:** 13 (Very high complexity)
- **Priority:** CRITICAL
- **Scope:** Complete state management refactor
- **Impact:** 30+ hooks to create, all components to update
- **Migration:** Gradual (hooks alongside Context, then remove)
- **Link:** https://github.com/AINative-Studio/dothack-frontend/issues/2

**#3 - Integrate AINative Authentication**
- **Story Points:** 8
- **Priority:** CRITICAL
- **Scope:** Login/Signup/Session management
- **Features:** JWT tokens, auto-login, user context
- **New Pages:** `/login`, `/signup`
- **Link:** https://github.com/AINative-Studio/dothack-frontend/issues/3

---

### High Priority (Sprint 3-4)

**#4 - Implement Protected Routes and RBAC**
- **Story Points:** 5
- **Priority:** HIGH
- **Scope:** Next.js middleware for route protection
- **Features:** Auth checks, role-based access, navigation guards
- **Security:** Client-side + server-side validation
- **Link:** https://github.com/AINative-Studio/dothack-frontend/issues/4

---

### Medium Priority (Sprint 5)

**#5 - Create Invitation Acceptance Page**
- **Story Points:** 3
- **Priority:** MEDIUM
- **Scope:** New route for `/invitations/[token]`
- **Features:** Accept/decline invitations, signup integration
- **Link:** https://github.com/AINative-Studio/dothack-frontend/issues/5

**#6 - Implement WebSocket for Real-Time Leaderboard**
- **Story Points:** 5
- **Priority:** MEDIUM (Enhancement)
- **Scope:** WebSocket client for live updates
- **Features:** Auto-reconnect, animations, connection status
- **Link:** https://github.com/AINative-Studio/dothack-frontend/issues/6

---

## Summary Statistics

### By Priority
- **CRITICAL:** 3 issues (26 story points) - Must complete first
- **HIGH:** 1 issue (5 story points)
- **MEDIUM:** 2 issues (8 story points)

### By Category
- **Infrastructure:** 2 issues (#1 API Client, #6 WebSocket)
- **State Management:** 1 issue (#2 React Query)
- **Authentication:** 2 issues (#3 Auth, #4 Routes)
- **Features:** 1 issue (#5 Invitations)

### Total Effort
- **6 issues**
- **39 total story points**
- **Estimated:** 8-10 weeks (4-5 sprints)

---

## Implementation Sequence

### Sprint 1 (Weeks 1-2) - Foundation
**Focus:** API infrastructure and authentication

1. **Issue #1** - API Client (5 pts) ⭐ START HERE
   - Required by all other issues
   - Core infrastructure piece

2. **Issue #3** - Authentication (8 pts)
   - Login/Signup pages
   - Auth context and token management

**Sprint 1 Total:** 13 points

---

### Sprint 2 (Weeks 3-4) - Data Layer
**Focus:** Migrate to server state management

1. **Issue #2** - React Query Migration (13 pts)
   - MASSIVE refactor
   - Create 30+ hooks
   - Update all components
   - Remove React Context

**Sprint 2 Total:** 13 points

---

### Sprint 3 (Weeks 5-6) - Security
**Focus:** Route protection and access control

1. **Issue #4** - Protected Routes (5 pts)
   - Next.js middleware
   - Role-based access
   - Navigation guards

**Sprint 3 Total:** 5 points

---

### Sprint 4-5 (Weeks 7-10) - Enhancements
**Focus:** Additional features

1. **Issue #5** - Invitations Page (3 pts)
   - New route and page
   - Email workflow

2. **Issue #6** - WebSocket Integration (5 pts)
   - Real-time leaderboard
   - Connection management

**Sprint 4-5 Total:** 8 points

---

## Dependencies Graph

```
API Client (#1) ⭐ NO DEPENDENCIES
├── Authentication (#3)
│   ├── Protected Routes (#4)
│   └── React Query (#2)
│       ├── Invitations Page (#5)
│       └── WebSocket (#6)
```

**Critical Path:** #1 → #3 → #2 → #4

---

## Migration Strategy

### Phase 1: Infrastructure (Weeks 1-2)
1. Create API client
2. Set up authentication
3. Test login/signup flow
4. Verify token management

### Phase 2: Data Migration (Weeks 3-4)
1. Install React Query
2. Create hooks gradually
3. Migrate components one-by-one
4. Keep Context until all migrations complete
5. Test thoroughly before removing Context

### Phase 3: Security (Weeks 5-6)
1. Add Next.js middleware
2. Implement route protection
3. Test all access scenarios
4. Update navigation based on roles

### Phase 4: Enhancements (Weeks 7-10)
1. Build invitations page
2. Integrate WebSocket
3. Polish UI/UX
4. Final testing

---

## Breaking Changes

### Current vs New Architecture

**Before:**
```typescript
// In-memory state
const hackathons = useStore(state => state.hackathons)
const addHackathon = useStore(state => state.addHackathon)

// No auth
const currentRole = 'ORGANIZER' // hardcoded

// Public routes
// No route protection
```

**After:**
```typescript
// Server state with React Query
const { data: hackathons, isLoading } = useHackathons()
const createHackathon = useCreateHackathon()

// Real auth
const { user, isAuthenticated } = useAuth()

// Protected routes
// Middleware enforces auth + RBAC
```

### Data Persistence
- **Before:** Lost on page refresh
- **After:** Persisted in backend database

### Authentication
- **Before:** Demo mode, no login
- **After:** Real auth with AINative

---

## Environment Variables Required

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_VERSION=v1

# Authentication
NEXT_PUBLIC_AINATIVE_AUTH_URL=https://api.ainative.studio/v1/auth
NEXT_PUBLIC_AINATIVE_APP_URL=https://app.dothack.com

# WebSocket (Optional)
NEXT_PUBLIC_WS_URL=ws://localhost:8080
NEXT_PUBLIC_WS_URL_PRODUCTION=wss://leaderboard.dothack.com

# Feature Flags
NEXT_PUBLIC_ENABLE_ANALYTICS=true
NEXT_PUBLIC_ENABLE_RECOMMENDATIONS=true
```

---

## Testing Requirements

All issues require:
- ✅ Unit tests for utilities/hooks
- ✅ Integration tests for API calls
- ✅ Component tests with React Testing Library
- ✅ E2E tests for critical flows (login, create hackathon, etc.)

### Key Test Scenarios
1. **Auth Flow:** Signup → Login → Auto-login → Logout
2. **Data Persistence:** Create hackathon → Refresh → Still exists
3. **Protected Routes:** Access restricted page → Redirect to login → Login → Access granted
4. **Real-time:** Submit score → Leaderboard updates instantly

---

## Package Dependencies to Install

```json
{
  "dependencies": {
    "@tanstack/react-query": "^5.17.0",
    "@tanstack/react-query-devtools": "^5.17.0"
  }
}
```

**Already installed:**
- Next.js 13+ ✅
- TypeScript ✅
- React 18+ ✅

---

## Files to Create (Summary)

### Infrastructure
- `lib/api-client.ts`
- `lib/env.ts`
- `lib/query-client.ts`
- `lib/query-keys.ts`
- `lib/errors/api-errors.ts`

### Authentication
- `lib/auth/auth-service.ts`
- `lib/auth/auth-context.tsx`
- `lib/auth/route-protection.ts`
- `lib/auth/check-role.ts`
- `app/(auth)/login/page.tsx`
- `app/(auth)/signup/page.tsx`
- `components/auth/LoginForm.tsx`
- `components/auth/SignupForm.tsx`
- `components/UserMenu.tsx`
- `middleware.ts`

### Hooks (30+)
- `hooks/use-hackathons.ts`
- `hooks/use-create-hackathon.ts`
- `hooks/use-teams.ts`
- `hooks/use-projects.ts`
- ... (and 25+ more)

### WebSocket
- `lib/websocket/websocket-client.ts`
- `hooks/use-leaderboard-realtime.ts`
- `hooks/use-websocket.ts`

### Pages
- `app/invitations/[token]/page.tsx`
- `app/unauthorized/page.tsx`

---

## Files to Update

### Layouts
- `app/layout.tsx` - Add QueryClientProvider + AuthProvider
- `app/(app)/layout.tsx` - Add user menu, conditional navigation

### Components
- **All** components using `useStore()` → Update to use React Query hooks
- **All** forms → Update to use mutation hooks

---

## Files to Delete (After Migration)

- `lib/store.tsx` - React Context provider (replaced by React Query)
- `lib/supabase.ts` - Supabase client (replaced by backend API)

---

## Quick Start Commands

### View All Issues
```bash
gh issue list --repo AINative-Studio/dothack-frontend --limit 10
```

### Start Sprint 1
```bash
# Clone frontend repo
git clone git@github.com:AINative-Studio/dothack-frontend.git
cd dothack-frontend

# Assign issues
gh issue edit 1 --add-assignee @me
gh issue edit 3 --add-assignee @me

# Create feature branch
git checkout -b feature/1-api-client
```

### Install Dependencies
```bash
npm install @tanstack/react-query @tanstack/react-query-devtools
```

---

## Success Criteria

### Sprint 1 Complete When:
- ✅ API client implemented and tested
- ✅ Login/Signup pages functional
- ✅ Users can authenticate and get tokens
- ✅ API calls include auth tokens

### Sprint 2 Complete When:
- ✅ React Query installed and configured
- ✅ All 30+ hooks created
- ✅ All components migrated
- ✅ React Context removed
- ✅ Data persists between sessions

### Sprint 3 Complete When:
- ✅ Middleware protects routes
- ✅ Unauthorized users redirected to login
- ✅ Role-based access working
- ✅ Navigation shows only permitted items

### Sprint 4-5 Complete When:
- ✅ Invitations page functional
- ✅ WebSocket connected and updating
- ✅ All tests passing
- ✅ Production ready

---

## Risk Mitigation

### High-Risk Items
1. **React Query Migration (Issue #2)** - MASSIVE refactor
   - **Mitigation:** Gradual migration, keep Context until complete

2. **Authentication Security** - Critical vulnerability if done wrong
   - **Mitigation:** Use httpOnly cookies, validate all tokens server-side

3. **Breaking Changes** - Entire app architecture changes
   - **Mitigation:** Thorough testing, staged rollout

### Rollback Plan
- Keep React Context code until React Query fully tested
- Feature flags for new vs old auth
- Database backups before production deploy

---

## Communication Plan

### Stakeholder Updates
- Weekly progress reports
- Demo after each sprint
- Highlight blockers immediately

### Documentation
- Update README with new setup instructions
- Document environment variables
- Create troubleshooting guide

---

## Next Steps

1. **Team Review** - Review all 6 issues
2. **Sprint Planning** - Assign Sprint 1 issues
3. **Environment Setup** - Configure `.env.local`
4. **Start Development** - Begin with Issue #1 (API Client)
5. **Daily Standups** - Track progress

---

**All Issues Created:** ✅
**Ready for Development:** ✅
**Total Backlog:** 39 story points

---

**Related Documents:**
- [Frontend-Backend GAP Analysis](https://github.com/AINative-Studio/dothack-backend/blob/main/docs/FRONTEND_BACKEND_GAP_ANALYSIS.md)
- [Backend Issues Summary](https://github.com/AINative-Studio/dothack-backend/blob/main/docs/GITHUB_ISSUES_SUMMARY.md)
- [Authentication Architecture](https://github.com/AINative-Studio/dothack-backend/blob/main/docs/AUTHENTICATION_ARCHITECTURE.md)
