# DotHack Backend - Quick Reference Guide

## File Locations

### API Endpoints
- **Location:** `/Users/aideveloper/dothack-backend/python-api/api/routes/`
- **13 route modules:**
  - `hackathons.py` (5 endpoints)
  - `participants.py` (4 endpoints)
  - `tracks.py` (5 endpoints)
  - `teams.py` (7 endpoints)
  - `submissions.py` (8 endpoints)
  - `judging.py` (3 endpoints)
  - `prizes.py` (6 endpoints)
  - `dashboard.py` (4 endpoints)
  - `search.py` (2 endpoints)
  - `recommendations.py` (3 endpoints)
  - `analytics.py` (2 endpoints)
  - `export.py` (3 endpoints)
  - `files.py` (6 endpoints)

### Business Logic
- **Location:** `/Users/aideveloper/dothack-backend/python-api/services/`
- **18 service modules** (8,918 lines total)
- Key services:
  - `hackathon_service.py` - Hackathon CRUD
  - `team_service.py` - Team management
  - `submission_service.py` - Project submissions
  - `judging_service.py` - Scoring & judging
  - `dashboard_service.py` - Aggregated statistics
  - `search_service.py` - Semantic search
  - `embedding_service.py` - AI embeddings

### Authentication & Integrations
- **AINative Auth:** `/Users/aideveloper/dothack-backend/python-api/integrations/ainative/`
- **ZeroDB Client:** `/Users/aideveloper/dothack-backend/python-api/integrations/zerodb/`
- **Dependencies:** `/Users/aideveloper/dothack-backend/python-api/api/dependencies.py`

### Tests
- **Location:** `/Users/aideveloper/dothack-backend/python-api/tests/`
- **35 test files** with 80%+ coverage
- Run: `pytest tests/ -v --cov --cov-report=term-missing`

### Database Setup
- **Script:** `/Users/aideveloper/dothack-backend/scripts/setup-zerodb-tables.py`
- **Tables:** 10 core tables (hackathons, teams, submissions, etc.)

### Documentation
- **API Status:** `/Users/aideveloper/dothack-backend/docs/IMPLEMENTATION_STATUS.md`
- **Auth Docs:** `/Users/aideveloper/dothack-backend/docs/AUTHENTICATION_ARCHITECTURE.md`
- **Backlog:** `/Users/aideveloper/dothack-backend/docs/planning/BACKLOG.md`

---

## Running the Backend

### Start API Server
```bash
cd /Users/aideveloper/dothack-backend/python-api
uvicorn main:app --reload --port 8000
```

**Access:**
- API Docs: `http://localhost:8000/v1/docs`
- API Root: `http://localhost:8000/`
- Health: `http://localhost:8000/health`

### Run Tests
```bash
cd /Users/aideveloper/dothack-backend/python-api
pytest tests/ -v --cov --cov-report=term-missing
```

### Setup Database Tables
```bash
cd /Users/aideveloper/dothack-backend
python scripts/setup-zerodb-tables.py --apply
```

---

## Configuration

### Required Environment Variables
```bash
# Authentication
AINATIVE_API_URL=https://api.ainative.studio
AINATIVE_API_KEY=<your_key>

# Database
ZERODB_API_KEY=<your_key>
ZERODB_PROJECT_ID=<your_uuid>
ZERODB_BASE_URL=https://api.ainative.studio

# Application
PORT=8000
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### Load from `.env`
```bash
cd python-api
# Create .env file with above variables
# App will automatically load from .env
```

---

## API Endpoint Summary

| Method | Endpoint | Purpose | Role |
|--------|----------|---------|------|
| POST | `/api/v1/hackathons` | Create hackathon | AUTH |
| GET | `/api/v1/hackathons` | List hackathons | AUTH |
| GET | `/api/v1/hackathons/{id}` | Get hackathon | AUTH |
| PATCH | `/api/v1/hackathons/{id}` | Update hackathon | ORGANIZER |
| DELETE | `/api/v1/hackathons/{id}` | Delete hackathon | ORGANIZER |
| POST | `/api/v1/hackathons/{id}/teams` | Create team | AUTH |
| GET | `/api/v1/hackathons/{id}/teams` | List teams | AUTH |
| POST | `/api/v1/hackathons/{id}/submissions` | Submit project | AUTH |
| GET | `/api/v1/dashboard/organizer` | Organizer dashboard | ORGANIZER |
| GET | `/api/v1/dashboard/builder` | Builder dashboard | BUILDER |
| GET | `/api/v1/dashboard/judge` | Judge dashboard | JUDGE |
| POST | `/api/v1/hackathons/{id}/scores` | Submit score | JUDGE |

---

## Authentication

### JWT Token
```bash
# In request header:
Authorization: Bearer <jwt_token>
```

### API Key
```bash
# In request header:
x-api-key: <api_key>
```

### Get Current User
```python
# In any endpoint:
async def my_endpoint(user = Depends(get_current_user)):
    user_id = user["id"]
    email = user["email"]
