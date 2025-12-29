"""
Submission API Endpoints

RESTful API for managing hackathon project submissions.
Provides CRUD operations and file upload functionality.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from api.dependencies import get_current_user
from api.schemas.submission import (
    ErrorResponse,
    FileMetadata,
    FileUploadRequest,
    FileUploadResponse,
    SimilarSubmissionItem,
    SimilarSubmissionsResponse,
    SubmissionCreateRequest,
    SubmissionListResponse,
    SubmissionResponse,
    SubmissionUpdateRequest,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from integrations.zerodb.client import ZeroDBClient
from services.submission_service import (
    create_submission,
    delete_submission,
    find_similar_submissions,
    get_submission,
    list_submissions,
    update_submission,
    upload_file_to_submission,
)

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/v1/submissions", tags=["Submissions"])


def get_zerodb_client() -> ZeroDBClient:
    """
    Dependency to get ZeroDB client instance.

    Returns:
        Configured ZeroDBClient instance

    Example:
        >>> @router.post("/submissions")
        >>> async def create(
        ...     client: ZeroDBClient = Depends(get_zerodb_client)
        ... ):
        ...     # Use client for database operations
        ...     pass
    """
    from config import settings

    return ZeroDBClient(
        api_key=settings.ZERODB_API_KEY,
        project_id=settings.ZERODB_PROJECT_ID,
        base_url=settings.ZERODB_BASE_URL,
        timeout=settings.ZERODB_TIMEOUT,
    )


@router.post(
    "",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new submission",
    description="Create a new hackathon project submission. Submission starts in DRAFT status.",
    responses={
        201: {
            "description": "Submission created successfully",
            "model": SubmissionResponse,
        },
        400: {
            "description": "Invalid request data",
            "model": ErrorResponse,
        },
        401: {
            "description": "Unauthorized - invalid or missing authentication",
            "model": ErrorResponse,
        },
        404: {
            "description": "Team or hackathon not found",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def create_submission_endpoint(
    submission_data: SubmissionCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> SubmissionResponse:
    """
    Create a new submission.

    Creates a new project submission for a hackathon with DRAFT status.
    Files can be uploaded separately using the file upload endpoint.

    Args:
        submission_data: Submission details (team_id, project info, URLs)
        current_user: Authenticated user from JWT/API key
        zerodb_client: ZeroDB client instance

    Returns:
        Created submission details

    Example Request:
        ```json
        {
            "team_id": "550e8400-e29b-41d4-a716-446655440000",
            "hackathon_id": "660e8400-e29b-41d4-a716-446655440001",
            "project_name": "AI Code Assistant",
            "description": "An intelligent code completion tool...",
            "repository_url": "https://github.com/team/project",
            "demo_url": "https://demo.example.com"
        }
        ```
    """
    try:
        logger.info(
            f"User {current_user.get('id')} creating submission for "
            f"team {submission_data.team_id}"
        )

        submission = await create_submission(
            zerodb_client=zerodb_client,
            team_id=str(submission_data.team_id),
            hackathon_id=str(submission_data.hackathon_id),
            project_name=submission_data.project_name,
            description=submission_data.description,
            repository_url=submission_data.repository_url,
            demo_url=submission_data.demo_url,
            video_url=submission_data.video_url,
            files=[file.model_dump() for file in submission_data.files] if submission_data.files else [],
        )

        return SubmissionResponse(**submission)

    except ValueError as e:
        logger.warning(f"Validation error creating submission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "",
    response_model=SubmissionListResponse,
    summary="List submissions",
    description="List submissions with optional filters (hackathon, team, status).",
    responses={
        200: {
            "description": "List of submissions",
            "model": SubmissionListResponse,
        },
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def list_submissions_endpoint(
    hackathon_id: Optional[UUID] = Query(None, description="Filter by hackathon ID"),
    team_id: Optional[UUID] = Query(None, description="Filter by team ID"),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by status (DRAFT, SUBMITTED, SCORED)"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip (pagination)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> SubmissionListResponse:
    """
    List submissions with filters.

    Retrieve a list of submissions with optional filtering by hackathon,
    team, or status. Supports pagination.

    Args:
        hackathon_id: Optional hackathon ID filter
        team_id: Optional team ID filter
        status_filter: Optional status filter (DRAFT, SUBMITTED, SCORED)
        skip: Pagination offset
        limit: Maximum number of results
        current_user: Authenticated user
        zerodb_client: ZeroDB client instance

    Returns:
        Paginated list of submissions

    Example Query:
        ```
        GET /v1/submissions?hackathon_id=660e8400-e29b-41d4-a716-446655440001&status=SUBMITTED&limit=20
        ```
    """
    try:
        logger.info(
            f"User {current_user.get('id')} listing submissions "
            f"(hackathon: {hackathon_id}, team: {team_id}, status: {status_filter})"
        )

        # Validate status if provided
        if status_filter and status_filter not in ["DRAFT", "SUBMITTED", "SCORED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status. Must be 'DRAFT', 'SUBMITTED', or 'SCORED'",
            )

        submissions = await list_submissions(
            zerodb_client=zerodb_client,
            requester_id=str(current_user.get("id")),
            hackathon_id=str(hackathon_id) if hackathon_id else None,
            team_id=str(team_id) if team_id else None,
            status=status_filter,  # type: ignore
            skip=skip,
            limit=limit,
        )

        return SubmissionListResponse(
            submissions=[SubmissionResponse(**sub) for sub in submissions],
            total=len(submissions),
            skip=skip,
            limit=limit,
        )

    except HTTPException:
        raise


@router.get(
    "/{submission_id}",
    response_model=SubmissionResponse,
    summary="Get submission details",
    description="Retrieve detailed information about a specific submission.",
    responses={
        200: {
            "description": "Submission details",
            "model": SubmissionResponse,
        },
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        },
        404: {
            "description": "Submission not found",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def get_submission_endpoint(
    submission_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> SubmissionResponse:
    """
    Get submission by ID.

    Retrieves detailed information about a specific submission including
    all metadata, URLs, files, and status.

    Args:
        submission_id: UUID of the submission
        current_user: Authenticated user
        zerodb_client: ZeroDB client instance

    Returns:
        Submission details

    Example:
        ```
        GET /v1/submissions/550e8400-e29b-41d4-a716-446655440000
        ```
    """
    try:
        logger.info(
            f"User {current_user.get('id')} retrieving submission {submission_id}"
        )

        submission = await get_submission(
            zerodb_client=zerodb_client,
            submission_id=str(submission_id),
            requester_id=str(current_user.get("id")),
        )

        return SubmissionResponse(**submission)

    except HTTPException:
        raise


@router.put(
    "/{submission_id}",
    response_model=SubmissionResponse,
    summary="Update submission",
    description="Update an existing submission's details. Only provided fields will be updated.",
    responses={
        200: {
            "description": "Submission updated successfully",
            "model": SubmissionResponse,
        },
        400: {
            "description": "Invalid request data",
            "model": ErrorResponse,
        },
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        },
        404: {
            "description": "Submission not found",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def update_submission_endpoint(
    submission_id: UUID,
    update_data: SubmissionUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> SubmissionResponse:
    """
    Update submission.

    Updates an existing submission with new information. Only fields
    provided in the request will be updated (partial update).

    Args:
        submission_id: UUID of the submission to update
        update_data: Fields to update
        current_user: Authenticated user
        zerodb_client: ZeroDB client instance

    Returns:
        Updated submission details

    Example Request:
        ```json
        {
            "project_name": "Updated Project Name",
            "status": "SUBMITTED"
        }
        ```
    """
    try:
        logger.info(
            f"User {current_user.get('id')} updating submission {submission_id}"
        )

        submission = await update_submission(
            zerodb_client=zerodb_client,
            submission_id=str(submission_id),
            requester_id=str(current_user.get("id")),
            project_name=update_data.project_name,
            description=update_data.description,
            repository_url=update_data.repository_url,
            demo_url=update_data.demo_url,
            video_url=update_data.video_url,
            status=update_data.status,
            files=[file.model_dump() for file in update_data.files] if update_data.files else None,
        )

        return SubmissionResponse(**submission)

    except ValueError as e:
        logger.warning(f"Validation error updating submission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise


@router.delete(
    "/{submission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete submission",
    description="Delete a submission. Cannot delete submissions that have been scored.",
    responses={
        204: {
            "description": "Submission deleted successfully",
        },
        400: {
            "description": "Cannot delete scored submission",
            "model": ErrorResponse,
        },
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        },
        404: {
            "description": "Submission not found",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def delete_submission_endpoint(
    submission_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> None:
    """
    Delete submission.

    Deletes a submission. SCORED submissions cannot be deleted to maintain
    judging integrity.

    Args:
        submission_id: UUID of the submission to delete
        current_user: Authenticated user
        zerodb_client: ZeroDB client instance

    Example:
        ```
        DELETE /v1/submissions/550e8400-e29b-41d4-a716-446655440000
        ```
    """
    try:
        logger.info(
            f"User {current_user.get('id')} deleting submission {submission_id}"
        )

        await delete_submission(
            zerodb_client=zerodb_client,
            submission_id=str(submission_id),
            requester_id=str(current_user.get("id")),
        )

    except HTTPException:
        raise


@router.post(
    "/{submission_id}/files",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload file to submission",
    description="Upload a file (PDF, images, etc.) to a submission.",
    responses={
        201: {
            "description": "File uploaded successfully",
            "model": FileUploadResponse,
        },
        400: {
            "description": "Invalid file data",
            "model": ErrorResponse,
        },
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        },
        404: {
            "description": "Submission not found",
            "model": ErrorResponse,
        },
        413: {
            "description": "File too large (max 100MB)",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def upload_file_endpoint(
    submission_id: UUID,
    file_data: FileUploadRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> FileUploadResponse:
    """
    Upload file to submission.

    Uploads a file (base64-encoded) to the submission. Files are stored
    in ZeroDB file storage and metadata is attached to the submission.

    Args:
        submission_id: UUID of the submission
        file_data: File information (name, type, size, base64 content)
        current_user: Authenticated user
        zerodb_client: ZeroDB client instance

    Returns:
        File upload details including URL

    Example Request:
        ```json
        {
            "file_name": "presentation.pdf",
            "file_type": "application/pdf",
            "file_size": 2048576,
            "file_content": "JVBERi0xLjQKJeLjz9MKMSAwIG9ia..."
        }
        ```

    Note:
        - Maximum file size: 100MB
        - File content must be base64-encoded
        - Supported MIME types: All standard types
    """
    try:
        logger.info(
            f"User {current_user.get('id')} uploading file {file_data.file_name} "
            f"to submission {submission_id}"
        )

        file_metadata = await upload_file_to_submission(
            zerodb_client=zerodb_client,
            submission_id=str(submission_id),
            file_name=file_data.file_name,
            file_content=file_data.file_content,
            file_type=file_data.file_type,
            file_size=file_data.file_size,
            requester_id=str(current_user.get("id")),
        )

        return FileUploadResponse(**file_metadata)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error uploading file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file. Please contact support.",
        )


@router.get(
    "/{submission_id}/similar",
    response_model=SimilarSubmissionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Find similar submissions",
    description="Find submissions similar to the given submission using semantic search",
    responses={
        200: {
            "description": "Similar submissions found successfully",
            "model": SimilarSubmissionsResponse,
        },
        404: {
            "description": "Submission not found",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def get_similar_submissions(
    submission_id: UUID,
    top_k: int = Query(
        10,
        ge=1,
        le=50,
        description="Maximum number of similar submissions to return",
    ),
    similarity_threshold: float = Query(
        0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0.0-1.0)",
    ),
    same_hackathon_only: bool = Query(
        True,
        description="If true, only return submissions from the same hackathon",
    ),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> SimilarSubmissionsResponse:
    """
    Find submissions similar to the given submission.

    Uses semantic search to find submissions with similar project descriptions
    and content based on AI-powered vector similarity.

    **Path Parameters:**
    - submission_id: UUID of the submission to find similar submissions for

    **Query Parameters:**
    - top_k: Maximum number of results (1-50, default: 10)
    - similarity_threshold: Minimum similarity score 0.0-1.0 (default: 0.5)
    - same_hackathon_only: Only search within same hackathon (default: true)

    **Returns:**
    List of similar submissions sorted by relevance (highest similarity score first).
    Each result includes:
    - Full submission details
    - Similarity score (0.0-1.0, higher is more similar)
    - Execution time metrics

    **Use Cases:**
    - Discover related projects
    - Find duplicate submissions
    - Explore similar ideas within a hackathon
    - Content recommendation

    **Performance:**
    Typical response time: < 300ms

    **Note:**
    - The query submission itself is excluded from results
    - Results are ranked by similarity score (descending)
    - Only returns submissions that meet the similarity threshold
    """
    try:
        logger.info(
            f"Finding similar submissions for {submission_id} "
            f"(top_k={top_k}, threshold={similarity_threshold}, "
            f"same_hackathon={same_hackathon_only})"
        )

        result = await find_similar_submissions(
            zerodb_client=zerodb_client,
            submission_id=str(submission_id),
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            same_hackathon_only=same_hackathon_only,
        )

        # Transform results to response schema
        similar_items = [
            SimilarSubmissionItem(**submission)
            for submission in result["similar_submissions"]
        ]

        return SimilarSubmissionsResponse(
            submission_id=result["submission_id"],
            similar_submissions=similar_items,
            total_found=result["total_found"],
            execution_time_ms=result.get("execution_time_ms"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error finding similar submissions: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find similar submissions. Please contact support.",
        )
