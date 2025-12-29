# DotHack Backend PRD
## AI-Native Hackathon Operations Platform - Backend Architecture

**Version:** 1.0
**Last Updated:** 2025-12-28
**Status:** Draft
**ZeroDB API Version:** v1.5.0

---

## 1. Executive Summary

DotHack Backend is a **production-grade hackathon operations platform** built on ZeroDB's unified intelligent database platform. It provides complete hackathon lifecycle management with AI-powered features including semantic search, vector embeddings, real-time event streaming, and RLHF feedback collection.

### Key Capabilities
- **Hackathon Management**: Complete CRUD for hackathons, tracks, teams, and projects
- **Semantic Knowledge Base**: AI-powered submission search using 384-dim embeddings
- **Real-Time Operations**: Event streaming for live hackathon updates
- **Agent Memory**: Persistent context for AI assistants and judges
- **RLHF Data Collection**: Feedback loops for continuous improvement
- **Dual Database Model**: Serverless + Dedicated PostgreSQL options

---

## 2. Technology Stack

### Backend Languages (Hybrid Architecture)
- **Python (FastAPI)**: API layer, AI/ML operations, embedding generation
- **Go (Gin/Echo)**: High-performance services, concurrent operations, real-time features

### Database Platform
- **ZeroDB** (AINative Studio)
  - Base URL: `https://api.ainative.studio`
  - Authentication: API Key (X-API-Key header)
  - Project-scoped data isolation

### Core ZeroDB Services
1. **Projects API**: Multi-project management
2. **Tables API**: NoSQL document storage (10 core tables)
3. **Vectors API**: 384-dimension embeddings (BAAI/bge-small-en-v1.5)
4. **Embeddings API**: Generate, embed-and-store, semantic search
5. **Memory API**: AI agent persistent context
6. **Events API**: Real-time event streaming (RedPanda)
7. **Files API**: S3-compatible object storage (MinIO)
8. **RLHF API**: Feedback collection and model improvement
9. **SQL Query API**: Direct PostgreSQL access (optional)
10. **Agent Logs API**: Tracing and debugging

---

## 3. Data Architecture

### 3.1 ZeroDB Tables (NoSQL Storage)

All tables use project-scoped isolation with JSONB metadata support.

#### Core Tables

**hackathons**
```json
{
  "hackathon_id": "UUID PRIMARY KEY",
  "name": "TEXT NOT NULL",
  "description": "TEXT",
  "status": "TEXT CHECK(status IN ('DRAFT', 'LIVE', 'CLOSED'))",
  "start_at": "TIMESTAMP",
  "end_at": "TIMESTAMP",
  "tracks_config": "JSONB",
  "rubric_config": "JSONB",
  "created_at": "TIMESTAMP DEFAULT NOW()",
  "updated_at": "TIMESTAMP DEFAULT NOW()"
}
```

**tracks**
```json
{
  "track_id": "UUID PRIMARY KEY",
  "hackathon_id": "UUID",
  "name": "TEXT NOT NULL",
  "description": "TEXT",
  "requirements": "JSONB",
  "max_teams": "INTEGER",
  "created_at": "TIMESTAMP DEFAULT NOW()"
}
```

**participants**
```json
{
  "participant_id": "UUID PRIMARY KEY",
  "email": "TEXT UNIQUE NOT NULL",
  "name": "TEXT NOT NULL",
  "org": "TEXT",
  "skills": "JSONB",
  "bio": "TEXT",
  "created_at": "TIMESTAMP DEFAULT NOW()"
}
```

**hackathon_participants** (junction table)
```json
{
  "id": "UUID PRIMARY KEY",
  "hackathon_id": "UUID",
  "participant_id": "UUID",
  "role": "TEXT CHECK(role IN ('BUILDER', 'ORGANIZER', 'JUDGE', 'MENTOR'))",
  "metadata": "JSONB",
  "joined_at": "TIMESTAMP DEFAULT NOW()"
}
```

