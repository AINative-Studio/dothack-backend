/**
 * TypeScript Type Definitions for Database Schema
 *
 * Source: PRD.md Section 5 - Data Model
 *
 * These types match the ZeroDB table schemas exactly.
 * Use these types for type-safe API interactions.
 */

// ============================================================================
// Core Types
// ============================================================================

export type UUID = string;
export type Timestamp = string; // ISO 8601 format

// ============================================================================
// Enum Types
// ============================================================================

export enum HackathonStatus {
  DRAFT = 'DRAFT',
  LIVE = 'LIVE',
  CLOSED = 'CLOSED',
}

export enum ParticipantRole {
  BUILDER = 'BUILDER',
  ORGANIZER = 'ORGANIZER',
  JUDGE = 'JUDGE',
  MENTOR = 'MENTOR',
}

export enum TeamMemberRole {
  LEAD = 'LEAD',
  MEMBER = 'MEMBER',
}

export enum ProjectStatus {
  IDEA = 'IDEA',
  BUILDING = 'BUILDING',
  SUBMITTED = 'SUBMITTED',
}

// ============================================================================
// Table Row Types
// ============================================================================

/**
 * Hackathon
 * Core hackathon metadata and lifecycle management
 */
export interface Hackathon {
  hackathon_id: UUID;
  name: string;
  description: string;
  status: HackathonStatus;
  start_at: Timestamp;
  end_at: Timestamp;
  created_at: Timestamp;
}

/**
 * Track
 * Hackathon tracks/categories for organizing projects
 */
export interface Track {
  track_id: UUID;
  hackathon_id: UUID;
  name: string;
  description: string;
}

/**
 * Participant
 * Registry of all participants across all hackathons
 */
export interface Participant {
  participant_id: UUID;
  name: string;
  email: string;
  org: string | null;
  created_at: Timestamp;
}

/**
 * Hackathon Participant (Join Table)
 * Maps participants to hackathons with roles
 */
export interface HackathonParticipant {
  hackathon_id: UUID;
  participant_id: UUID;
  role: ParticipantRole;
}

/**
 * Team
 * Team records for hackathon collaboration
 */
export interface Team {
  team_id: UUID;
  hackathon_id: UUID;
  name: string;
  track_id: UUID | null;
  created_at: Timestamp;
}

/**
 * Team Member
 * Team membership records with roles
 */
export interface TeamMember {
  team_id: UUID;
  participant_id: UUID;
  role: TeamMemberRole;
}

/**
 * Project
 * Project metadata and tracking
 */
export interface Project {
  project_id: UUID;
  hackathon_id: UUID;
  team_id: UUID;
  title: string;
  one_liner: string;
  status: ProjectStatus;
  repo_url: string | null;
  demo_url: string | null;
  created_at: Timestamp;
}

/**
 * Submission
 * Final project submissions with narrative and artifacts
 */
export interface Submission {
  submission_id: UUID;
  project_id: UUID;
  submitted_at: Timestamp;
  submission_text: string;
  artifact_links_json: string; // JSON stringified ArtifactLinks
  namespace: string; // Format: hackathons/{hackathon_id}/submissions
}

/**
 * Rubric
 * Judging criteria and weights for hackathons
 */
export interface Rubric {
  rubric_id: UUID;
  hackathon_id: UUID;
  title: string;
  criteria_json: string; // JSON stringified RubricCriteria
}

/**
 * Score
 * Judge scores and feedback for submissions
 */
export interface Score {
  score_id: UUID;
  submission_id: UUID;
  judge_participant_id: UUID;
  score_json: string; // JSON stringified CriteriaScores
  total_score: number;
  feedback: string;
}

// ============================================================================
// JSON Field Types (Parsed)
// ============================================================================

/**
 * Artifact Links
 * Structure for submission artifact_links_json field
 */
export interface ArtifactLinks {
  demo_video?: string;
  slides?: string;
  additional?: string[];
  [key: string]: string | string[] | undefined;
}

/**
 * Rubric Criterion
 * Single criterion definition
 */
export interface RubricCriterion {
  weight: number;
  description: string;
  max_score: number;
}

/**
 * Rubric Criteria
 * Structure for rubric criteria_json field
 */
export interface RubricCriteria {
  [criterionKey: string]: RubricCriterion;
}

/**
 * Criteria Scores
 * Structure for score score_json field
 */
export interface CriteriaScores {
  [criterionKey: string]: number;
}

// ============================================================================
// API Request Types
// ============================================================================

/**
 * Generic table insert request
 * All table inserts must use this structure
 */
export interface TableInsertRequest<T> {
  row_data: T;
}

/**
 * Table list query parameters
 */
export interface TableListParams {
  limit?: number;
  offset?: number;
  filter?: Record<string, unknown>;
}

/**
 * Embed-and-Store Document
 */
