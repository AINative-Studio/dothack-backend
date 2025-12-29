# DotHack Backend - Agile Backlog

**Version:** 1.0
**Last Updated:** 2025-12-28
**Status:** Ready for Development

---

## Backlog Overview

This backlog covers the complete implementation of DotHack Backend based on the PRD. Stories are organized by Epic and prioritized for sequential delivery.

### Total Effort

- **Epics:** 6
- **Total Stories:** 42
- **Total Points:** 84 points
- **Estimated Duration:** 10-12 weeks (2-person team)

---

## Epic 1: Project Setup & Infrastructure (8 points)

**Goal:** Set up repository structure, development environment, and CI/CD pipeline.

**Acceptance Criteria:**
- [ ] Repository initialized with proper structure
- [ ] Development environment documented and working
- [ ] CI/CD pipeline passing
- [ ] All team members can run project locally

### Stories

#### Story 1.1: Repository initialization and structure
**Type:** CHORE
**Points:** 1
**Priority:** CRITICAL

**Description:**
Initialize DotHack Backend repository with proper folder structure following AINative coding standards.

**Tasks:**
- Create `python-api/` directory with FastAPI structure
- Create `go-services/` directory with Go module structure
- Create `scripts/` directory for automation
- Create `docs/` directory with proper subdirectories
- Add `.gitignore` for Python and Go
- Add `README.md` with quick start guide

**Acceptance Criteria:**
- [ ] Folder structure matches PRD Section 4
- [ ] README.md includes setup instructions
- [ ] .gitignore covers Python, Go, IDE files
- [ ] All required directories present

**Files Affected:**
- Repository root structure
- `README.md`
- `.gitignore`
- `docs/planning/BACKLOG.md`

---

#### Story 1.2: Python FastAPI skeleton setup
**Type:** CHORE
**Points:** 2
**Priority:** HIGH

**Description:**
Create FastAPI application skeleton with proper configuration, logging, and error handling.

**Tasks:**
- Create `python-api/main.py` with FastAPI app
- Create `python-api/config.py` for configuration management
- Create `python-api/api/` directory structure
- Add `requirements.txt` with core dependencies
- Configure logging with structured output
- Add health check endpoint `/health`

**Acceptance Criteria:**
- [ ] FastAPI app starts on port 8000
- [ ] `/health` endpoint returns 200 OK
- [ ] Logging configured with INFO level
- [ ] Configuration loaded from environment variables
- [ ] `requirements.txt` includes: fastapi, uvicorn, pydantic, httpx

**Testing:**
```bash
cd python-api
uvicorn main:app --reload --port 8000
curl http://localhost:8000/health
# Should return: {"status": "healthy"}
```

**Dependencies:** None

---

#### Story 1.3: ZeroDB integration setup
**Type:** FEATURE
**Points:** 2
**Priority:** CRITICAL

**Description:**
Create ZeroDB client wrapper for Python with authentication and base HTTP client.

**Tasks:**
- Create `python-api/integrations/zerodb/client.py`
- Implement HTTP client with X-API-Key authentication
- Create wrapper methods for Tables, Vectors, Events APIs
- Add error handling and retries
- Create configuration for ZeroDB connection

**Acceptance Criteria:**
- [ ] ZeroDB client successfully connects with API key
- [ ] Error handling for network failures
- [ ] Retry logic with exponential backoff
- [ ] Environment variables: `ZERODB_API_KEY`, `ZERODB_PROJECT_ID`, `ZERODB_BASE_URL`
- [ ] Connection test passes

**Testing:**
```python
client = ZeroDBClient()
project = await client.get_project_info()
assert project["id"] == os.getenv("ZERODB_PROJECT_ID")
```

**Dependencies:** Story 1.2

---

#### Story 1.4: AINative Authentication integration
**Type:** FEATURE
**Points:** 2
**Priority:** CRITICAL

**Description:**
Integrate with AINative Studio authentication system for user authentication.

**Tasks:**
- Create `python-api/integrations/ainative/auth_client.py`
- Implement token verification via `/v1/auth/me`
- Create `get_current_user()` dependency
- Add API key authentication support
- Create authentication middleware