**teams**
```json
{
  "team_id": "UUID PRIMARY KEY",
  "hackathon_id": "UUID",
  "name": "TEXT NOT NULL",
  "track_id": "UUID",
  "description": "TEXT",
  "status": "TEXT CHECK(status IN ('FORMING', 'ACTIVE', 'SUBMITTED'))",
  "created_at": "TIMESTAMP DEFAULT NOW()"
}
```

**team_members** (junction table)
```json
{
  "id": "UUID PRIMARY KEY",
  "team_id": "UUID",
  "participant_id": "UUID",
  "role": "TEXT CHECK(role IN ('LEAD', 'MEMBER'))",
  "joined_at": "TIMESTAMP DEFAULT NOW()"
}
```

**projects**
```json
{
  "project_id": "UUID PRIMARY KEY",
  "hackathon_id": "UUID",
  "team_id": "UUID",
  "title": "TEXT NOT NULL",
  "one_liner": "TEXT",
  "description": "TEXT",
  "status": "TEXT CHECK(status IN ('IDEA', 'BUILDING', 'SUBMITTED'))",
  "repo_url": "TEXT",
  "demo_url": "TEXT",
  "tech_stack": "JSONB",
  "created_at": "TIMESTAMP DEFAULT NOW()",
  "updated_at": "TIMESTAMP DEFAULT NOW()"
}
```

**submissions**
```json
{
  "submission_id": "UUID PRIMARY KEY",
  "project_id": "UUID",
  "submitted_at": "TIMESTAMP",
  "submission_text": "TEXT NOT NULL",
  "artifact_links": "JSONB",
  "video_url": "TEXT",
  "vector_namespace": "TEXT",
  "created_at": "TIMESTAMP DEFAULT NOW()"
}
```

**rubrics**
```json
{
  "rubric_id": "UUID PRIMARY KEY",
  "hackathon_id": "UUID",
  "title": "TEXT NOT NULL",
  "criteria": "JSONB NOT NULL",
  "total_points": "INTEGER",
  "created_at": "TIMESTAMP DEFAULT NOW()"
}
```

**scores**
```json
{
  "score_id": "UUID PRIMARY KEY",
  "submission_id": "UUID",
  "judge_participant_id": "UUID",
  "rubric_id": "UUID",
  "scores_breakdown": "JSONB",
  "total_score": "REAL",
  "feedback": "TEXT",
  "created_at": "TIMESTAMP DEFAULT NOW()"
}
```

### 3.2 Vector Embeddings (Semantic Layer)

**Model**: BAAI/bge-small-en-v1.5
**Dimensions**: 384
**Namespaces**:
- `hackathons/{hackathon_id}/submissions` - Submission narratives
- `hackathons/{hackathon_id}/projects` - Project descriptions
- `hackathons/{hackathon_id}/feedback` - Judge feedback summaries

**Metadata Structure**:
```json
{
  "hackathon_id": "UUID",
  "track_id": "UUID",
  "team_id": "UUID",
  "project_id": "UUID",
  "submission_id": "UUID",
  "entity_type": "submission | project | feedback",
  "tags": ["AI", "ML", "Web3"],
  "submitted_at": "ISO8601 timestamp"
}
```

### 3.3 Event Streams (Real-Time)

**Topics**:
- `hackathon.lifecycle` - Status changes (DRAFT → LIVE → CLOSED)
- `team.events` - Team formation, member joins
- `submission.events` - New submissions, updates
- `judging.events` - Score submissions, feedback added

**Event Schema**:
```json
{
  "event_type": "submission.created | team.formed | score.submitted",
  "data": {
    "hackathon_id": "UUID",
    "entity_id": "UUID",
    "actor_id": "UUID",
    "metadata": {}
  },
  "timestamp": "ISO8601"
}
```

### 3.4 Agent Memory (AI Context)