export interface EmbeddingDocument {
  id: string; // Format: submission:{submission_id}
  text: string;
  metadata: {
    hackathon_id: UUID;
    track_id?: UUID;
    team_id: UUID;
    project_id: UUID;
    submitted_at: Timestamp;
    [key: string]: unknown;
  };
}

/**
 * Embed-and-Store Request
 */
export interface EmbedAndStoreRequest {
  documents: EmbeddingDocument[];
  namespace: string; // Format: hackathons/{hackathon_id}/submissions
}

/**
 * Semantic Search Request
 */
export interface SemanticSearchRequest {
  query: string;
  namespace: string;
  limit?: number;
  similarity_threshold?: number;
  filter?: {
    track_id?: UUID;
    team_id?: UUID;
    [key: string]: unknown;
  };
}

// ============================================================================
// Create (Insert) Types
// ============================================================================

export type CreateHackathon = Omit<Hackathon, 'created_at'>;
export type CreateTrack = Track;
export type CreateParticipant = Omit<Participant, 'created_at'>;
export type CreateHackathonParticipant = HackathonParticipant;
export type CreateTeam = Omit<Team, 'created_at'>;
export type CreateTeamMember = TeamMember;
export type CreateProject = Omit<Project, 'created_at'>;
export type CreateSubmission = Submission;
export type CreateRubric = Rubric;
export type CreateScore = Score;

// ============================================================================
// Utility Types
// ============================================================================

/**
 * API Response wrapper
 */
export interface APIResponse<T> {
  data: T;
  error?: string;
}

/**
 * Paginated response
 */
export interface PaginatedResponse<T> {
  data: T[];
  total?: number;
  limit: number;
  offset: number;
}

/**
 * Namespace utilities
 */
export const EmbeddingNamespace = {
  submissions: (hackathonId: UUID): string =>
    `hackathons/${hackathonId}/submissions`,
  projects: (hackathonId: UUID): string =>
    `hackathons/${hackathonId}/projects`,
  judging: (hackathonId: UUID): string =>
    `hackathons/${hackathonId}/judging`,
} as const;

/**
 * Document ID utilities
 */
export const DocumentId = {
  submission: (submissionId: UUID): string => `submission:${submissionId}`,
  project: (projectId: UUID): string => `project:${projectId}`,
} as const;

// ============================================================================
// Validation Constants
// ============================================================================

export const API_CONSTANTS = {
  EMBEDDING_MODEL: 'BAAI/bge-small-en-v1.5',
  EMBEDDING_DIMENSIONS: 384,
  BASE_URL: 'https://api.ainative.studio/v1/public',
  DEFAULT_LIMIT: 100,
  MAX_LIMIT: 100,
} as const;

// ============================================================================
// Type Guards
// ============================================================================

export function isHackathonStatus(status: string): status is HackathonStatus {
  return Object.values(HackathonStatus).includes(status as HackathonStatus);
}

export function isParticipantRole(role: string): role is ParticipantRole {
  return Object.values(ParticipantRole).includes(role as ParticipantRole);
}

export function isTeamMemberRole(role: string): role is TeamMemberRole {
  return Object.values(TeamMemberRole).includes(role as TeamMemberRole);
}

export function isProjectStatus(status: string): status is ProjectStatus {
  return Object.values(ProjectStatus).includes(status as ProjectStatus);
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Parse JSON field safely
 */
export function parseJSONField<T>(jsonString: string): T | null {
  try {
    return JSON.parse(jsonString) as T;
  } catch {
    return null;
  }
}

/**
 * Stringify for JSON field
 */
export function stringifyJSONField<T>(data: T): string {
  return JSON.stringify(data);
}

/**
 * Calculate total score from criteria scores
 */
export function calculateTotalScore(
  scores: CriteriaScores,
  criteria: RubricCriteria
): number {
  let totalWeightedScore = 0;
  let totalWeight = 0;

  for (const [key, criterion] of Object.entries(criteria)) {
    const score = scores[key];
    if (score !== undefined) {
      totalWeightedScore += score * criterion.weight;
      totalWeight += criterion.weight;
    }
  }

  return totalWeight > 0 ? totalWeightedScore / totalWeight : 0;
}

/**
 * Validate UUID format
 */
export function isValidUUID(uuid: string): boolean {
  const uuidRegex =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(uuid);
}

/**
 * Generate namespace for embeddings
 */
export function generateSubmissionNamespace(hackathonId: UUID): string {
  if (!isValidUUID(hackathonId)) {
    throw new Error(`Invalid hackathon UUID: ${hackathonId}`);
  }
  return EmbeddingNamespace.submissions(hackathonId);
}

/**
 * Generate document ID for submission
 */
export function generateSubmissionDocumentId(submissionId: UUID): string {
  if (!isValidUUID(submissionId)) {
    throw new Error(`Invalid submission UUID: ${submissionId}`);
  }
  return DocumentId.submission(submissionId);
}