```

---

## Database Tables

1. **hackathons** - Hackathon events
2. **tracks** - Competition categories
3. **participants** - User profiles
4. **hackathon_participants** - User roles per hackathon
5. **teams** - Team information
6. **team_members** - Team membership
7. **projects** - Project submissions
8. **submissions** - Submission artifacts
9. **rubrics** - Judging rubrics
10. **scores** - Judge scores

---

## Key Service Methods

### Hackathon Service
```python
await hackathon_service.create_hackathon(...)
await hackathon_service.list_hackathons(...)
await hackathon_service.get_hackathon(...)
await hackathon_service.update_hackathon(...)
await hackathon_service.delete_hackathon(...)
```

### Team Service
```python
await team_service.create_team(...)
await team_service.list_teams(...)
await team_service.get_team(...)
await team_service.update_team(...)
await team_service.delete_team(...)
await team_service.add_member(...)
await team_service.remove_member(...)
```

### Submission Service
```python
await submission_service.create_submission(...)
await submission_service.list_submissions(...)
await submission_service.get_submission(...)
await submission_service.update_submission(...)
await submission_service.delete_submission(...)
```

### Dashboard Service
```python
await dashboard_service.get_organizer_dashboard(...)
await dashboard_service.get_builder_dashboard(...)
await dashboard_service.get_judge_dashboard(...)
await dashboard_service.get_hackathon_overview(...)
```

---

## Testing Examples

### Test Single Endpoint
```bash
cd python-api
pytest tests/test_hackathon_endpoints.py -v
```

### Test Specific Function
```bash
pytest tests/test_hackathon_service.py::test_create_hackathon -v
```

### Generate Coverage Report
```bash
pytest tests/ --cov --cov-report=html
# View: htmlcov/index.html
```

---

## Common Tasks

### Add New Endpoint
1. Create route in `/python-api/api/routes/{feature}.py`
2. Create service in `/python-api/services/{feature}_service.py`
3. Create schema in `/python-api/api/schemas/{feature}.py`
4. Create tests in `/python-api/tests/test_{feature}.py`
5. Run tests to ensure 80%+ coverage
6. Commit with reference to GitHub issue

### Add Authorization Check
```python
from services.authorization import check_organizer

# In endpoint:
await check_organizer(user_id=user["id"], hackathon_id=hackathon_id, zerodb=zerodb)
```

### Use ZeroDB
```python
from integrations.zerodb.client import ZeroDBClient

client = ZeroDBClient()
# Use client.tables for table operations
# Use client.vectors for search
# Use client.embeddings for embeddings
```

### Query ZeroDB Table
```python
# Example: Get all hackathons by user
result = await zerodb_client.tables.query(
    table_name="hackathons",
    where=[{"field": "organizer_id", "op": "==", "value": user_id}]
)
```

---

## Troubleshooting

### Tests Failing
1. Check `.env` file has correct credentials
2. Ensure ZeroDB tables are created: `python scripts/setup-zerodb-tables.py --apply`
3. Run: `pytest tests/ -v` to see detailed errors

### API Not Starting
1. Check port 8000 is available: `lsof -i :8000`
2. Verify Python dependencies: `pip install -r requirements.txt`
3. Check config: `python -c "from config import settings; print(settings)"`

### Authentication Errors
1. Verify JWT token is valid: Check with AINative API
2. Check Authorization header format: `Bearer <token>`
3. Check API key in X-API-Key header (case-insensitive)

### ZeroDB Connection Issues
1. Verify API credentials in `.env`
2. Test connection: `python -c "from integrations.zerodb.client import ZeroDBClient; client = ZeroDBClient()"`
3. Check firewall/proxy settings

---

## Performance Tips

1. **Use pagination** for list endpoints (avoid fetching all records)
2. **Cache dashboard data** - Expensive to compute
3. **Use semantic search** for finding similar projects
4. **Batch operations** when importing data
5. **Monitor slow queries** in logs

---

## Deployment

### To Railway
1. Push to `main` branch
2. GitHub Actions CI/CD will run tests
3. Deploy to Railway automatically on success
4. Monitor: `railway logs`

### Environment Variables (Railway)
Add these in Railway dashboard:
- `ZERODB_API_KEY`
- `ZERODB_PROJECT_ID`
- `AINATIVE_API_KEY`
- `PORT=8000`

---

## Resources

- **PRD:** `/Users/aideveloper/dothack-backend/dothack-backendprd.md`
- **Backlog:** `/Users/aideveloper/dothack-backend/docs/planning/BACKLOG.md`
- **Auth Architecture:** `/Users/aideveloper/dothack-backend/docs/AUTHENTICATION_ARCHITECTURE.md`
- **ZeroDB Docs:** https://zerodb.com/docs
- **AINative Docs:** https://ainative.studio/docs
- **FastAPI Docs:** https://fastapi.tiangolo.com/