**Use Cases**:
- Judge preferences and evaluation patterns
- Organizer workflows and configurations
- AI assistant context across sessions
- Builder interaction history

**Memory Schema**:
```json
{
  "content": "Judge prefers innovation over polish",
  "metadata": {
    "user_id": "judge_123",
    "hackathon_id": "hack_456",
    "session_id": "session_789",
    "importance": "high"
  },
  "tags": ["judging", "preferences"]
}
```

### 3.5 RLHF Data Collection

**Interaction Tracking**:
```json
{
  "type": "ai_suggestion",
  "prompt": "Suggest team formation strategy",
  "response": "Form teams around complementary skill sets...",
  "rating": 4,
  "feedback": "Good but missing timeline considerations"
}
```

---

## 4. API Architecture

### 4.1 Python Services (FastAPI)

**Port**: 8000
**Responsibilities**:
- HTTP API layer and request routing
- Business logic orchestration
- ZeroDB client wrappers
- Embedding generation and semantic search
- RLHF data collection

**Core Modules**:

```
python-api/
├── api/
│   ├── routes/
│   │   ├── hackathons.py       # Hackathon CRUD
│   │   ├── teams.py            # Team management
│   │   ├── submissions.py      # Submission handling
│   │   ├── judging.py          # Scoring & feedback
│   │   ├── search.py           # Semantic search
│   │   └── analytics.py        # Dashboards & reports
│   ├── dependencies.py         # FastAPI dependencies
│   └── middleware.py           # Auth, logging, CORS
├── services/
│   ├── hackathon_service.py
│   ├── team_service.py
│   ├── submission_service.py
│   ├── judging_service.py
│   └── semantic_service.py     # Embeddings wrapper
├── integrations/
│   ├── zerodb/
│   │   ├── client.py           # Base HTTP client
│   │   ├── projects.py
│   │   ├── tables.py
│   │   ├── vectors.py
│   │   ├── embeddings.py       # Generate, embed-and-store, search
│   │   ├── memory.py
│   │   ├── events.py
│   │   └── rlhf.py
│   └── types.py
├── models/
│   ├── hackathon.py            # Pydantic models
│   ├── team.py
│   ├── submission.py
│   └── score.py
├── utils/
│   ├── embedding.py            # Embedding helpers
│   ├── namespace.py            # Namespace generation
│   └── response.py
├── config.py
└── main.py
```

**Key Endpoints**:

```python
# Hackathon Management
POST   /api/v1/hackathons
GET    /api/v1/hackathons
GET    /api/v1/hackathons/{hackathon_id}
PATCH  /api/v1/hackathons/{hackathon_id}
DELETE /api/v1/hackathons/{hackathon_id}

# Team Operations
POST   /api/v1/hackathons/{hackathon_id}/teams
POST   /api/v1/teams/{team_id}/members
GET    /api/v1/teams/{team_id}

# Submissions
POST   /api/v1/projects/{project_id}/submit
GET    /api/v1/hackathons/{hackathon_id}/submissions

# Semantic Search
POST   /api/v1/hackathons/{hackathon_id}/search
GET    /api/v1/submissions/{submission_id}/similar

# Judging
POST   /api/v1/submissions/{submission_id}/score
GET    /api/v1/hackathons/{hackathon_id}/leaderboard

# Analytics
GET    /api/v1/hackathons/{hackathon_id}/stats
GET    /api/v1/hackathons/{hackathon_id}/export
```

### 4.2 Go Services (Microservices)

**Port**: 9000
**Responsibilities**:
- High-performance concurrent operations
- Real-time event streaming
- WebSocket connections
- Background jobs and workers
- Performance-critical paths

**Core Services**:

```
go-services/
├── cmd/
│   ├── event-stream/      # Real-time event streaming service
│   ├── analytics/         # Real-time analytics aggregation
│   └── worker/            # Background job processor
├── pkg/
│   ├── zerodb/
│   │   ├── client.go      # Go HTTP client for ZeroDB
│   │   ├── tables.go
│   │   ├── events.go
│   │   └── vectors.go
│   ├── handlers/
│   │   ├── websocket.go   # WebSocket handlers
│   │   └── events.go
│   ├── workers/
│   │   ├── embedding.go   # Async embedding generation
│   │   ├── aggregation.go # Score aggregation
│   │   └── cleanup.go     # Data cleanup jobs
│   └── models/
│       └── types.go
├── internal/
│   ├── config/
│   └── middleware/
└── main.go
```

**Key Responsibilities**:

1. **Event Streaming Service**
   - Subscribe to ZeroDB event topics
   - Broadcast to WebSocket clients
   - Real-time leaderboard updates
   - Live submission notifications

2. **Analytics Service**
   - Real-time score aggregation
   - Team progress tracking
   - Concurrent metric calculations

3. **Worker Service**
   - Batch embedding generation
   - Scheduled report generation
   - Data export jobs
   - Cleanup old hackathons

### 4.3 Service Communication

**Architecture Pattern**: Backend for Frontend (BFF)

```
Client (Web/Mobile)
    ↓
Python FastAPI (API Gateway)
    ↓
    ├─→ ZeroDB (Tables, Vectors, Embeddings)
    ├─→ Go Event Stream Service (WebSocket)
    └─→ Go Analytics Service (Real-time stats)
```

**Communication**:
- **HTTP/REST**: Python → Go (internal APIs)
- **gRPC** (optional Phase 2): High-performance RPC
- **Message Queue**: Async job dispatch (Python → Go workers)

---

## 5. Core User Flows with ZeroDB APIs

### 5.1 Organizer: Create Hackathon

```python
# Step 1: Create hackathon row
POST /v1/public/{project_id}/database/tables/hackathons/rows
{
  "data": {
    "hackathon_id": "uuid-generated",
    "name": "AI Hackathon 2025",
    "status": "DRAFT",
    "start_at": "2025-02-01T09:00:00Z",
    "end_at": "2025-02-03T18:00:00Z"
  }
}

# Step 2: Create tracks
POST /v1/public/{project_id}/database/tables/tracks/rows
{
  "data": {
    "track_id": "uuid-generated",
    "hackathon_id": "hackathon-uuid",
    "name": "AI/ML Track"
  }
}

# Step 3: Publish event
POST /v1/public/{project_id}/database/events
{
  "event_type": "hackathon.created",
  "data": {
    "hackathon_id": "hackathon-uuid"
  }
}
```

### 5.2 Builder: Submit Project

```python
# Step 1: Insert submission row
POST /v1/public/{project_id}/database/tables/submissions/rows
{
  "data": {
    "submission_id": "uuid-generated",
    "project_id": "project-uuid",
    "submission_text": "Full project description...",
    "artifact_links": {"github": "...", "demo": "..."}
  }
}

# Step 2: Generate and store embeddings
POST /v1/public/{project_id}/embeddings/embed-and-store
{
  "documents": [{
    "id": "submission-uuid",
    "text": "Full project description...",
    "metadata": {
      "hackathon_id": "hackathon-uuid",
      "track_id": "track-uuid",
      "team_id": "team-uuid",
      "entity_type": "submission"
    }
  }],
  "namespace": "hackathons/hack-uuid/submissions",
  "upsert": true
}

# Step 3: Update project status
PUT /v1/public/{project_id}/database/tables/projects/rows/{project_row_id}
{
  "data": {
    "status": "SUBMITTED"
  }
}

# Step 4: Publish event
POST /v1/public/{project_id}/database/events
{
  "event_type": "submission.created",
  "data": {
    "submission_id": "submission-uuid",
    "hackathon_id": "hackathon-uuid"
  }
}
```

### 5.3 Judge: Score Submission with AI Assistance

