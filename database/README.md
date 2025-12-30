# Backend Documentation

This directory contains backend-related documentation and schema definitions for the AI-Native Hackathon Platform.

## Directory Structure

```
backend/
├── database/
│   ├── schema.md          # Complete database schema documentation
│   └── schema.types.ts    # TypeScript type definitions
└── README.md              # This file
```

## Database Schema

### Schema Documentation (`database/schema.md`)

Complete reference for all 10 database tables:
- Hackathons
- Tracks
- Participants
- Hackathon Participants
- Teams
- Team Members
- Projects
- Submissions
- Rubrics
- Scores

Includes:
- Field definitions with types and constraints
- Entity relationships
- API constraints and requirements
- JSON field formats
- Setup checklist

### TypeScript Types (`database/schema.types.ts`)

Type-safe interfaces for all database entities:

**Key Features:**
- Enum types for status values and roles
- Table row interfaces matching exact schema
- Parsed JSON field types
- API request/response types
- Helper functions and type guards
- Validation utilities

**Usage Example:**

```typescript
import {
  Hackathon,
  CreateHackathon,
  HackathonStatus,
  TableInsertRequest,
  EmbeddingNamespace,
  isValidUUID,
} from '@/backend/database/schema.types';

// Create a hackathon
const newHackathon: CreateHackathon = {
  hackathon_id: crypto.randomUUID(),
  name: 'AI Builders Hackathon',
  description: 'Build AI-powered tools',
  status: HackathonStatus.DRAFT,
  start_at: new Date('2025-02-01').toISOString(),
  end_at: new Date('2025-02-15').toISOString(),
};

// Prepare API request
const request: TableInsertRequest<CreateHackathon> = {
  row_data: newHackathon,
};

// Generate embeddings namespace
const namespace = EmbeddingNamespace.submissions(newHackathon.hackathon_id);
// Result: "hackathons/{uuid}/submissions"
```

## API Integration

### Base URL
```
https://api.ainative.studio/v1/public
```

### Authentication
All requests require `X-API-Key` header:
```typescript
headers: {
  'X-API-Key': process.env.ZERODB_API_KEY,
  'Content-Type': 'application/json'
}
```

### Table Operations

**Create Table:**
```typescript
POST /{project_id}/database/tables
```

**Insert Row:**
```typescript
POST /{project_id}/database/tables/{table_name}/rows
Body: { "row_data": { ...fields } }
```

**List Rows:**
```typescript
GET /{project_id}/database/tables/{table_name}/rows?limit=100&offset=0
```

### Embeddings Operations

**Embed and Store:**
```typescript
POST /{project_id}/embeddings/embed-and-store
Body: {
  "documents": [{
    "id": "submission:{uuid}",
    "text": "...",
    "metadata": { ... }
  }],
  "namespace": "hackathons/{uuid}/submissions"
}
```

**Search:**
```typescript
POST /{project_id}/embeddings/search
Body: {
  "query": "...",
  "namespace": "hackathons/{uuid}/submissions",
  "limit": 10,
  "similarity_threshold": 0.7
}
```

## Critical Constraints

From PRD Section 0 - Non-Negotiables:

### Embeddings
- **Model**: MUST use `BAAI/bge-small-en-v1.5`
- **Dimensions**: MUST be 384
- **Vector endpoints**: MUST include `/database/` prefix

### Tables
- **Insert body**: MUST use `row_data` field
- **Project ID**: MUST be valid UUID in path
- **Auth**: MUST send `X-API-Key` header

### Namespaces
Format: `hackathons/{hackathon_id}/submissions`

## Related Documentation

- **PRD** (`/prd.md`) - Complete product requirements
- **Frontend PRD** (`/frontendprd.md`) - Frontend specifications
- **Backlog** (`/backlog.md`) - Feature backlog
- **GitHub Issues** - #7-#29 for API integration tasks

## Setup Steps

1. **Create ZeroDB Project**
   ```bash
   curl -X POST https://api.ainative.studio/v1/public/projects \
     -H "X-API-Key: $ZERODB_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"name": "hackathon-platform", "database_enabled": true}'
   ```

2. **Create All Tables**
   - Use schema definitions from `database/schema.md`
   - Create each table via `POST /{project_id}/database/tables`

3. **Configure Frontend**
   ```env
   NEXT_PUBLIC_ZERODB_PROJECT_ID=<project_uuid>
   ZERODB_API_KEY=<api_key>
   ```

4. **Implement API Client**
   - See Issue #1: Create API Client for Backend Integration
   - Use types from `schema.types.ts`

## Contributing

When modifying schema:
1. Update `schema.md` documentation
2. Update `schema.types.ts` TypeScript types
3. Update this README if adding new files
4. Run type checks: `npm run type-check`
5. Update related GitHub issues

## Support

For questions or issues:
- Review PRD and Frontend PRD documentation
- Check GitHub issues (#7-#29) for API integration
- Consult ZeroDB Platform Developer Guide
