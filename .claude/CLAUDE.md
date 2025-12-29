# DotHack Backend - Project Memory

## 🚨 RULE #1: NO AI ATTRIBUTION (ZERO TOLERANCE)

**FORBIDDEN in commits/PRs:** "Claude", "Anthropic", "claude.com", "AI-generated", emojis+attribution
**Enforcement:** `.git/hooks/commit-msg` blocks commits, see `.claude/git-rules.md`

**Correct format:**
```
Title
- Change 1
- Change 2
```

---

## Quick Reference

**Project:** DotHack Backend - Hackathon Management Platform
**Stack:** Python FastAPI + Go microservices + ZeroDB
**Deploy:** Railway (prod), Docker (dev)

### Structure
```
/Users/aideveloper/dothack-backend/
├── python-api/           # FastAPI backend
│   ├── api/             # API routes
│   ├── services/        # Business logic
│   ├── integrations/    # AINative Auth, ZeroDB
│   └── tests/           # >= 80% coverage required
├── go-services/         # Go microservices
│   └── leaderboard/    # Real-time WebSocket service
├── scripts/             # Automation scripts
├── docs/                # Documentation
│   ├── planning/       # BACKLOG.md, PRD
│   ├── deployment/     # Deployment guides
│   └── *.md            # Auth architecture, integration
└── .claude/            # Coding standards & rules
```

---

## Critical Rules

### 1. Git Commits
- File: `.claude/git-rules.md`
- Hook: `.git/hooks/commit-msg`
- Zero tolerance for AI attribution

### 2. File Placement
- File: `.claude/CRITICAL_FILE_PLACEMENT_RULES.md`
- Docs → `docs/{category}/`
- No root `.md` (except README.md)

### 3. Testing (MANDATORY)

**ZERO TOLERANCE - Execute before claiming pass:**
```bash
# Python API
cd python-api
python3 -m pytest tests/ -v --cov --cov-report=term-missing

# Must see: ✓ PASSED, ✓ 80%+ coverage
```

**Requirements:**
- 80%+ coverage with proof
- All endpoints tested (TDD/BDD)
- Output captured for PRs

### 4. Authentication (MANDATORY)

**🚨 CRITICAL: MUST USE AINative Studio Authentication**

**DO:**
- ✅ Use AINative Auth API (`https://api.ainative.studio/v1/auth/*`)
- ✅ Verify tokens via `/v1/auth/me`
- ✅ Store AINative `user_id` in `hackathon_participants`
- ✅ Implement role-based authorization in DotHack

**DON'T:**
- ❌ Build custom `/auth/register`, `/auth/login` endpoints
- ❌ Store passwords in DotHack database
- ❌ Generate JWT tokens in DotHack
- ❌ Implement OAuth flows in DotHack

**Documentation:** See `/docs/AUTHENTICATION_ARCHITECTURE.md`

### 5. Issue Tracking (MANDATORY)

**NO CODE WITHOUT AN ISSUE. NO PR WITHOUT A LINK.**

- File: `.claude/ISSUE_TRACKING_ENFORCEMENT.md`
- Every code change must have a GitHub issue
- Branch naming: `[type]/[issue-number]-[description]`
- Commit format: Reference issue in every commit (`Refs #123`)
- PR format: "Closes #123" required

### 6. Code Quality
- Type hints all functions
- Docstrings public methods
- Follow TDD/BDD workflow (Red → Green → Refactor)
- Fibonacci story pointing (0, 1, 2, 3, 5, 8)

---

## Architecture

### Technology Stack

**Backend:**
- Python 3.11 + FastAPI
- ZeroDB (unified database platform)
- AINative Authentication

**Real-Time:**
- Go + WebSockets (leaderboard service)
- ZeroDB Events API (event streaming)

**Search:**
- ZeroDB Vectors API (semantic search)
- BAAI/bge-small-en-v1.5 embeddings (384 dimensions)

**Deployment:**
- Railway (production)
- Docker (development)

### Data Model

**Users:** Managed by AINative (email, password, OAuth)
**Roles:** Managed by DotHack in `hackathon_participants` (ORGANIZER, BUILDER, JUDGE, MENTOR)
**Data:** All hackathon data stored in ZeroDB tables

### Core Tables (ZeroDB)

1. `hackathons` - Hackathon metadata
2. `tracks` - Hackathon tracks
3. `participants` - User profiles
4. `hackathon_participants` - User-hackathon-role mapping
5. `teams` - Team information
6. `team_members` - Team membership
7. `projects` - Project submissions
8. `submissions` - Submission artifacts
9. `rubrics` - Judging criteria
10. `scores` - Judge scores