```python
# Step 1: Search agent memory for judge preferences
POST /v1/public/{project_id}/database/memory/search
{
  "query": "judge scoring preferences innovation",
  "limit": 5
}

# Step 2: Submit score
POST /v1/public/{project_id}/database/tables/scores/rows
{
  "data": {
    "score_id": "uuid-generated",
    "submission_id": "submission-uuid",
    "judge_participant_id": "judge-uuid",
    "scores_breakdown": {
      "innovation": 8,
      "execution": 7,
      "impact": 9
    },
    "total_score": 24,
    "feedback": "Excellent innovation..."
  }
}

# Step 3: Log RLHF interaction
POST /v1/public/{project_id}/database/rlhf/interactions
{
  "type": "ai_suggestion",
  "prompt": "Suggest rubric scores for submission",
  "response": "Suggested scores: innovation=8, execution=7...",
  "rating": 5
}

# Step 4: Store judge memory
POST /v1/public/{project_id}/database/memory
{
  "content": "Judge values innovation over polish in early-stage prototypes",
  "metadata": {
    "user_id": "judge-uuid",
    "hackathon_id": "hackathon-uuid"
  },
  "tags": ["judging", "preferences"]
}
```

### 5.4 Organizer: Semantic Search Submissions

```python
# Natural language search
POST /v1/public/{project_id}/embeddings/search
{
  "query": "projects using machine learning for healthcare",
  "top_k": 10,
  "namespace": "hackathons/hack-uuid/submissions",
  "filter": {
    "track_id": "ai-ml-track-uuid"
  },
  "similarity_threshold": 0.7,
  "include_metadata": true
}

# Response includes ranked submissions with similarity scores
```

### 5.5 Analytics: Real-Time Leaderboard

```python
# Go Analytics Service
# 1. List all scores for hackathon
GET /v1/public/{project_id}/database/tables/scores/rows?filter={"hackathon_id":"uuid"}

# 2. Aggregate in Go (concurrent processing)
# 3. Cache results
# 4. Broadcast via WebSocket
```

---

## 6. Advanced Features

### 6.1 Semantic Similarity Recommendations

**Use Case**: "Find similar submissions to this one"

```python
# Get submission embedding
GET /v1/public/{project_id}/database/vectors/{submission_id}

# Search for similar vectors
POST /v1/public/{project_id}/database/vectors/search
{
  "query_vector": [0.1, 0.2, ...],  # Retrieved embedding
  "top_k": 5,
  "namespace": "hackathons/hack-uuid/submissions",
  "similarity_metric": "cosine"
}
```

### 6.2 AI Judge Assistant

**Use Case**: AI suggests scores based on rubric and past feedback

```python
# 1. Retrieve judge's past evaluations from memory
POST /v1/public/{project_id}/database/memory/search
{
  "query": "judge scoring patterns for innovation",
  "limit": 10
}

# 2. Search similar submissions
POST /v1/public/{project_id}/embeddings/search
{
  "query": "current submission text...",
  "namespace": "hackathons/hack-uuid/submissions"
}

# 3. Generate AI suggestion (external LLM call)
# 4. Log interaction for RLHF
POST /v1/public/{project_id}/database/rlhf/interactions
{
  "prompt": "Suggest scores for submission based on rubric",
  "response": "AI generated suggestion...",
  "rating": null  # To be filled by judge
}
```

### 6.3 Export Hackathon Data

```python
# 1. Query all tables
GET /v1/public/{project_id}/database/tables/hackathons/rows/{hackathon_row_id}
GET /v1/public/{project_id}/database/tables/submissions/rows?filter=...
GET /v1/public/{project_id}/database/tables/scores/rows?filter=...

# 2. Export RLHF data
POST /v1/public/{project_id}/database/rlhf/export
{
  "format": "json",
  "start_date": "2025-02-01",
  "end_date": "2025-02-03"
}

# 3. Generate comprehensive report (Python service)
# 4. Store in Files API
POST /v1/public/{project_id}/database/files
{
  "filename": "hackathon_report.pdf",
  "size": 1024000,
  "content_type": "application/pdf"
}
```

