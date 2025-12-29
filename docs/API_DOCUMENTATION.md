# DotHack Hackathon Platform - API Documentation

Complete API documentation for the DotHack Hackathon Platform backend.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [API Documentation Access](#api-documentation-access)
- [Using Postman Collection](#using-postman-collection)
- [API Endpoints](#api-endpoints)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)

## Overview

The DotHack Hackathon Platform API is a comprehensive REST API for managing hackathons, teams, submissions, and judging. Built with FastAPI, it provides automatic OpenAPI documentation and type-safe request/response handling.

**Base URL:** `http://localhost:8000` (development)

**API Version:** v1

## Authentication

All endpoints (except `/health`) require authentication using one of the following methods:

### JWT Bearer Token

Include in the `Authorization` header:

```
Authorization: Bearer <your-jwt-token>
```

### API Key

Include in the `X-API-Key` header:

```
X-API-Key: <your-api-key>
```

## API Documentation Access

The DotHack API provides three ways to access documentation:

### 1. Interactive Swagger UI

Visit: `http://localhost:8000/v1/docs`

Features:
- Interactive API explorer
- Try out endpoints directly from browser
- View request/response schemas
- Authentication support

### 2. ReDoc Documentation

Visit: `http://localhost:8000/v1/redoc`

Features:
- Clean, readable documentation
- Code samples
- Comprehensive schema documentation
- Search functionality

### 3. OpenAPI JSON Schema

Visit: `http://localhost:8000/openapi.json`

Use this for:
- Generating client libraries
- API testing tools
- Custom documentation

## Using Postman Collection

### Import Collection

1. Open Postman
2. Click "Import" button
3. Select `postman/DotHack-API.postman_collection.json`
4. Collection will be added to your workspace

### Configure Environment Variables

The collection uses the following variables (configure in Postman environment):

| Variable | Description | Example |
|----------|-------------|---------|
| `base_url` | API base URL | `http://localhost:8000` |
| `auth_token` | JWT authentication token | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| `hackathon_id` | Sample hackathon UUID | `550e8400-e29b-41d4-a716-446655440000` |
| `team_id` | Sample team UUID | `660e8400-e29b-41d4-a716-446655440001` |
| `submission_id` | Sample submission UUID | `770e8400-e29b-41d4-a716-446655440002` |
| `user_id` | Current user UUID | `880e8400-e29b-41d4-a716-446655440003` |
| `participant_id` | Sample participant UUID | `990e8400-e29b-41d4-a716-446655440004` |
| `track_id` | Sample track UUID | `aa0e8400-e29b-41d4-a716-446655440005` |
| `rubric_id` | Sample rubric UUID | `bb0e8400-e29b-41d4-a716-446655440006` |

### Quick Start

1. Set `base_url` to your API URL
2. Obtain JWT token from authentication endpoint
3. Set `auth_token` variable
4. Test with "Health Check" endpoint
5. Explore other endpoints

## API Endpoints

### Health

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/health` | Check API health status | No |

### Hackathons

| Method | Endpoint | Description | Auth Required | Role |
|--------|----------|-------------|---------------|------|
| POST | `/api/v1/hackathons` | Create hackathon | Yes | Any |
| GET | `/api/v1/hackathons` | List hackathons | Yes | Any |
| GET | `/api/v1/hackathons/{id}` | Get hackathon details | Yes | Any |
| PATCH | `/api/v1/hackathons/{id}` | Update hackathon | Yes | ORGANIZER |
| DELETE | `/api/v1/hackathons/{id}` | Delete hackathon (soft) | Yes | ORGANIZER |

**Status Values:**
- `draft` - Being planned
- `upcoming` - Visible, accepting registrations
- `active` - Currently running
- `judging` - Submissions closed, judging in progress
- `completed` - Finished, results published
- `cancelled` - Cancelled

### Teams

| Method | Endpoint | Description | Auth Required | Role |
|--------|----------|-------------|---------------|------|
| POST | `/teams` | Create team | Yes | Any |
| GET | `/teams` | List teams | Yes | Any |
| GET | `/teams/{id}` | Get team details | Yes | Any |
| PUT | `/teams/{id}` | Update team | Yes | Team LEAD |
| DELETE | `/teams/{id}` | Delete team | Yes | Team LEAD |
| POST | `/teams/{id}/members` | Add team member | Yes | Team LEAD |
| DELETE | `/teams/{id}/members/{participant_id}` | Remove team member | Yes | Team LEAD |

**Team Status Values:**
- `FORMING` - Team is being formed
- `ACTIVE` - Team is actively working
- `SUBMITTED` - Team has submitted project

### Submissions

| Method | Endpoint | Description | Auth Required | Role |
|--------|----------|-------------|---------------|------|
| POST | `/v1/submissions` | Create submission | Yes | Any |
| GET | `/v1/submissions` | List submissions | Yes | Any |
| GET | `/v1/submissions/{id}` | Get submission details | Yes | Any |
| PUT | `/v1/submissions/{id}` | Update submission | Yes | Team member |
| DELETE | `/v1/submissions/{id}` | Delete submission | Yes | Team member |
| POST | `/v1/submissions/{id}/files` | Upload file | Yes | Team member |

**Submission Status Values:**
- `DRAFT` - Submission in progress
- `SUBMITTED` - Submitted for judging
- `SCORED` - Judging completed

**File Upload:**
- Maximum file size: 100MB
- File content must be base64-encoded
- Supported types: All standard MIME types

### Judging

| Method | Endpoint | Description | Auth Required | Role |
|--------|----------|-------------|---------------|------|
| POST | `/judging/scores` | Submit score | Yes | JUDGE |
| GET | `/judging/hackathons/{id}/results` | Get leaderboard | Yes | Any |
| GET | `/judging/assignments` | Get judge assignments | Yes | JUDGE |

**Scoring:**
- Score range: 0-100
- Judge can only submit one score per submission
- Scores are averaged across all judges

### Participants

| Method | Endpoint | Description | Auth Required | Role |
|--------|----------|-------------|---------------|------|
| POST | `/api/v1/hackathons/{id}/join` | Join hackathon | Yes | Any |
| POST | `/api/v1/hackathons/{id}/invite-judges` | Invite judges | Yes | ORGANIZER |
| GET | `/api/v1/hackathons/{id}/participants` | List participants | No | Any |
| DELETE | `/api/v1/hackathons/{id}/leave` | Leave hackathon | Yes | Any |

**Participant Roles:**
- `BUILDER` - Hackathon participant/competitor
- `JUDGE` - Submission judge
- `ORGANIZER` - Hackathon organizer (full permissions)
- `MENTOR` - Hackathon mentor

### Analytics

| Method | Endpoint | Description | Auth Required | Role |
|--------|----------|-------------|---------------|------|
| GET | `/api/v1/hackathons/{id}/stats` | Get hackathon statistics | Yes | ORGANIZER |
| GET | `/api/v1/hackathons/{id}/export` | Export hackathon data | Yes | ORGANIZER |

**Statistics Include:**
- Total participant count with role breakdown
- Total team count
- Total submission count with status breakdown
- Average scores per track

**Export Formats:**
- `json` - Structured JSON with nested objects
- `csv` - Flattened CSV with all records (automatically downloads as file)

## Error Handling

All errors follow a consistent JSON format:

```json
{
  "error": {
    "status_code": 400,
    "message": "Validation error",
    "details": [
      {
        "field": "end_date",
        "message": "end_date must be after start_date"
      }
    ],
    "path": "/api/v1/hackathons"
  }
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 204 | No Content | Resource deleted successfully |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource conflict (e.g., duplicate) |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |
| 504 | Gateway Timeout | Request timeout |

## Rate Limiting

API requests are rate-limited to ensure fair usage:

- **Per API Key:** 100 requests per minute
- **Per API Key:** 1000 requests per hour

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

When rate limit is exceeded:

```json
{
  "error": {
    "status_code": 429,
    "message": "Rate limit exceeded",
    "details": "Too many requests. Please try again in 60 seconds."
  }
}
```

## Example Usage

### Create Hackathon

```bash
curl -X POST http://localhost:8000/api/v1/hackathons \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AI Hackathon 2025",
    "description": "Build AI-powered applications",
    "organizer_id": "user-123",
    "start_date": "2025-03-01T09:00:00Z",
    "end_date": "2025-03-03T18:00:00Z",
    "location": "San Francisco, CA",
    "status": "draft"
  }'
```

### List Hackathons

```bash
curl -X GET "http://localhost:8000/api/v1/hackathons?status=active&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Submit Score

```bash
curl -X POST "http://localhost:8000/judging/scores?submission_id=SUB_ID&hackathon_id=HACK_ID&rubric_id=RUB_ID" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "judge_id": "judge-456",
    "criteria": "Innovation",
    "score": 28.5,
    "comment": "Excellent use of AI technology"
  }'
```

### Get Hackathon Statistics

```bash
curl -X GET "http://localhost:8000/api/v1/hackathons/HACKATHON_ID/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Export Hackathon Data (CSV)

```bash
curl -X GET "http://localhost:8000/api/v1/hackathons/HACKATHON_ID/export?format=csv" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o hackathon_export.csv
```

## Support

For questions or issues:

- **Email:** hello@ainative.studio
- **Website:** https://ainative.studio
- **Documentation:** http://localhost:8000/v1/docs

## License

MIT License - See LICENSE file for details

---

**Last Updated:** 2024-12-28
**API Version:** v1
**Status:** Active Development