---

## Common Tasks

### New API Endpoint
1. Create `python-api/api/routes/{feature}.py`
2. Create `python-api/services/{feature}_service.py`
3. Add authentication dependency (`Depends(get_current_user)`)
4. Add role checking (`check_organizer()`, `check_judge()`, etc.)
5. Create tests in `tests/test_{feature}.py`
6. Document in OpenAPI
7. Test, commit (NO AI ATTRIBUTION)

### Tests
```bash
cd python-api
pytest tests/ -v --cov --cov-report=term-missing
```

### ZeroDB Table Setup
```bash
# Create all tables
python scripts/setup-zerodb-tables.py --apply

# Verify tables
python scripts/verify-zerodb-tables.py
```

### Dev Start
```bash
# Python API
cd python-api
uvicorn main:app --reload --port 8000

# Go Leaderboard Service
cd go-services/leaderboard
go run main.go
```

---

## Environment Variables

**Required:**
```bash
# AINative Authentication
AINATIVE_API_URL=https://api.ainative.studio
AINATIVE_API_KEY=your_api_key  # For server-to-server calls

# ZeroDB
ZERODB_API_KEY=your_zerodb_api_key
ZERODB_PROJECT_ID=your_project_uuid
ZERODB_BASE_URL=https://api.ainative.studio

# Application
PORT=8000
LOG_LEVEL=INFO
```

---

## Development Workflow

### Agile Process
1. Check backlog: `/docs/planning/BACKLOG.md`
2. Pick story from current sprint
3. Create branch: `feature/[issue-number]-[description]`
4. Write tests first (TDD)
5. Implement feature
6. Run tests (>= 80% coverage)
7. Create PR linking issue
8. Review and merge

### Sprint Sequence (10-12 weeks)

**Sprint 1 (Weeks 1-2):** Epic 1-2 - Setup & Authentication (20 points)
**Sprint 2 (Weeks 3-4):** Epic 3 - Data Layer (14 points)
**Sprint 3 (Weeks 5-6):** Epic 4 - API Endpoints (18 points)
**Sprint 4 (Weeks 7-8):** Epic 5 - Semantic Search (12 points)
**Sprint 5 (Weeks 9-10):** Epic 6 - Real-Time Features (20 points)

---

## Key Documentation

- **PRD:** `/dothack-backendprd.md`
- **Backlog:** `/docs/planning/BACKLOG.md`
- **Auth Architecture:** `/docs/AUTHENTICATION_ARCHITECTURE.md`
- **Auth Integration:** `/docs/AINATIVE_AUTH_INTEGRATION.md`
- **Quick Start:** `/docs/README.md`
- **GitHub Issues:** https://github.com/AINative-Studio/dothack-backend/issues

---

## Deployment Checklist

- [ ] Tests passing (`pytest`)
- [ ] No AI attribution (`git log`)
- [ ] Authentication via AINative (NO standalone auth)
- [ ] >= 80% test coverage
- [ ] API docs updated
- [ ] Error handling complete
- [ ] Security reviewed
- [ ] GitHub issue linked

---

## MCP Servers (via Slash Commands)

**ZeroDB:** 44 slash commands available
- `/zerodb-help` - Show all commands
- `/zerodb-table-*` - Table operations
- `/zerodb-vector-*` - Vector/embedding operations
- `/zerodb-memory-*` - Agent memory operations
- `/zerodb-event-*` - Event streaming
- `/zerodb-rlhf-*` - RLHF feedback collection

**Google Analytics:** 6 slash commands
- `/ga-search-schema` - Find dimensions/metrics
- `/ga-get-data` - Retrieve analytics data
- `/ga-quick-report` - Generate overview report

See `.claude/commands/` for all available commands.

---

## 🚨 FINAL REMINDER

**BEFORE COMMIT:**
1. Contains "Claude"/"Anthropic"? → STOP! REMOVE!
2. Has attribution footer/emoji? → STOP! REMOVE!
3. Tests executed? → If NO, STOP! TEST FIRST!
4. Using AINative Auth? → If NO, STOP! FIX!
5. Issue linked in commit? → If NO, STOP! ADD REF!

**Hook blocks forbidden text.**

---

**Project:** DotHack Backend - Hackathon Management Platform
**Updated:** 2025-12-28
**Status:** Active Development
**Team:** AINative Studio