**Acceptance Criteria:**
- [ ] Token verification works with AINative API
- [ ] `get_current_user()` dependency returns user info
- [ ] Both JWT and API key auth supported
- [ ] Invalid tokens return 401 Unauthorized
- [ ] Authentication documented in `/docs/AUTHENTICATION_ARCHITECTURE.md`

**Testing:**
```python
# Test with valid token
headers = {"Authorization": "Bearer valid_token"}
response = await client.get("/test", headers=headers)
assert response.status_code == 200

# Test with invalid token
headers = {"Authorization": "Bearer invalid_token"}
response = await client.get("/test", headers=headers)
assert response.status_code == 401
```

**Dependencies:** Story 1.2

---

#### Story 1.5: CI/CD pipeline setup
**Type:** DEVOPS
**Points:** 1
**Priority:** HIGH

**Description:**
Set up GitHub Actions CI/CD pipeline with linting, testing, and deployment.

**Tasks:**
- Create `.github/workflows/ci.yml`
- Add linting (black, ruff, mypy for Python)
- Add test execution with coverage
- Add deployment to Railway (staging)
- Configure environment secrets

**Acceptance Criteria:**
- [ ] CI runs on every push to `main` and PRs
- [ ] Linting passes (black, ruff, mypy)
- [ ] Tests execute with pytest
- [ ] Coverage >= 80%
- [ ] Auto-deploy to staging on merge to `main`

**Dependencies:** Story 1.2, 1.4

---

## Epic 2: AINative Authentication Integration (12 points)

**Goal:** Complete integration with AINative Studio authentication system.

**Acceptance Criteria:**
- [ ] All endpoints protected with AINative auth
- [ ] Role-based authorization working
- [ ] OAuth flows tested
- [ ] Documentation complete

### Stories

#### Story 2.1: Authentication dependency implementation
**Type:** FEATURE
**Points:** 2
**Priority:** CRITICAL

**Description:**
Create reusable authentication dependencies for FastAPI endpoints.

**Tasks:**
- Create `python-api/api/dependencies.py`
- Implement `get_current_user()` dependency
- Implement `get_current_user_optional()` dependency
- Add caching for user info (5-minute TTL)
- Add proper error messages for auth failures

**Acceptance Criteria:**
- [ ] `get_current_user()` verifies token via AINative
- [ ] User info cached to reduce API calls
- [ ] Optional auth returns None for unauthenticated
- [ ] Clear error messages for invalid/expired tokens
- [ ] 5-minute cache TTL implemented

**Testing:**
```python
@router.get("/protected")
async def protected_route(current_user = Depends(get_current_user)):
    return {"user_id": current_user["id"]}

# Test passes with valid token
# Test fails with invalid token (401)
# Test cache (2nd call within 5 min doesn't hit AINative)
```

**Dependencies:** Story 1.4

---

#### Story 2.2: Role-based authorization service
**Type:** FEATURE
**Points:** 3
**Priority:** HIGH

**Description:**
Implement role checking service for hackathon-specific authorization.

**Tasks:**
- Create `python-api/services/authorization.py`
- Implement `check_role()` function
- Implement `check_organizer()` helper
- Implement `check_judge()` helper
- Implement `check_builder()` helper
- Query `hackathon_participants` table for roles

**Acceptance Criteria:**
- [ ] `check_role()` queries ZeroDB for participant role
- [ ] Returns 403 Forbidden if role not found
- [ ] Helper functions for common role checks
- [ ] Logs authorization failures
- [ ] Performance: < 100ms for role check

**Testing:**
```python
# User is ORGANIZER for hackathon_123
await check_organizer("hackathon_123", "user_456", zerodb_client)
# Passes

# User is BUILDER (not ORGANIZER)
await check_organizer("hackathon_123", "user_789", zerodb_client)
# Raises HTTPException(403)
```

**Dependencies:** Story 1.3, Story 2.1

---

#### Story 2.3: OAuth callback handlers
**Type:** FEATURE
**Points:** 2
**Priority:** MEDIUM

**Description:**
Create endpoint handlers for GitHub and LinkedIn OAuth callbacks.

**Tasks:**
- Create documentation for OAuth flow
- Document frontend integration with AINative OAuth
- Create example redirect handlers
- Add OAuth documentation to `/docs/AUTHENTICATION_ARCHITECTURE.md`