---

## 7. Non-Functional Requirements

### 7.1 Performance

| Operation | Target | ZeroDB Capability |
|-----------|--------|-------------------|
| Create hackathon | < 200ms | Tables API |
| Submit project | < 500ms | Tables + Embeddings API |
| Semantic search | < 200ms | Embeddings search (< 100ms per text) |
| Real-time events | < 50ms | Event streaming (RedPanda) |
| Leaderboard update | < 100ms | Concurrent Go aggregation |

### 7.2 Scalability

**ZeroDB Tier**: Pro Tier (recommended for MVP)
- Projects: 10 max
- Vectors: 100,000 max (supports ~100k submissions)
- Tables: 50 max (10 core tables, room for expansion)
- Events: 1,000,000/month
- Storage: 10 GB

**Upgrade Path**: Scale Tier for production
- Vectors: 1,000,000 max
- Tables: 500 max
- Events: 10,000,000/month
- Quantum features enabled

### 7.3 Security & Authentication

**🚨 MANDATORY: Use AINative Studio Authentication System**

DotHack Backend **MUST NOT** build standalone authentication. Instead, it **MUST** integrate with the existing AINative Studio authentication platform.

**Rationale:**
- ✅ Centralized user management across all AINative products
- ✅ Single Sign-On (SSO) capability for users
- ✅ OAuth integration (GitHub, LinkedIn) pre-built
- ✅ Production-grade security (bcrypt, JWT, token blacklisting)
- ✅ API key management for programmatic access
- ✅ Zero maintenance cost for auth infrastructure

#### Authentication Architecture

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

#### AINative Auth Endpoints

**Base URL:** `https://api.ainative.studio`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/auth/register` | POST | User registration |
| `/v1/auth/login` | POST | Email/password login |
| `/v1/auth/logout` | POST | Token blacklisting |
| `/v1/auth/refresh` | POST | Refresh access token |
| `/v1/auth/me` | GET | Get current user (token verification) |
| `/v1/auth/github/callback` | POST | GitHub OAuth |
| `/v1/auth/linkedin/callback` | POST | LinkedIn OAuth |

#### Authentication Methods

| Method | Header | Format | Use Case |
|--------|--------|--------|----------|
| **JWT Token** | `Authorization` | `Bearer {token}` | Web/mobile apps |
| **API Key** | `X-API-Key` | `{api_key}` | Server-to-server |

#### Role-Based Access Control (RBAC)

**Roles stored in ZeroDB `hackathon_participants` table:**

```json
{
  "id": "uuid",
  "hackathon_id": "uuid",
  "participant_id": "uuid",  // AINative user_id
  "role": "ORGANIZER | BUILDER | JUDGE | MENTOR",
  "metadata": {
    "ainative_user_email": "user@example.com",
    "ainative_user_name": "John Doe"
  },
  "joined_at": "timestamp"
}
```

#### Implementation Requirements

**✅ REQUIRED:**
1. Verify all tokens via AINative `/v1/auth/me`
2. Store AINative `user_id` in `hackathon_participants`
3. Implement role checking for protected endpoints
4. Use API keys for server-to-server calls

**❌ FORBIDDEN:**
1. Building custom `/auth/register`, `/auth/login` endpoints
2. Storing passwords in DotHack database
3. Custom JWT token generation
4. Custom OAuth implementation

#### Data Validation
- Pydantic models for request validation
- SQL injection prevention (ZeroDB handles)
- Rate limiting: Pro tier (10,000 requests/hour)

**See `/docs/AUTHENTICATION_ARCHITECTURE.md` for complete implementation guide.**

### 7.4 Monitoring

1. **ZeroDB Usage**
   ```python
   GET /v1/public/{project_id}/usage
   ```
   Track: vectors_count, tables_count, events_count, storage_usage_mb

2. **Application Metrics**
   - Request latency (P50, P95, P99)
   - Error rates by endpoint
   - RLHF interaction rates
   - WebSocket connection count

3. **Agent Logs**
   ```python
   POST /v1/public/{project_id}/database/agent-logs
   {
     "agent_id": "judge_assistant_ai",
     "action": "suggest_scores",
     "result": {"status": "success"},
     "execution_time_ms": 450
   }
   ```

---

## 8. Deployment Architecture

### 8.1 Services

```
┌─────────────────────────────────────────┐
│         Load Balancer / API Gateway      │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴──────────┐
        │                    │
   ┌────▼─────┐        ┌────▼─────┐
   │  Python  │        │    Go    │
   │ FastAPI  │◄──────►│ Services │
   │  (8000)  │        │  (9000)  │
   └────┬─────┘        └────┬─────┘
        │                   │
        └───────┬───────────┘
                │
        ┌───────▼────────┐
        │    ZeroDB      │
        │ (AINative API) │
        └────────────────┘
         ├─ Tables
         ├─ Vectors (384-dim)
         ├─ Embeddings
         ├─ Memory
         ├─ Events
         ├─ Files
         └─ RLHF
