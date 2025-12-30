# GitHub Issues Summary - Missing Backend APIs
**Date:** 2025-12-30
**Created by:** GAP Analysis Automation

---

## Overview

Created **10 GitHub issues** for missing backend APIs identified in the Frontend-Backend GAP Analysis. All issues follow project conventions with:
- Detailed acceptance criteria
- Story point estimates (Fibonacci scale)
- Dependencies documented
- Frontend impact assessment
- Test coverage requirements (80%+)

---

## Created Issues

### Critical Priority (Sprint 3)

**#62 - Implement Tracks API for Hackathon Categories**
- **Story Points:** 5
- **Priority:** CRITICAL
- **Endpoints:** 5 CRUD endpoints
- **Frontend:** `/hackathons/[id]/setup/` - Track creation
- **Link:** https://github.com/AINative-Studio/dothack-backend/issues/62

**#63 - Implement Participants API for User Profile Management**
- **Story Points:** 8 (High complexity)
- **Priority:** CRITICAL
- **Tables:** 2 (participants, hackathon_participants)
- **Endpoints:** 9 endpoints (profiles + role management)
- **Frontend:** `/hackathons/[id]/participants/` - Participant management
- **Link:** https://github.com/AINative-Studio/dothack-backend/issues/63

**#64 - Implement Projects API for Hackathon Project Management**
- **Story Points:** 5
- **Priority:** CRITICAL
- **Endpoints:** 8 endpoints (CRUD + status updates)
- **Frontend:** `/hackathons/[id]/projects/` - Project listing
- **Link:** https://github.com/AINative-Studio/dothack-backend/issues/64

**#65 - Implement Rubrics API for Judging Criteria Management**
- **Story Points:** 5
- **Priority:** CRITICAL
- **Endpoints:** 7 endpoints (CRUD + activation)
- **Frontend:** `/hackathons/[id]/setup/`, `/hackathons/[id]/judging/`
- **Special:** JSON criteria validation, weight validation
- **Link:** https://github.com/AINative-Studio/dothack-backend/issues/65

---

### High Priority (Sprint 4)

**#66 - Implement Prizes API for Hackathon Prize Management**
- **Story Points:** 3
- **Priority:** HIGH
- **Endpoints:** 7 endpoints (CRUD + filtering)
- **Frontend:** `/hackathons/[id]/prizes/`, `/hackathons/[id]/leaderboard/`
- **Special:** Track-specific prizes, rank management
- **Link:** https://github.com/AINative-Studio/dothack-backend/issues/66

**#68 - Migrate Featured Hackathons from Supabase to ZeroDB**
- **Story Points:** 5
- **Priority:** HIGH
- **Migration:** Supabase → ZeroDB
- **Endpoints:** 6 endpoints (2 public, 4 admin)
- **Frontend:** `/components/homepage/HackathonsForYou.tsx`
- **Special:** Public read access, display order management
- **Link:** https://github.com/AINative-Studio/dothack-backend/issues/68

**#69 - Migrate Hackathon Themes from Supabase to ZeroDB**
- **Story Points:** 3
- **Priority:** HIGH
- **Migration:** Supabase → ZeroDB
- **Endpoints:** 6 endpoints (2 public, 4 admin)
- **Frontend:** `/components/homepage/TopHackathonThemes.tsx`
- **Special:** Auto-calculated statistics, background job
- **Link:** https://github.com/AINative-Studio/dothack-backend/issues/69

**#71 - Update Hackathon Schema with Missing Fields**
- **Story Points:** 3
- **Priority:** HIGH
- **New Fields:** logo_url, is_online, participant_count
- **Endpoints:** 2 new (logo upload/delete)
- **Frontend:** Homepage components, setup pages
- **Special:** Image validation, auto-increment counters
- **Link:** https://github.com/AINative-Studio/dothack-backend/issues/71

---

### Medium Priority (Sprint 5)

**#67 - Implement Invitations API for Hackathon Participant Invites**
- **Story Points:** 8 (High complexity)
- **Priority:** MEDIUM
- **Endpoints:** 8 endpoints
- **Frontend:** NEW ROUTE - `/invitations/[token]/`
- **Special:** Email integration, token management, auto-provisioning
- **Link:** https://github.com/AINative-Studio/dothack-backend/issues/67

**#70 - Implement Dashboard Aggregation APIs for Role-Based Views**
- **Story Points:** 5
- **Priority:** MEDIUM
- **Endpoints:** 4 dashboard endpoints (organizer, builder, judge, overview)
- **Frontend:** All dashboard components
- **Special:** Aggregation queries, Redis caching, recent activity
- **Link:** https://github.com/AINative-Studio/dothack-backend/issues/70

