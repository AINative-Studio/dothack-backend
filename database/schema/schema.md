# Database Schema - AI-Native Hackathon Platform

> Source: PRD.md Section 5 - Data Model (Tables)
>
> All structured data stored using ZeroDB Tables API

---

## Tables Overview

The platform uses 10 tables to manage hackathon operations:

1. **hackathons** - Core hackathon metadata
2. **tracks** - Hackathon tracks/categories
3. **participants** - User registry
4. **hackathon_participants** - Join table for hackathon enrollment
5. **teams** - Team records
6. **team_members** - Team membership
7. **projects** - Project metadata
8. **submissions** - Final submissions
9. **rubrics** - Judging criteria
10. **scores** - Judge scores and feedback

---

## Table Schemas

### 1. hackathons

Core hackathon metadata and lifecycle management.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `hackathon_id` | UUID | PRIMARY KEY | Unique hackathon identifier |
| `name` | TEXT | NOT NULL | Hackathon name |
| `description` | TEXT | NOT NULL | Hackathon description |
| `status` | TEXT | NOT NULL | Lifecycle status: `DRAFT`, `LIVE`, `CLOSED` |
| `start_at` | TIMESTAMP | NOT NULL | Hackathon start time |
| `end_at` | TIMESTAMP | NOT NULL | Hackathon end time |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Record creation timestamp |

**Status Transitions:**
- `DRAFT` → `LIVE` → `CLOSED`

---

### 2. tracks

Hackathon tracks/categories for organizing projects.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `track_id` | UUID | PRIMARY KEY | Unique track identifier |
| `hackathon_id` | UUID | NOT NULL | Foreign key to hackathons |
| `name` | TEXT | NOT NULL | Track name |
| `description` | TEXT | | Track description |

**Relationships:**
- Many tracks per hackathon
- Projects can be assigned to one track

---

### 3. participants

Registry of all participants across all hackathons.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `participant_id` | UUID | PRIMARY KEY | Unique participant identifier |
| `name` | TEXT | NOT NULL | Participant full name |
| `email` | TEXT | UNIQUE, NOT NULL | Participant email |
| `org` | TEXT | NULLABLE | Organization/affiliation |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Record creation timestamp |

**Constraints:**
- Email must be unique across all participants

---

### 4. hackathon_participants

Join table mapping participants to hackathons with roles.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `hackathon_id` | UUID | NOT NULL | Foreign key to hackathons |
| `participant_id` | UUID | NOT NULL | Foreign key to participants |
| `role` | TEXT | NOT NULL | Participant role in hackathon |

**Valid Roles:**
- `BUILDER` - Team member/participant
- `ORGANIZER` - Hackathon organizer
- `JUDGE` - Submission evaluator
- `MENTOR` - Team advisor

**Composite Key:**
- (`hackathon_id`, `participant_id`)

---

### 5. teams

Team records for hackathon collaboration.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `team_id` | UUID | PRIMARY KEY | Unique team identifier |
| `hackathon_id` | UUID | NOT NULL | Foreign key to hackathons |
| `name` | TEXT | NOT NULL | Team name |
| `track_id` | UUID | NULLABLE | Foreign key to tracks (optional) |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Record creation timestamp |

**Relationships:**
- One team belongs to one hackathon
- Team can optionally be assigned to a track

---

### 6. team_members

Team membership records with roles.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `team_id` | UUID | NOT NULL | Foreign key to teams |
| `participant_id` | UUID | NOT NULL | Foreign key to participants |
| `role` | TEXT | NOT NULL | Member role in team |

**Valid Roles:**
- `LEAD` - Team leader
- `MEMBER` - Team member

**Composite Key:**
- (`team_id`, `participant_id`)

---

### 7. projects

Project metadata and tracking.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `project_id` | UUID | PRIMARY KEY | Unique project identifier |
| `hackathon_id` | UUID | NOT NULL | Foreign key to hackathons |
| `team_id` | UUID | NOT NULL | Foreign key to teams |
| `title` | TEXT | NOT NULL | Project title |
| `one_liner` | TEXT | | Short project description |
| `status` | TEXT | NOT NULL | Project status |
| `repo_url` | TEXT | NULLABLE | Repository URL |
| `demo_url` | TEXT | NULLABLE | Demo/deployment URL |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Record creation timestamp |

**Valid Statuses:**
- `IDEA` - Initial concept
- `BUILDING` - Development in progress
- `SUBMITTED` - Final submission complete

**Status Transitions:**
- `IDEA` → `BUILDING` → `SUBMITTED`

---

### 8. submissions