**Acceptance Criteria:**
- [ ] Documentation shows OAuth flow diagram
- [ ] Frontend integration guide complete
- [ ] Example code for OAuth redirects
- [ ] GitHub OAuth flow documented
- [ ] LinkedIn OAuth flow documented

**Testing:**
- [ ] Manual test: Login with GitHub
- [ ] Manual test: Login with LinkedIn
- [ ] Verify user created in AINative
- [ ] Verify token works for API calls

**Dependencies:** Story 2.1

---

#### Story 2.4: Authentication testing suite
**Type:** TEST
**Points:** 2
**Priority:** HIGH

**Description:**
Create comprehensive test suite for authentication and authorization.

**Tasks:**
- Create `python-api/tests/test_auth.py`
- Test token verification
- Test invalid token handling
- Test role-based authorization
- Test API key authentication
- Test caching behavior

**Acceptance Criteria:**
- [ ] >= 80% coverage for auth code
- [ ] All auth scenarios tested
- [ ] Mock AINative API responses
- [ ] Test both success and failure cases
- [ ] Performance tests for caching

**Test Cases:**
```python
describe("Authentication")
  it("verifies valid JWT token")
  it("rejects invalid JWT token")
  it("verifies valid API key")
  it("rejects invalid API key")
  it("caches user info for 5 minutes")

describe("Authorization")
  it("allows ORGANIZER to update hackathon")
  it("denies BUILDER from updating hackathon")
  it("allows JUDGE to score submission")
  it("denies BUILDER from scoring submission")
```

**Dependencies:** Story 2.1, Story 2.2

---

#### Story 2.5: Authentication documentation
**Type:** DOCS
**Points:** 1
**Priority:** MEDIUM

**Description:**
Create comprehensive documentation for authentication integration.

**Tasks:**
- Update `/docs/AUTHENTICATION_ARCHITECTURE.md`
- Create API reference for auth endpoints
- Document environment variables
- Create troubleshooting guide
- Add code examples

**Acceptance Criteria:**
- [ ] Architecture diagram included
- [ ] All auth endpoints documented
- [ ] Environment variables documented
- [ ] Code examples for common patterns
- [ ] Troubleshooting section complete

**Dependencies:** Story 2.1, Story 2.2, Story 2.3

---

#### Story 2.6: Authentication error handling
**Type:** FEATURE
**Points:** 2
**Priority:** MEDIUM

**Description:**
Implement proper error handling and logging for authentication failures.

**Tasks:**
- Create custom exception classes
- Add structured logging for auth events
- Implement retry logic for AINative API
- Add rate limiting for auth endpoints
- Create error response format

**Acceptance Criteria:**
- [ ] Custom exceptions for auth errors
- [ ] All auth events logged with context
- [ ] 3 retries with exponential backoff
- [ ] Rate limiting: 100 requests/minute per IP
- [ ] Consistent error response format

**Error Responses:**
```json
{
  "detail": "Invalid or expired token",
  "error_code": "AUTH_INVALID_TOKEN",
  "timestamp": "2025-12-28T10:00:00Z"
}
```

**Dependencies:** Story 2.1

---

## Epic 3: ZeroDB Tables & Core Data Layer (14 points)

**Goal:** Create and initialize all ZeroDB tables for hackathon data.

### Stories

#### Story 3.1: ZeroDB table creation script
**Type:** CHORE
**Points:** 2
**Priority:** CRITICAL

**Description:**
Create Python script to initialize all 10 core ZeroDB tables with proper schemas.

**Tasks:**
- Create `scripts/setup-zerodb-tables.py`
- Implement table creation for all 10 tables (hackathons, tracks, participants, etc.)
- Add idempotent table creation (skip if exists)
- Add dry-run mode
- Add colored output for readability

**Tables to Create:**
1. hackathons
2. tracks
3. participants
4. hackathon_participants
5. teams
6. team_members
7. projects
8. submissions
9. rubrics
10. scores

**Acceptance Criteria:**
- [ ] All 10 tables created successfully
- [ ] Script is idempotent (can run multiple times)
- [ ] Dry-run mode shows what would be created
- [ ] Color-coded output (success=green, warning=yellow)
- [ ] Documentation in `/docs/deployment/ZERODB_SETUP.md`