---

## Summary Statistics

### By Priority
- **CRITICAL:** 4 issues (39 story points)
- **HIGH:** 4 issues (16 story points)
- **MEDIUM:** 2 issues (13 story points)

### By Complexity
- **Simple (3 pts):** 3 issues
- **Medium (5 pts):** 5 issues
- **Complex (8 pts):** 2 issues

### Total Effort
- **10 issues**
- **68 total story points**
- **Estimated:** 10-12 weeks (5-6 sprints)

---

## Implementation Sequence

### Sprint 3 (Weeks 5-6) - Core Foundation
**Focus:** Critical APIs for hackathon management

1. **Issue #63** - Participants API (8 pts) ⭐ START HERE
   - Required by most other APIs
   - Establishes user-hackathon relationship

2. **Issue #62** - Tracks API (5 pts)
   - Required for team formation
   - Simple CRUD implementation

3. **Issue #64** - Projects API (5 pts)
   - Team project management
   - Status tracking

**Sprint 3 Total:** 18 points

---

### Sprint 4 (Weeks 7-8) - Judging & Content
**Focus:** Judging system and public content

1. **Issue #65** - Rubrics API (5 pts)
   - Judging criteria management
   - JSON validation

2. **Issue #66** - Prizes API (3 pts)
   - Prize management
   - Track-specific awards

3. **Issue #71** - Hackathon Schema Updates (3 pts)
   - Add missing fields
   - Logo upload

4. **Issue #68** - Featured Hackathons Migration (5 pts)
   - Supabase → ZeroDB
   - Homepage content

5. **Issue #69** - Hackathon Themes Migration (3 pts)
   - Supabase → ZeroDB
   - Theme statistics

**Sprint 4 Total:** 19 points

---

### Sprint 5 (Weeks 9-10) - Enhanced Features
**Focus:** Invitations and dashboards

1. **Issue #67** - Invitations API (8 pts)
   - Email system
   - Token management

2. **Issue #70** - Dashboard APIs (5 pts)
   - Role-based views
   - Aggregation queries

**Sprint 5 Total:** 13 points

---

## Dependencies Graph

```
Participants API (#63)
├── Projects API (#64)
├── Invitations API (#67)
└── Dashboard APIs (#70)

Tracks API (#62)
├── Prizes API (#66) - track-specific prizes
└── Projects API (#64) - team track selection

Rubrics API (#65)
└── Dashboard APIs (#70) - judging progress

Hackathons API (existing)
├── All above APIs
└── Hackathon Schema Updates (#71)

Supabase Migrations
├── Featured Hackathons (#68)
└── Hackathon Themes (#69)
```

---

## Quick Start Commands

### View All Issues
```bash
gh issue list --repo AINative-Studio/dothack-backend \
  --label enhancement --limit 20
```

### Start Sprint 3
```bash
# Assign to yourself
gh issue edit 63 --add-assignee @me
gh issue edit 62 --add-assignee @me
gh issue edit 64 --add-assignee @me

# Move to In Progress
gh issue edit 63 --add-label "in-progress"
```

### Create Feature Branch
```bash
git checkout -b feature/63-participants-api
```

---

## Testing Requirements

All issues require:
- ✅ 80%+ test coverage
- ✅ Unit tests for business logic
- ✅ Integration tests for endpoints
- ✅ Authorization tests
- ✅ Validation tests

---

## Documentation Requirements

All issues require:
- ✅ OpenAPI/Swagger documentation
- ✅ Pydantic schema definitions
- ✅ Docstrings on public methods
- ✅ API usage examples

---

## Next Steps

1. **Review Issues** - Team reviews all 10 issues
2. **Refinement** - Update estimates if needed
3. **Sprint Planning** - Assign Sprint 3 issues
4. **Start Implementation** - Begin with Issue #63 (Participants API)
5. **Daily Updates** - Update issue progress daily

---

## Issue Templates Used

All issues follow this structure:
- 📋 Description & Reference
- 👤 User Stories
- ✅ Acceptance Criteria (ZeroDB, API, Schemas, Logic, Auth, Tests, Docs)
- 📊 Story Points
- 🔗 Dependencies
- 🎯 Priority
- 💻 Frontend Impact

---

**All Issues Created:** ✅
**Ready for Sprint Planning:** ✅
**Total Backlog:** 68 story points

---

**Related Documents:**
- [Frontend-Backend GAP Analysis](FRONTEND_BACKEND_GAP_ANALYSIS.md)
- [Project Backlog](planning/BACKLOG.md)
- [Authentication Architecture](AUTHENTICATION_ARCHITECTURE.md)