```

### 8.2 Environment Variables

```bash
# ZeroDB
ZERODB_API_KEY=your_api_key
ZERODB_PROJECT_ID=your_project_uuid
ZERODB_BASE_URL=https://api.ainative.studio

# Python Service
PYTHON_API_PORT=8000
PYTHON_API_HOST=0.0.0.0
LOG_LEVEL=INFO

# Go Service
GO_SERVICE_PORT=9000
GO_SERVICE_HOST=0.0.0.0
WORKER_CONCURRENCY=10

# Optional: External LLM for AI features
OPENAI_API_KEY=optional_for_ai_features
```

### 8.3 Deployment Options

1. **Railway** (Recommended)
   - Python FastAPI: Railway Service
   - Go Services: Railway Service
   - ZeroDB: Already hosted by AINative

2. **Docker Compose** (Local Dev)
   ```yaml
   services:
     python-api:
       build: ./python-api
       ports: ["8000:8000"]
     go-services:
       build: ./go-services
       ports: ["9000:9000"]
   ```

3. **Kubernetes** (Production)
   - Python API: Deployment + HPA
   - Go Services: StatefulSet for workers
   - Ingress: NGINX

---

## 9. Development Roadmap

### Phase 1: MVP (4 weeks)
- ✅ ZeroDB project setup
- ✅ Create 10 core tables
- ✅ Python FastAPI skeleton
- ✅ Basic CRUD endpoints
- ✅ Embedding integration
- ✅ Semantic search

### Phase 2: Advanced Features (4 weeks)
- ✅ Go event streaming service
- ✅ Real-time leaderboard
- ✅ AI judge assistant
- ✅ RLHF data collection
- ✅ Agent memory integration

### Phase 3: Production (2 weeks)
- ✅ Performance optimization
- ✅ Monitoring & logging
- ✅ Documentation
- ✅ Load testing
- ✅ Production deployment

---

## 10. API Reference (Backend Internal)

### 10.1 Python FastAPI → ZeroDB

All ZeroDB calls use project-scoped API key:

```python
from integrations.zerodb import ZeroDBClient

client = ZeroDBClient(
    api_key=os.getenv("ZERODB_API_KEY"),
    project_id=os.getenv("ZERODB_PROJECT_ID")
)

# Tables
client.tables.create_row("hackathons", data={...})
client.tables.list_rows("hackathons", skip=0, limit=100)
client.tables.update_row("hackathons", row_id, data={...})

# Embeddings
client.embeddings.embed_and_store(documents=[...], namespace="...")
client.embeddings.search(query="...", namespace="...", top_k=10)

# Memory
client.memory.store(content="...", metadata={...})
client.memory.search(query="...", limit=10)

# Events
client.events.publish(event_type="...", data={...})