Final project submissions with narrative and artifacts.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `submission_id` | UUID | PRIMARY KEY | Unique submission identifier |
| `project_id` | UUID | NOT NULL | Foreign key to projects |
| `submitted_at` | TIMESTAMP | NOT NULL | Submission timestamp |
| `submission_text` | TEXT | NOT NULL | Canonical submission narrative |
| `artifact_links_json` | TEXT | | JSON string of artifact links |
| `namespace` | TEXT | NOT NULL | Embeddings namespace |

**Embeddings Integration:**
- `namespace` format: `hackathons/{hackathon_id}/submissions`
- Submission text is embedded using BAAI/bge-small-en-v1.5 (384 dimensions)
- Document ID: `submission:{submission_id}`

**Artifact Links JSON Format:**
```json
{
  "demo_video": "https://...",
  "slides": "https://...",
  "additional": ["https://..."]
}
```

---

### 9. rubrics

Judging criteria and weights for hackathons.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `rubric_id` | UUID | PRIMARY KEY | Unique rubric identifier |
| `hackathon_id` | UUID | NOT NULL | Foreign key to hackathons |
| `title` | TEXT | NOT NULL | Rubric title |
| `criteria_json` | TEXT | NOT NULL | JSON string of criteria with weights |

**Criteria JSON Format:**
```json
{
  "innovation": {
    "weight": 0.3,
    "description": "Originality and creativity",
    "max_score": 10
  },
  "technical_execution": {
    "weight": 0.3,
    "description": "Code quality and implementation",
    "max_score": 10
  },
  "impact": {
    "weight": 0.2,
    "description": "Potential real-world impact",
    "max_score": 10
  },
  "presentation": {
    "weight": 0.2,
    "description": "Clarity of communication",
    "max_score": 10
  }
}
```

**Relationships:**
- One rubric per hackathon (typically)

---

### 10. scores

Judge scores and feedback for submissions.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `score_id` | UUID | PRIMARY KEY | Unique score identifier |
| `submission_id` | UUID | NOT NULL | Foreign key to submissions |
| `judge_participant_id` | UUID | NOT NULL | Foreign key to participants (judge) |
| `score_json` | TEXT | NOT NULL | JSON string of per-criteria scores |
| `total_score` | REAL | NOT NULL | Calculated total score |
| `feedback` | TEXT | | Judge feedback text |

**Score JSON Format:**
```json
{
  "innovation": 8,
  "technical_execution": 7,
  "impact": 9,
  "presentation": 8
}
```

**Total Score Calculation:**
```
total_score = weighted average based on rubric criteria weights
```

**Constraints:**
- One score per (submission, judge) pair
- Composite unique: (`submission_id`, `judge_participant_id`)

---

## API Constraints (Critical)

From PRD Section 0 - Non-Negotiables:

### Table Operations

**Create Table:**
```
POST /{project_id}/database/tables
```

**Insert Row:**
```
POST /{project_id}/database/tables/{table_name}/rows
```

**Body Format:**
```json
{
  "row_data": {
    "field1": "value1",
    "field2": "value2"
  }
}
```

**List Rows:**
```
GET /{project_id}/database/tables/{table_name}/rows?limit=100&offset=0
```

### Embeddings Operations

**Model:** `BAAI/bge-small-en-v1.5`
**Dimensions:** 384
**Endpoint:** `POST /{project_id}/embeddings/embed-and-store`

---

## Data Model Notes

1. **UUID Generation**: Client-side UUID generation for primary keys
2. **JSON Storage**: Use TEXT fields with JSON.stringify() for complex data
3. **Timestamps**: Use ISO 8601 format
4. **Append-Only Pattern**: No row updates in MVP (status changes via new rows)
5. **Namespaces**: Strict format for embeddings isolation

---

## Entity Relationships

```
hackathons
├── tracks (1:N)
├── hackathon_participants (1:N)
│   └── participants (N:1)
├── teams (1:N)
│   ├── team_members (1:N)
│   │   └── participants (N:1)
│   └── projects (1:N)
│       └── submissions (1:1)
│           └── scores (1:N)
│               └── participants (judges) (N:1)
└── rubrics (1:1)
```

---

## Setup Checklist

- [ ] Create ZeroDB project with `database_enabled: true`
- [ ] Create all 10 tables via API
- [ ] Validate table schemas match this specification
- [ ] Test insert operations with `row_data` format
- [ ] Configure embeddings namespace pattern
- [ ] Set up API authentication (X-API-Key header)

---

## Related Documentation

- **PRD**: Section 5 (Data Model), Section 8 (API Mapping)
- **Frontend PRD**: Section 3 (Screen Inventory)
- **Backlog**: All FE-* stories map to these tables
- **GitHub Issues**: #7-#16 (Table API Integration)