**Testing:**
```bash
# Dry run
python scripts/setup-zerodb-tables.py --dry-run

# Actual creation
python scripts/setup-zerodb-tables.py --apply

# Verify
python scripts/verify-zerodb-tables.py
```

**Dependencies:** Story 1.3

---

#### Story 3.2: Hackathon CRUD service
**Type:** FEATURE
**Points:** 3
**Priority:** HIGH

**Description:**
Implement service layer for hackathon creation, retrieval, update, and deletion.

**Tasks:**
- Create `python-api/services/hackathon_service.py`
- Implement `create_hackathon()`
- Implement `get_hackathon()`
- Implement `list_hackathons()`
- Implement `update_hackathon()`
- Implement `delete_hackathon()`
- Auto-add creator as ORGANIZER in `hackathon_participants`

**Acceptance Criteria:**
- [ ] All CRUD operations working
- [ ] Creator automatically assigned as ORGANIZER
- [ ] Hackathon status validation (DRAFT, LIVE, CLOSED)
- [ ] Pagination for list endpoint
- [ ] Soft delete (mark as deleted, don't remove)

**Testing:**
```python
describe("Hackathon Service")
  it("creates hackathon with valid data")
  it("adds creator as ORGANIZER")
  it("validates hackathon status")
  it("lists hackathons with pagination")
  it("updates hackathon (ORGANIZER only)")
  it("soft deletes hackathon")
```

**Dependencies:** Story 1.3, Story 2.2, Story 3.1

---

#### Story 3.3: Team management service
**Type:** FEATURE
**Points:** 3
**Priority:** HIGH

**Description:**
Implement service layer for team creation and member management.

**Tasks:**
- Create `python-api/services/team_service.py`
- Implement `create_team()`
- Implement `add_team_member()`
- Implement `remove_team_member()`
- Implement `get_team()`
- Validate max team size
- Assign team lead automatically

**Acceptance Criteria:**
- [ ] Teams created within hackathons
- [ ] Creator assigned as team LEAD
- [ ] Max team size enforced (default: 5)
- [ ] Members can leave teams
- [ ] Team status tracked (FORMING, ACTIVE)

**Testing:**
```python
describe("Team Service")
  it("creates team for hackathon")
  it("assigns creator as team LEAD")
  it("adds members to team")
  it("enforces max team size")
  it("removes members from team")
  it("prevents duplicate members")
```

**Dependencies:** Story 3.1, Story 3.2

---

#### Story 3.4: Project submission service
**Type:** FEATURE
**Points:** 3
**Priority:** HIGH

**Description:**
Implement service layer for project submissions with validation.

**Tasks:**
- Create `python-api/services/submission_service.py`
- Implement `submit_project()`
- Implement `get_submission()`
- Implement `update_submission()`
- Validate team membership
- Validate submission deadline
- Update project status to SUBMITTED

**Acceptance Criteria:**
- [ ] Only team members can submit
- [ ] Submission deadline enforced
- [ ] Project status updated to SUBMITTED
- [ ] Submission text stored in ZeroDB
- [ ] Artifact links validated (URLs)

**Testing:**
```python
describe("Submission Service")
  it("allows team member to submit")
  it("denies non-team member submission")
  it("enforces submission deadline")
  it("validates artifact URLs")
  it("updates project status")
  it("prevents duplicate submissions")
```

**Dependencies:** Story 3.1, Story 3.3

---

#### Story 3.5: Judging and scoring service
**Type:** FEATURE
**Points:** 3
**Priority:** HIGH

**Description:**
Implement service layer for submission scoring and feedback.

**Tasks:**
- Create `python-api/services/judging_service.py`
- Implement `score_submission()`
- Implement `get_scores()`
- Implement `calculate_leaderboard()`
- Validate judge assignment
- Validate score ranges
- Calculate total scores

**Acceptance Criteria:**
- [ ] Only assigned JUDGE can score
- [ ] Score validation per rubric
- [ ] Total score calculated automatically
- [ ] Leaderboard generated from scores
- [ ] Scores immutable once submitted

**Testing:**
```python
describe("Judging Service")
  it("allows assigned JUDGE to score")
  it("denies non-judge from scoring")
  it("validates score ranges")
  it("calculates total score")
  it("generates leaderboard")
  it("prevents score modification after submit")
```

**Dependencies:** Story 3.1, Story 3.4

---

## Epic 4: API Endpoints Implementation (18 points)

**Goal:** Implement all REST API endpoints for hackathon operations.

### Stories

#### Story 4.1: Hackathon endpoints
**Type:** FEATURE
**Points:** 2
**Priority:** HIGH

**Description:**
Create REST API endpoints for hackathon management.

**Endpoints:**
- `POST /api/v1/hackathons` - Create hackathon
- `GET /api/v1/hackathons` - List hackathons
- `GET /api/v1/hackathons/{id}` - Get hackathon details
- `PATCH /api/v1/hackathons/{id}` - Update hackathon (ORGANIZER)
- `DELETE /api/v1/hackathons/{id}` - Delete hackathon (ORGANIZER)

**Acceptance Criteria:**
- [ ] All endpoints implement proper authentication
- [ ] ORGANIZER role required for updates/deletes
- [ ] Request/response validation with Pydantic
- [ ] OpenAPI documentation auto-generated
- [ ] All endpoints tested

**Dependencies:** Story 3.2

---

#### Story 4.2: Team endpoints
**Type:** FEATURE
**Points:** 2
**Priority:** HIGH

**Description:**
Create REST API endpoints for team management.

**Endpoints:**
- `POST /api/v1/hackathons/{id}/teams` - Create team
- `POST /api/v1/teams/{id}/members` - Add member
- `DELETE /api/v1/teams/{id}/members/{user_id}` - Remove member
- `GET /api/v1/teams/{id}` - Get team details
- `GET /api/v1/hackathons/{id}/teams` - List teams

**Acceptance Criteria:**
- [ ] Team members can add/remove members
- [ ] Max team size enforced
- [ ] Only participants can join teams
- [ ] Team lead has special permissions
- [ ] All endpoints tested

**Dependencies:** Story 3.3

---

#### Story 4.3: Submission endpoints
**Type:** FEATURE
**Points:** 2
**Priority:** HIGH

**Description:**
Create REST API endpoints for project submissions.

**Endpoints:**
- `POST /api/v1/projects/{id}/submit` - Submit project
- `GET /api/v1/submissions/{id}` - Get submission
- `GET /api/v1/hackathons/{id}/submissions` - List submissions
- `PATCH /api/v1/submissions/{id}` - Update submission (before deadline)

**Acceptance Criteria:**
- [ ] Only team members can submit
- [ ] Deadline validation enforced
- [ ] Artifact links validated
- [ ] Submission status tracked
- [ ] All endpoints tested

**Dependencies:** Story 3.4

---

#### Story 4.4: Judging endpoints
**Type:** FEATURE
**Points:** 2
**Priority:** HIGH

**Description:**
Create REST API endpoints for scoring and judging.

**Endpoints:**
- `POST /api/v1/submissions/{id}/score` - Score submission (JUDGE)
- `GET /api/v1/submissions/{id}/scores` - Get all scores
- `GET /api/v1/hackathons/{id}/leaderboard` - Get leaderboard

**Acceptance Criteria:**
- [ ] Only JUDGE role can score
- [ ] Rubric validation enforced
- [ ] Leaderboard sorted by total score
- [ ] Scores cannot be modified once submitted
- [ ] All endpoints tested

**Dependencies:** Story 3.5

---

#### Story 4.5: Participant management endpoints
**Type:** FEATURE
**Points:** 2
**Priority:** MEDIUM

**Description:**
Create REST API endpoints for participant management.

**Endpoints:**
- `POST /api/v1/hackathons/{id}/join` - Join hackathon (BUILDER)
- `POST /api/v1/hackathons/{id}/invite-judges` - Invite judges (ORGANIZER)
- `GET /api/v1/hackathons/{id}/participants` - List participants
- `DELETE /api/v1/hackathons/{id}/leave` - Leave hackathon

**Acceptance Criteria:**
- [ ] Authenticated users can join
- [ ] Role assigned on join (BUILDER default)
- [ ] ORGANIZER can invite JUDGE
- [ ] Participants can leave before submission
- [ ] All endpoints tested

**Dependencies:** Story 3.1

---

#### Story 4.6: Search endpoint
**Type:** FEATURE
**Points:** 3
**Priority:** MEDIUM

**Description:**
Create search endpoint for finding hackathons, teams, and submissions.

**Endpoints:**
- `POST /api/v1/search` - Universal search
- `POST /api/v1/hackathons/{id}/search` - Search within hackathon

**Acceptance Criteria:**
- [ ] Search by keywords
- [ ] Filter by status, track, etc.
- [ ] Pagination support
- [ ] Results sorted by relevance
- [ ] < 200ms response time

**Dependencies:** Story 4.1, Story 4.2, Story 4.3

---

#### Story 4.7: Analytics endpoints
**Type:** FEATURE
**Points:** 2
**Priority:** LOW

**Description:**
Create analytics endpoints for hackathon statistics.

**Endpoints:**
- `GET /api/v1/hackathons/{id}/stats` - Get hackathon statistics
- `GET /api/v1/hackathons/{id}/export` - Export hackathon data

**Acceptance Criteria:**
- [ ] Total participants, teams, submissions
- [ ] Average scores per track
- [ ] Export to JSON/CSV
- [ ] ORGANIZER access only
- [ ] All endpoints tested

**Dependencies:** Story 4.1, Story 4.3, Story 4.4

---

#### Story 4.8: API documentation
**Type:** DOCS
**Points:** 1
**Priority:** MEDIUM

**Description:**
Create comprehensive API documentation with examples.

**Tasks:**
- Configure FastAPI OpenAPI generation
- Add detailed descriptions to all endpoints
- Add request/response examples
- Create Postman collection
- Deploy to `/docs` endpoint

**Acceptance Criteria:**
- [ ] OpenAPI 3.0 spec generated
- [ ] All endpoints documented
- [ ] Request/response schemas included
- [ ] Authentication documented
- [ ] Postman collection available

**Dependencies:** Story 4.1-4.7

---

#### Story 4.9: API integration tests
**Type:** TEST
**Points:** 2
**Priority:** HIGH

**Description:**
Create comprehensive integration test suite for all API endpoints.

**Tasks:**
- Create `python-api/tests/integration/test_api.py`
- Test all endpoint flows
- Test error cases
- Test authentication/authorization
- Achieve >= 80% coverage

**Acceptance Criteria:**
- [ ] All happy paths tested
- [ ] All error cases tested
- [ ] Auth/authz tested
- [ ] >= 80% coverage
- [ ] Tests run in CI

**Dependencies:** Story 4.1-4.7

---

## Epic 5: Semantic Search & Embeddings (12 points)

**Goal:** Implement AI-powered semantic search using ZeroDB vector embeddings.

### Stories

#### Story 5.1: Embedding generation service
**Type:** FEATURE
**Points:** 3
**Priority:** HIGH

**Description:**
Create service to generate embeddings for submission text using ZeroDB Embeddings API.

**Tasks:**
- Create `python-api/services/embedding_service.py`
- Implement embedding generation for submissions
- Use BAAI/bge-small-en-v1.5 model (384 dimensions)
- Store embeddings in ZeroDB vectors
- Create namespace: `hackathons/{hackathon_id}/submissions`

**Acceptance Criteria:**
- [ ] Embeddings generated on submission
- [ ] 384-dimension vectors stored
- [ ] Namespace per hackathon
- [ ] Metadata includes track, team, submission info
- [ ] < 500ms generation time

**Testing:**
```python
describe("Embedding Service")
  it("generates 384-dim embedding")
  it("stores embedding in ZeroDB")
  it("uses correct namespace")
  it("includes proper metadata")
  it("handles API errors gracefully")
```

**Dependencies:** Story 1.3, Story 3.4

---

#### Story 5.2: Semantic search implementation
**Type:** FEATURE
**Points:** 3
**Priority:** HIGH

**Description:**
Implement semantic search for finding similar submissions.

**Tasks:**
- Create `python-api/services/search_service.py`
- Implement natural language search
- Implement similarity search
- Filter by hackathon, track, status
- Return ranked results with similarity scores

**Acceptance Criteria:**
- [ ] Natural language queries work
- [ ] Results ranked by similarity
- [ ] Filter by metadata
- [ ] Top-k results configurable
- [ ] < 200ms search time

**Testing:**
```python
describe("Semantic Search")
  it("finds relevant submissions by text query")
  it("filters by hackathon")
  it("filters by track")
  it("returns similarity scores")
  it("handles no results gracefully")
```

**Dependencies:** Story 5.1

---

#### Story 5.3: Similar submissions endpoint
**Type:** FEATURE
**Points:** 2
**Priority:** MEDIUM

**Description:**
Create endpoint to find submissions similar to a given submission.

**Endpoint:**
- `GET /api/v1/submissions/{id}/similar` - Find similar submissions

**Acceptance Criteria:**
- [ ] Returns top-k similar submissions
- [ ] Similarity threshold configurable
- [ ] Excludes the query submission itself
- [ ] Includes similarity scores
- [ ] All tested

**Dependencies:** Story 5.2

---

#### Story 5.4: AI-powered recommendations
**Type:** FEATURE
**Points:** 2
**Priority:** LOW

**Description:**
Implement AI-powered recommendations for judges and organizers.

**Tasks:**
- Create recommendation service
- Recommend similar past projects to judges
- Suggest team formation based on skills
- Track quality of recommendations (RLHF)

**Acceptance Criteria:**
- [ ] Judges see similar submissions
- [ ] Team recommendations based on skills
- [ ] Feedback collected for improvement
- [ ] Recommendations improve over time

**Dependencies:** Story 5.2

---

#### Story 5.5: Embedding tests
**Type:** TEST
**Points:** 2
**Priority:** HIGH

**Description:**
Create comprehensive test suite for embeddings and search.

**Tasks:**
- Test embedding generation
- Test vector storage
- Test semantic search
- Test similarity calculations
- Achieve >= 80% coverage

**Acceptance Criteria:**
- [ ] All embedding flows tested
- [ ] Search accuracy validated
- [ ] Performance tested (< 500ms)
- [ ] >= 80% coverage
- [ ] Mock external APIs

**Dependencies:** Story 5.1, Story 5.2

---

## Epic 6: Real-Time Features & Advanced Functionality (20 points)

**Goal:** Implement real-time updates, event streaming, and advanced features.

### Stories

#### Story 6.1: Event streaming service
**Type:** FEATURE
**Points:** 5
**Priority:** MEDIUM

**Description:**
Implement event publishing and subscription using ZeroDB Events API.

**Tasks:**
- Create event publisher service
- Publish events on hackathon lifecycle changes
- Publish events on submission creation
- Publish events on score submission
- Document event schemas

**Events:**
- `hackathon.created`
- `hackathon.started`
- `hackathon.closed`
- `team.formed`
- `submission.created`
- `score.submitted`

**Acceptance Criteria:**
- [ ] Events published to ZeroDB
- [ ] Event schemas documented
- [ ] Events include proper metadata
- [ ] Event delivery < 50ms
- [ ] All events tested

**Dependencies:** Story 3.2, Story 3.4, Story 3.5

---

#### Story 6.2: Real-time leaderboard (Go service)
**Type:** FEATURE
**Points:** 5
**Priority:** MEDIUM

**Description:**
Implement Go service for real-time leaderboard updates via WebSocket.

**Tasks:**
- Create Go WebSocket service
- Subscribe to score events
- Calculate leaderboard in real-time
- Broadcast updates to clients
- Handle concurrent connections

**Acceptance Criteria:**
- [ ] WebSocket server on port 9000
- [ ] Leaderboard updates in < 100ms
- [ ] Handles 100+ concurrent connections
- [ ] Graceful reconnection handling
- [ ] All tested

**Dependencies:** Story 6.1

---

#### Story 6.3: Agent memory integration
**Type:** FEATURE
**Points:** 3
**Priority:** LOW

**Description:**
Integrate ZeroDB Memory API for AI agent persistent context.

**Tasks:**
- Create memory service
- Store judge preferences
- Store organizer workflows
- Retrieve context for AI assistants
- Search memory by semantic similarity

**Acceptance Criteria:**
- [ ] Judge preferences stored
- [ ] Context retrieved for AI
- [ ] Semantic search works
- [ ] Memory persists across sessions
- [ ] All tested

**Dependencies:** Story 1.3

---

#### Story 6.4: RLHF feedback collection
**Type:** FEATURE
**Points:** 3
**Priority:** LOW

**Description:**
Implement RLHF feedback collection for AI-powered features.

**Tasks:**
- Create RLHF service
- Log AI suggestions
- Collect user feedback (thumbs up/down)
- Store in ZeroDB RLHF API
- Generate improvement reports

**Acceptance Criteria:**
- [ ] AI interactions logged
- [ ] User feedback collected
- [ ] Feedback stored in ZeroDB
- [ ] Reports generated
- [ ] All tested

**Dependencies:** Story 5.4, Story 6.3

---

#### Story 6.5: Export and reporting
**Type:** FEATURE
**Points:** 2
**Priority:** LOW

**Description:**
Implement comprehensive data export and reporting.

**Tasks:**
- Export hackathon data (JSON, CSV)
- Generate PDF reports
- Export RLHF data
- Archive completed hackathons
- Schedule automated reports

**Acceptance Criteria:**
- [ ] Export to JSON/CSV working
- [ ] PDF reports generated
- [ ] RLHF data exportable
- [ ] Archival process automated
- [ ] All tested

**Dependencies:** Story 4.7, Story 6.4

---

#### Story 6.6: File upload and storage
**Type:** FEATURE
**Points:** 2
**Priority:** LOW

**Description:**
Implement file upload for team logos, submission artifacts, and documents.

**Tasks:**
- Integrate ZeroDB Files API
- Upload team logos
- Upload submission screenshots/videos
- Generate presigned URLs for downloads
- Validate file types and sizes

**Acceptance Criteria:**
- [ ] Files uploaded to ZeroDB
- [ ] Max size: 10MB per file
- [ ] Allowed types: images, PDFs, videos
- [ ] Presigned URLs for secure access
- [ ] All tested

**Dependencies:** Story 1.3

---

## Backlog Summary

### By Epic

| Epic | Stories | Points | Priority |
|------|---------|--------|----------|
| **Epic 1: Project Setup** | 5 | 8 | CRITICAL |
| **Epic 2: Authentication** | 6 | 12 | CRITICAL |
| **Epic 3: Data Layer** | 5 | 14 | HIGH |
| **Epic 4: API Endpoints** | 9 | 18 | HIGH |
| **Epic 5: Semantic Search** | 5 | 12 | MEDIUM |
| **Epic 6: Real-Time Features** | 6 | 20 | MEDIUM |
| **TOTAL** | **42** | **84** | - |

### By Priority

| Priority | Stories | Points |
|----------|---------|--------|
| CRITICAL | 10 | 24 |
| HIGH | 15 | 33 |
| MEDIUM | 12 | 20 |
| LOW | 5 | 7 |

### Recommended Development Sequence

**Sprint 1 (Week 1-2): Foundation**
- Epic 1: Project Setup (8 points)
- Epic 2: Authentication (12 points)
- **Total:** 20 points

**Sprint 2 (Week 3-4): Core Data**
- Epic 3: Data Layer (14 points)
- **Total:** 14 points

**Sprint 3 (Week 5-6): API Layer**
- Epic 4: API Endpoints (18 points)
- **Total:** 18 points

**Sprint 4 (Week 7-8): AI Features**
- Epic 5: Semantic Search (12 points)
- **Total:** 12 points

**Sprint 5 (Week 9-10): Advanced Features**
- Epic 6: Real-Time Features (20 points)
- **Total:** 20 points

### Definition of Done

A story is considered "Done" when:
- [ ] Code implemented and committed to feature branch
- [ ] All acceptance criteria met
- [ ] Tests written with >= 80% coverage
- [ ] Tests passing in CI
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] PR merged to main
- [ ] Deployed to staging
- [ ] Verified in staging environment

---

**Next Steps:**
1. Create GitHub issues for all stories in Epic 1
2. Assign stories to team members
3. Begin Sprint 1 planning
4. Set up project board
