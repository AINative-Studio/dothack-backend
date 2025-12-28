# dothack-backend

> AI-Native Hackathon Operations Platform - Production Backend built on ZeroDB

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![PRD](https://img.shields.io/badge/PRD-v1.0-green.svg)](../dothack-backendprd.md)
[![ZeroDB](https://img.shields.io/badge/ZeroDB-v1.5.0-purple.svg)](https://api.ainative.studio/docs)

## Overview

DotHack Backend is a **hybrid Python + Go microservices architecture** powering end-to-end hackathon operations with AI-enhanced features:

- **Semantic Search**: 384-dim vector embeddings for intelligent submission discovery
- **Real-Time Events**: Live leaderboards, submission notifications via WebSockets
- **AI Judge Assistant**: LLM-powered scoring suggestions with RLHF feedback loops
- **Agent Memory**: Persistent context across sessions for organizers, judges, and builders
- **Production-Ready**: Built on ZeroDB's unified database platform with auto-scaling

## Quick Links

- **[Backend PRD](../dothack-backendprd.md)** - Complete product requirements
- **[Architecture Docs](ARCHITECTURE.md)** - Technical design and data flows
- **[ZeroDB API Docs](https://api.ainative.studio/docs)** - Database platform reference

## Architecture at a Glance

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
         ├─ Tables (10 core tables)
         ├─ Vectors (384-dim BAAI embeddings)
         ├─ Embeddings API
         ├─ Memory (AI context)
         ├─ Events (RedPanda streaming)
         ├─ Files (MinIO S3-compatible)
         └─ RLHF (feedback loops)
```

## Technology Stack

### Backend Services
- **Python 3.11+ (FastAPI)**: API layer, business logic, AI/ML operations
- **Go 1.21+ (Gin/Echo)**: Real-time event streaming, concurrent workers, analytics
- **ZeroDB**: Unified database platform (PostgreSQL + pgvector + Qdrant + MinIO + RedPanda)

### Key ZeroDB Features
- **Model**: BAAI/bge-small-en-v1.5 (384 dimensions)
- **Vector Search**: < 50ms semantic similarity
- **Events**: Real-time streaming with RedPanda
- **Memory**: Agent context persistence
- **RLHF**: Automatic feedback collection

## Repository Structure (Monorepo)

```
dothack-backend/
├── .claude/                    # Claude Code integration
│   ├── commands/               # Slash commands (TDD, PR, review)
│   └── agents/                 # Agent configurations
│
├── python-api/                 # Python FastAPI service (Port 8000)
│   ├── api/
│   │   ├── routes/             # Endpoint definitions
│   │   ├── dependencies.py
│   │   └── middleware.py
│   ├── services/               # Business logic
│   ├── integrations/
│   │   └── zerodb/             # ZeroDB client wrapper
│   ├── models/                 # Pydantic models
│   ├── utils/
│   ├── config.py
│   ├── requirements.txt
│   └── main.py
│
├── go-services/                # Go microservices (Port 9000)
│   ├── cmd/
│   │   ├── event-stream/       # Real-time WebSocket service
│   │   ├── analytics/          # Concurrent analytics
│   │   └── worker/             # Background jobs
│   ├── pkg/
│   │   ├── zerodb/             # Go ZeroDB client
│   │   ├── handlers/
│   │   └── workers/
│   ├── internal/
│   ├── go.mod
│   └── main.go
│
├── scripts/                    # Deployment and setup scripts
│   ├── setup-zerodb.py         # Create tables and schemas
│   ├── seed-data.py            # Test data generation
│   └── deploy.sh               # Deployment automation
│
├── docs/                       # Additional documentation
│   ├── api/                    # API reference
│   ├── architecture/           # Architecture diagrams
│   └── deployment/             # Deployment guides
│
├── tests/                      # Test suites
│   ├── python/                 # Python unit/integration tests
│   └── go/                     # Go test suites
│
├── .env.example                # Environment variables template
├── .gitignore
├── docker-compose.yml          # Local development stack
├── README.md                   # This file
├── ARCHITECTURE.md             # Technical architecture
└── LICENSE
```

## Getting Started

### Prerequisites

- **Python 3.11+** - API layer
- **Go 1.21+** - Microservices
- **Docker & Docker Compose** - Local development (optional)
- **ZeroDB API Key** - Get from [AINative Studio](https://ainative.studio)

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/AINative-Studio/dothack-backend.git
   cd dothack-backend
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your ZeroDB credentials
   ```

   Required variables:
   ```bash
   ZERODB_API_KEY=your_api_key_here
   ZERODB_PROJECT_ID=your_project_uuid_here
   ZERODB_BASE_URL=https://api.ainative.studio
   ```

3. **Setup Python service**
   ```bash
   cd python-api
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Setup Go services**
   ```bash
   cd go-services
   go mod download
   ```

5. **Initialize ZeroDB tables** (when ready)
   ```bash
   python scripts/setup-zerodb.py
   ```

### Running Locally

#### Option 1: Docker Compose (Recommended)
```bash
docker-compose up
```

Services will be available at:
- Python API: http://localhost:8000
- Go Services: http://localhost:9000
- API Docs: http://localhost:8000/docs

#### Option 2: Manual Start

**Terminal 1 - Python FastAPI:**
```bash
cd python-api
uvicorn main:app --reload --port 8000
```

**Terminal 2 - Go Event Stream:**
```bash
cd go-services/cmd/event-stream
go run main.go
```

**Terminal 3 - Go Analytics:**
```bash
cd go-services/cmd/analytics
go run main.go
```

## Development Workflow

### Claude Code Integration

This repo uses `.claude/` for AI-assisted development:

```bash
# TDD workflow
/tdd create test for submission service

# Create PR
/pr create feature/semantic-search

# Code review
/review check submission_service.py
```

### API Development Cycle

1. **Define endpoint** in `python-api/api/routes/`
2. **Implement service** in `python-api/services/`
3. **Add ZeroDB call** in `python-api/integrations/zerodb/`
4. **Write tests** in `tests/python/`
5. **Run & validate** via `/docs` interactive API

### Testing

**Python tests:**
```bash
cd python-api
pytest tests/ -v
```

**Go tests:**
```bash
cd go-services
go test ./... -v
```

**Integration tests:**
```bash
docker-compose up -d
pytest tests/integration/ -v
```

## Core API Endpoints

### Hackathon Management
```bash
POST   /api/v1/hackathons              # Create hackathon
GET    /api/v1/hackathons               # List hackathons
GET    /api/v1/hackathons/{id}          # Get details
PATCH  /api/v1/hackathons/{id}          # Update
DELETE /api/v1/hackathons/{id}          # Delete
```

### Team & Projects
```bash
POST   /api/v1/hackathons/{id}/teams    # Create team
POST   /api/v1/teams/{id}/members       # Add member
POST   /api/v1/projects/{id}/submit     # Submit project
```

### Semantic Search
```bash
POST   /api/v1/hackathons/{id}/search   # Natural language search
GET    /api/v1/submissions/{id}/similar # Find similar submissions
```

### Judging
```bash
POST   /api/v1/submissions/{id}/score   # Submit score
GET    /api/v1/hackathons/{id}/leaderboard  # Get rankings
```

### Real-Time
```bash
WS     ws://localhost:9000/events       # WebSocket event stream
GET    /api/v1/hackathons/{id}/live     # Live stats
```

## ZeroDB Integration

### Table Schema Creation

```python
# All 10 core tables are created via setup script
python scripts/setup-zerodb.py

# Tables:
# - hackathons
# - tracks
# - participants
# - hackathon_participants
# - teams
# - team_members
# - projects
# - submissions
# - rubrics
# - scores
```

### Embedding Generation

```python
# Automatic on submission
POST /api/v1/projects/{id}/submit

# Backend flow:
# 1. Store submission in tables
# 2. Generate 384-dim embedding (BAAI/bge-small-en-v1.5)
# 3. Store vector in namespace: hackathons/{hackathon_id}/submissions
# 4. Publish event: submission.created
```

### Semantic Search

```python
# Natural language query
POST /api/v1/hackathons/{id}/search
{
  "query": "projects using AI for healthcare",
  "top_k": 10,
  "threshold": 0.7
}

# Returns ranked results with similarity scores
```

## Deployment

### Railway (Recommended)

1. **Create Railway services:**
   - Python API: `railway up` in `python-api/`
   - Go Event Stream: `railway up` in `go-services/cmd/event-stream/`
   - Go Analytics: `railway up` in `go-services/cmd/analytics/`

2. **Set environment variables** in Railway dashboard

3. **Deploy:**
   ```bash
   git push railway main
   ```

### Docker Production

```bash
# Build images
docker build -t dothack-python:latest -f python-api/Dockerfile .
docker build -t dothack-go-events:latest -f go-services/Dockerfile .

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

## Monitoring & Observability

### ZeroDB Usage Tracking
```bash
GET /v1/public/{project_id}/usage

# Monitor:
# - vectors_count (100K limit on Pro tier)
# - tables_count (50 limit)
# - events_count (1M/month limit)
# - storage_usage_mb (10GB limit)
```

### Application Metrics
- Request latency (P50, P95, P99)
- Error rates by endpoint
- RLHF interaction rates
- WebSocket connections

### Agent Logs
```python
# Automatic logging via ZeroDB Agent Logs API
POST /v1/public/{project_id}/database/agent-logs
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Follow `.claude/commands/` workflow for TDD
4. Commit with descriptive messages
5. Push and create Pull Request
6. Use `/review` for AI-assisted code review

## License

MIT License - see [LICENSE](LICENSE) file

## Support & Resources

- **Documentation**: [docs/](docs/)
- **PRD**: [dothack-backendprd.md](../dothack-backendprd.md)
- **ZeroDB Docs**: https://api.ainative.studio/docs
- **Issues**: https://github.com/AINative-Studio/dothack-backend/issues
- **Discord**: Join AINative Studio community

## Roadmap

### Phase 1: MVP (Current)
- ✅ Backend PRD & architecture
- ✅ ZeroDB integration design
- ⏳ Python FastAPI skeleton
- ⏳ Core CRUD endpoints
- ⏳ Embedding integration

### Phase 2: Advanced Features
- ⏳ Go event streaming
- ⏳ Real-time leaderboard
- ⏳ AI judge assistant
- ⏳ RLHF data collection

### Phase 3: Production
- ⏳ Load testing
- ⏳ Monitoring & alerts
- ⏳ Production deployment
- ⏳ Documentation finalization

---

**Built with ❤️ by AINative Studio**

*Powered by [ZeroDB](https://ainative.studio) - The Unified Intelligent Database Platform*