# RLHF
client.rlhf.log_interaction(prompt="...", response="...", rating=5)
```

### 10.2 Go Services → ZeroDB

```go
package zerodb

type Client struct {
    APIKey    string
    ProjectID string
    BaseURL   string
}

// Events
func (c *Client) SubscribeEvents(topic string, handler func(Event)) error
func (c *Client) PublishEvent(eventType string, data map[string]interface{}) error

// Vectors
func (c *Client) SearchVectors(queryVector []float64, namespace string, topK int) ([]SearchResult, error)

// Tables
func (c *Client) ListRows(tableName string, filter map[string]interface{}) ([]Row, error)
```

---

## 11. Success Metrics

### Technical Metrics
- **API Response Time**: P95 < 200ms
- **Embedding Generation**: < 100ms per submission
- **Event Delivery Latency**: < 50ms
- **Search Accuracy**: Semantic similarity > 0.7 for relevant matches

### Business Metrics
- **Hackathons Hosted**: 10+ per quarter
- **Submissions Processed**: 500+ per hackathon
- **AI Interaction Rate**: 30%+ of judges use AI suggestions
- **RLHF Data Quality**: 80%+ interactions rated 4+

### Operational Metrics
- **Uptime**: 99.9%
- **Zero Data Loss**: All submissions persisted
- **Cost Efficiency**: < $100/month for Pro tier (10 hackathons/month)

---

## 12. Risk Mitigation

### Technical Risks

| Risk | Mitigation | ZeroDB Feature |
|------|-----------|----------------|
| Embedding generation slow | Batch processing in Go worker | Async jobs |
| Vector search accuracy low | Use 384-dim BAAI model, tune threshold | Native embedding API |
| Real-time events delayed | Go concurrent event handlers | RedPanda streaming |
| Data loss on crashes | ZeroDB handles persistence | Auto-backups |
| API rate limits | Cache frequently accessed data | Pro tier: 10k req/hr |

### Operational Risks

| Risk | Mitigation |
|------|-----------|
| ZeroDB API downtime | Implement retry logic with exponential backoff |
| Cost overruns | Monitor usage API, set alerts at 80% tier limits |
| Complex queries slow | Use Go for aggregations, cache leaderboards |

---

## 13. Appendix

### A. ZeroDB Endpoint Mapping

| Feature | ZeroDB Endpoint | Usage |
|---------|----------------|-------|
| Create hackathon | `POST /v1/public/{project}/database/tables/hackathons/rows` | Core CRUD |
| Store submission embedding | `POST /v1/public/{project}/embeddings/embed-and-store` | Semantic search |
| Search submissions | `POST /v1/public/{project}/embeddings/search` | Natural language |
| Publish event | `POST /v1/public/{project}/database/events` | Real-time updates |
| Store judge memory | `POST /v1/public/{project}/database/memory` | AI context |
| Log AI interaction | `POST /v1/public/{project}/database/rlhf/interactions` | RLHF |
| Get leaderboard | `GET /v1/public/{project}/database/tables/scores/rows` | Analytics |

### B. Embedding Dimensions

- **Model**: BAAI/bge-small-en-v1.5 (HuggingFace)
- **Dimensions**: 384 (NOT 1536)
- **Cost**: FREE (Railway-hosted)
- **Performance**: < 100ms per text

### C. Vector Namespaces Convention

```
hackathons/{hackathon_id}/submissions
hackathons/{hackathon_id}/projects
hackathons/{hackathon_id}/feedback
```

### D. Event Types Taxonomy

```
hackathon.created
hackathon.started
hackathon.closed
team.formed
team.member_joined
submission.created
score.submitted
feedback.added
```

---

**End of Backend PRD**

**Next Steps**:
1. Review and approve PRD
2. Set up ZeroDB project
3. Create table schemas
4. Scaffold Python FastAPI
5. Build Go event service
6. Implement core flows

**Questions?** Contact: backend-team@ainative.studio
