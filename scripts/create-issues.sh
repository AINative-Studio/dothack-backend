#!/bin/bash

# Epic 3: ZeroDB Tables & Core Data Layer (Stories 3.1-3.5)

gh issue create --repo AINative-Studio/dothack-backend \
  --title "[CHORE] ZeroDB table creation script" \
  --label "chore,critical,ready,backend,s" \
  --body "## Story 3.1: ZeroDB table creation script

**Epic:** Epic 3 - ZeroDB Tables & Core Data Layer
**Type:** CHORE
**Points:** 2
**Priority:** CRITICAL

## Description
Create Python script to initialize all 10 core ZeroDB tables with proper schemas.

## Tasks
- [ ] Create \`scripts/setup-zerodb-tables.py\`
- [ ] Implement table creation for all 10 tables (hackathons, tracks, participants, etc.)
- [ ] Add idempotent table creation (skip if exists)
- [ ] Add dry-run mode
- [ ] Add colored output for readability

## Tables to Create
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

## Acceptance Criteria
- [ ] All 10 tables created successfully
- [ ] Script is idempotent (can run multiple times)
- [ ] Dry-run mode shows what would be created
- [ ] Color-coded output (success=green, warning=yellow)
- [ ] Documentation in \`/docs/deployment/ZERODB_SETUP.md\`

## Testing
\`\`\`bash
# Dry run
python scripts/setup-zerodb-tables.py --dry-run

# Actual creation
python scripts/setup-zerodb-tables.py --apply

# Verify
python scripts/verify-zerodb-tables.py
\`\`\`

## Dependencies
#3

## Story Points
**2 points** (Effort: S)"

gh issue create --repo AINative-Studio/dothack-backend \
  --title "[FEATURE] Hackathon CRUD service" \
  --label "feature,high,ready,backend,m" \
  --body "## Story 3.2: Hackathon CRUD service

**Epic:** Epic 3 - ZeroDB Tables & Core Data Layer
**Type:** FEATURE
**Points:** 3
**Priority:** HIGH

## Description
Implement service layer for hackathon creation, retrieval, update, and deletion.

## Tasks
- [ ] Create \`python-api/services/hackathon_service.py\`
- [ ] Implement \`create_hackathon()\`
- [ ] Implement \`get_hackathon()\`
- [ ] Implement \`list_hackathons()\`
- [ ] Implement \`update_hackathon()\`
- [ ] Implement \`delete_hackathon()\`
- [ ] Auto-add creator as ORGANIZER in \`hackathon_participants\`

## Acceptance Criteria
- [ ] All CRUD operations working
- [ ] Creator automatically assigned as ORGANIZER
- [ ] Hackathon status validation (DRAFT, LIVE, CLOSED)
- [ ] Pagination for list endpoint
- [ ] Soft delete (mark as deleted, don't remove)

## Testing
\`\`\`python
describe(\"Hackathon Service\")
  it(\"creates hackathon with valid data\")
  it(\"adds creator as ORGANIZER\")
  it(\"validates hackathon status\")
  it(\"lists hackathons with pagination\")
  it(\"updates hackathon (ORGANIZER only)\")
  it(\"soft deletes hackathon\")
\`\`\`

## Dependencies
#3, #7, #12

## Story Points
**3 points** (Effort: M)"

gh issue create --repo AINative-Studio/dothack-backend \
  --title "[FEATURE] Team management service" \
  --label "feature,high,ready,backend,m" \
  --body "## Story 3.3: Team management service

**Epic:** Epic 3 - ZeroDB Tables & Core Data Layer
**Type:** FEATURE
**Points:** 3
**Priority:** HIGH

## Description
Implement service layer for team creation and member management.

## Tasks
- [ ] Create \`python-api/services/team_service.py\`
- [ ] Implement \`create_team()\`
- [ ] Implement \`add_team_member()\`
- [ ] Implement \`remove_team_member()\`
- [ ] Implement \`get_team()\`
- [ ] Validate max team size
- [ ] Assign team lead automatically

## Acceptance Criteria
- [ ] Teams created within hackathons
- [ ] Creator assigned as team LEAD
- [ ] Max team size enforced (default: 5)
- [ ] Members can leave teams
- [ ] Team status tracked (FORMING, ACTIVE)

## Testing
\`\`\`python
describe(\"Team Service\")
  it(\"creates team for hackathon\")
  it(\"assigns creator as team LEAD\")
  it(\"adds members to team\")
  it(\"enforces max team size\")
  it(\"removes members from team\")
  it(\"prevents duplicate members\")
\`\`\`

## Dependencies
#12, #13

## Story Points
**3 points** (Effort: M)"

gh issue create --repo AINative-Studio/dothack-backend \
  --title "[FEATURE] Project submission service" \
  --label "feature,high,ready,backend,m" \
  --body "## Story 3.4: Project submission service

**Epic:** Epic 3 - ZeroDB Tables & Core Data Layer
**Type:** FEATURE
**Points:** 3
**Priority:** HIGH

## Description
Implement service layer for project submissions with validation.

## Tasks
- [ ] Create \`python-api/services/submission_service.py\`
- [ ] Implement \`submit_project()\`
- [ ] Implement \`get_submission()\`
- [ ] Implement \`update_submission()\`
- [ ] Validate team membership
- [ ] Validate submission deadline
- [ ] Update project status to SUBMITTED

## Acceptance Criteria
- [ ] Only team members can submit
- [ ] Submission deadline enforced
- [ ] Project status updated to SUBMITTED
- [ ] Submission text stored in ZeroDB
- [ ] Artifact links validated (URLs)

## Testing
\`\`\`python
describe(\"Submission Service\")
  it(\"allows team member to submit\")
  it(\"denies non-team member submission\")
  it(\"enforces submission deadline\")
  it(\"validates artifact URLs\")
  it(\"updates project status\")
  it(\"prevents duplicate submissions\")
\`\`\`

## Dependencies
#12, #14

## Story Points
**3 points** (Effort: M)"

gh issue create --repo AINative-Studio/dothack-backend \
  --title "[FEATURE] Judging and scoring service" \
  --label "feature,high,ready,backend,m" \
  --body "## Story 3.5: Judging and scoring service

**Epic:** Epic 3 - ZeroDB Tables & Core Data Layer
**Type:** FEATURE
**Points:** 3
**Priority:** HIGH

## Description
Implement service layer for submission scoring and feedback.

## Tasks
- [ ] Create \`python-api/services/judging_service.py\`
- [ ] Implement \`score_submission()\`
- [ ] Implement \`get_scores()\`
- [ ] Implement \`calculate_leaderboard()\`
- [ ] Validate judge assignment
- [ ] Validate score ranges
- [ ] Calculate total scores

## Acceptance Criteria
- [ ] Only assigned JUDGE can score
- [ ] Score validation per rubric
- [ ] Total score calculated automatically
- [ ] Leaderboard generated from scores
- [ ] Scores immutable once submitted

## Testing
\`\`\`python
describe(\"Judging Service\")
  it(\"allows assigned JUDGE to score\")
  it(\"denies non-judge from scoring\")
  it(\"validates score ranges\")
  it(\"calculates total score\")
  it(\"generates leaderboard\")
  it(\"prevents score modification after submit\")
\`\`\`

## Dependencies
#12, #15

## Story Points
**3 points** (Effort: M)"

echo "✅ Epic 3 issues created successfully!"
