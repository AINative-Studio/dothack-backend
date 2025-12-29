"""
Submission Management Service

Provides submission CRUD operations and file handling for hackathon projects.
Uses ZeroDB tables API for data persistence and ZeroDB files API for file storage.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import HTTPException
from fastapi import status as http_status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)

# Configure logger
logger = logging.getLogger(__name__)

# Type for valid submission status
SubmissionStatus = Literal["DRAFT", "SUBMITTED", "SCORED"]


async def create_submission(
    zerodb_client: ZeroDBClient,
    team_id: str,
    hackathon_id: str,
    project_name: str,
    description: str,
    repository_url: Optional[str] = None,
    demo_url: Optional[str] = None,
    video_url: Optional[str] = None,
    files: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Create a new submission for a hackathon.

    Submission starts in DRAFT status.

    Args:
        zerodb_client: ZeroDB client instance
        team_id: Team ID making the submission
        hackathon_id: Hackathon ID
        project_name: Project name (required, non-empty)
        description: Project description (required, non-empty)
        repository_url: Optional Git repository URL
        demo_url: Optional live demo URL
        video_url: Optional demo video URL
        files: Optional list of file metadata

    Returns:
        Dict with submission details including submission_id

    Raises:
        ValueError: If required fields are empty or invalid
        HTTPException: 404 if team not found
        HTTPException: 500 if database error occurs

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> submission = await create_submission(
        ...     client,
        ...     team_id="team-123",
        ...     hackathon_id="hack-456",
        ...     project_name="Awesome Project",
        ...     description="This project is amazing..."
        ... )
        >>> print(submission["submission_id"])
    """
    try:
        # Validate inputs
        if not project_name or not project_name.strip():
            raise ValueError("Project name cannot be empty")
        if not description or not description.strip():
            raise ValueError("Description cannot be empty")

        # Verify team exists
        teams = await zerodb_client.tables.query_rows(
            "teams",
            filter={"team_id": team_id},
            limit=1
        )
        if not teams:
            logger.warning(f"Team not found: {team_id}")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Team {team_id} not found",
            )

        # Generate submission ID
        submission_id = str(uuid.uuid4())

        # Prepare submission data
        submission_data = {
            "submission_id": submission_id,
            "team_id": team_id,
            "hackathon_id": hackathon_id,
            "project_name": project_name.strip(),
            "description": description.strip(),
            "status": "DRAFT",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        if repository_url:
            submission_data["repository_url"] = repository_url
        if demo_url:
            submission_data["demo_url"] = demo_url
        if video_url:
            submission_data["video_url"] = video_url
        if files:
            submission_data["files"] = files

        # Insert submission
        await zerodb_client.tables.insert_rows(
            "submissions",
            rows=[submission_data]
        )

        logger.info(
            f"Created submission {submission_id} for team {team_id} "
            f"in hackathon {hackathon_id}"
        )

        # Fetch and return created submission
        submissions = await zerodb_client.tables.query_rows(
            "submissions",
            filter={"submission_id": submission_id},
            limit=1
        )

        return submissions[0]

    except ValueError:
        # Re-raise validation errors
        raise

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout creating submission: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error creating submission: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create submission. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error creating submission: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create submission. Please contact support.",
        )


async def get_submission(
    zerodb_client: ZeroDBClient,
    submission_id: str,
    requester_id: str,
) -> Dict[str, Any]:
    """
    Get submission details.

    Args:
        zerodb_client: ZeroDB client instance
        submission_id: Submission ID to retrieve
        requester_id: User ID making the request (for future authorization)

    Returns:
        Dict with submission details

    Raises:
        HTTPException: 404 if submission not found
        HTTPException: 500 if database error

    Example:
        >>> submission = await get_submission(
        ...     client,
        ...     submission_id="sub-123",
        ...     requester_id="user-456"
        ... )
        >>> print(submission["project_name"])
    """
    try:
        # Get submission
        submissions = await zerodb_client.tables.query_rows(
            "submissions",
            filter={"submission_id": submission_id},
            limit=1
        )

        if not submissions:
            logger.warning(f"Submission not found: {submission_id}")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Submission {submission_id} not found",
            )

        return submissions[0]

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout getting submission: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error getting submission: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve submission. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error getting submission: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve submission. Please contact support.",
        )


async def list_submissions(
    zerodb_client: ZeroDBClient,
    requester_id: str,
    hackathon_id: Optional[str] = None,
    team_id: Optional[str] = None,
    status: Optional[SubmissionStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    List submissions with optional filters.

    Args:
        zerodb_client: ZeroDB client instance
        requester_id: User ID making the request (for future authorization)
        hackathon_id: Optional hackathon ID filter
        team_id: Optional team ID filter
        status: Optional status filter (DRAFT, SUBMITTED, SCORED)
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return (pagination)

    Returns:
        List of submission dictionaries

    Raises:
        HTTPException: 500 if database error

    Example:
        >>> submissions = await list_submissions(
        ...     client,
        ...     hackathon_id="hack-123",
        ...     status="SUBMITTED",
        ...     requester_id="user-456"
        ... )
        >>> print(f"Found {len(submissions)} submitted projects")
    """
    try:
        # Build filter
        filter_dict = {}
        if hackathon_id:
            filter_dict["hackathon_id"] = hackathon_id
        if team_id:
            filter_dict["team_id"] = team_id
        if status:
            filter_dict["status"] = status

        # Query submissions
        submissions = await zerodb_client.tables.query_rows(
            "submissions",
            filter=filter_dict if filter_dict else None,
            skip=skip,
            limit=limit
        )

        logger.info(f"Listed {len(submissions)} submissions")

        return submissions

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout listing submissions: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error listing submissions: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list submissions. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error listing submissions: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list submissions. Please contact support.",
        )


async def update_submission(
    zerodb_client: ZeroDBClient,
    submission_id: str,
    requester_id: str,
    project_name: Optional[str] = None,
    description: Optional[str] = None,
    repository_url: Optional[str] = None,
    demo_url: Optional[str] = None,
    video_url: Optional[str] = None,
    status: Optional[SubmissionStatus] = None,
    files: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Update submission details.

    Args:
        zerodb_client: ZeroDB client instance
        submission_id: Submission ID to update
        requester_id: User ID making the request (for future authorization)
        project_name: Optional new project name
        description: Optional new description
        repository_url: Optional new repository URL
        demo_url: Optional new demo URL
        video_url: Optional new video URL
        status: Optional new status (DRAFT, SUBMITTED, SCORED)
        files: Optional updated list of file metadata

    Returns:
        Dict with updated submission details

    Raises:
        ValueError: If status is invalid
        HTTPException: 404 if submission not found
        HTTPException: 500 if database error

    Example:
        >>> submission = await update_submission(
        ...     client,
        ...     submission_id="sub-123",
        ...     status="SUBMITTED",
        ...     requester_id="user-456"
        ... )
    """
    try:
        # Validate status if provided
        if status and status not in ["DRAFT", "SUBMITTED", "SCORED"]:
            raise ValueError(
                f"Invalid status: {status}. "
                "Must be 'DRAFT', 'SUBMITTED', or 'SCORED'"
            )

        # Check if submission exists
        submissions = await zerodb_client.tables.query_rows(
            "submissions",
            filter={"submission_id": submission_id},
            limit=1
        )

        if not submissions:
            logger.warning(f"Submission not found: {submission_id}")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Submission {submission_id} not found",
            )

        # Build update data
        update_data = {"updated_at": datetime.utcnow().isoformat()}
        
        if project_name is not None:
            update_data["project_name"] = project_name
        if description is not None:
            update_data["description"] = description
        if repository_url is not None:
            update_data["repository_url"] = repository_url
        if demo_url is not None:
            update_data["demo_url"] = demo_url
        if video_url is not None:
            update_data["video_url"] = video_url
        if files is not None:
            update_data["files"] = files
        
        if status is not None:
            update_data["status"] = status
            # If status changed to SUBMITTED, record the submission timestamp
            if status == "SUBMITTED" and submissions[0].get("status") != "SUBMITTED":
                update_data["submitted_at"] = datetime.utcnow().isoformat()

        # Update submission
        await zerodb_client.tables.update_rows(
            "submissions",
            filter={"submission_id": submission_id},
            update={"$set": update_data}
        )

        logger.info(f"Updated submission {submission_id}")

        # Fetch and return updated submission
        updated_submissions = await zerodb_client.tables.query_rows(
            "submissions",
            filter={"submission_id": submission_id},
            limit=1
        )

        return updated_submissions[0]

    except ValueError:
        # Re-raise validation errors
        raise

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout updating submission: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error updating submission: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update submission. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error updating submission: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update submission. Please contact support.",
        )


async def delete_submission(
    zerodb_client: ZeroDBClient,
    submission_id: str,
    requester_id: str,
) -> Dict[str, Any]:
    """
    Delete a submission.

    Args:
        zerodb_client: ZeroDB client instance
        submission_id: Submission ID to delete
        requester_id: User ID making the request (for future authorization)

    Returns:
        Dict with success status

    Raises:
        HTTPException: 404 if submission not found
        HTTPException: 400 if submission is already SCORED
        HTTPException: 500 if database error

    Example:
        >>> result = await delete_submission(
        ...     client,
        ...     submission_id="sub-123",
        ...     requester_id="user-456"
        ... )
    """
    try:
        # Check if submission exists
        submissions = await zerodb_client.tables.query_rows(
            "submissions",
            filter={"submission_id": submission_id},
            limit=1
        )

        if not submissions:
            logger.warning(f"Submission not found: {submission_id}")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Submission {submission_id} not found",
            )

        submission = submissions[0]

        # Prevent deletion of SCORED submissions
        if submission.get("status") == "SCORED":
            logger.warning(
                f"Attempted to delete SCORED submission: {submission_id}"
            )
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a submission that has been scored",
            )

        # Delete submission
        await zerodb_client.tables.delete_rows(
            "submissions",
            filter={"submission_id": submission_id}
        )

        logger.info(f"Deleted submission {submission_id}")

        return {"success": True, "deleted_id": submission_id}

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout deleting submission: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error deleting submission: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete submission. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error deleting submission: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete submission. Please contact support.",
        )


async def upload_file_to_submission(
    zerodb_client: ZeroDBClient,
    submission_id: str,
    file_name: str,
    file_content: str,
    file_type: str,
    file_size: int,
    requester_id: str,
) -> Dict[str, Any]:
    """
    Upload a file to a submission.

    Uses ZeroDB files API for file storage and updates submission file metadata.

    Args:
        zerodb_client: ZeroDB client instance
        submission_id: Submission ID to attach file to
        file_name: Name of the file
        file_content: Base64-encoded file content
        file_type: MIME type of the file
        file_size: Size of the file in bytes
        requester_id: User ID making the request (for future authorization)

    Returns:
        Dict with file upload details

    Raises:
        HTTPException: 404 if submission not found
        HTTPException: 500 if upload error

    Example:
        >>> file_info = await upload_file_to_submission(
        ...     client,
        ...     submission_id="sub-123",
        ...     file_name="demo.pdf",
        ...     file_content="base64content...",
        ...     file_type="application/pdf",
        ...     file_size=12345,
        ...     requester_id="user-456"
        ... )
    """
    try:
        # Check if submission exists
        submissions = await zerodb_client.tables.query_rows(
            "submissions",
            filter={"submission_id": submission_id},
            limit=1
        )

        if not submissions:
            logger.warning(f"Submission not found: {submission_id}")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Submission {submission_id} not found",
            )

        submission = submissions[0]

        # Upload file to ZeroDB
        upload_result = await zerodb_client.files.upload_file(
            file_name=file_name,
            file_content=file_content,
            content_type=file_type,
            metadata={
                "submission_id": submission_id,
                "uploaded_by": requester_id,
                "file_size": file_size,
            }
        )

        # Create file metadata
        file_metadata = {
            "file_id": upload_result["file_id"],
            "file_name": file_name,
            "file_url": upload_result["file_url"],
            "file_type": file_type,
            "file_size": file_size,
            "uploaded_at": datetime.utcnow().isoformat(),
        }

        # Update submission with new file
        existing_files = submission.get("files", [])
        existing_files.append(file_metadata)

        await zerodb_client.tables.update_rows(
            "submissions",
            filter={"submission_id": submission_id},
            update={
                "$set": {
                    "files": existing_files,
                    "updated_at": datetime.utcnow().isoformat()
                }
            }
        )

        logger.info(
            f"Uploaded file {file_name} to submission {submission_id}"
        )

        return file_metadata

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout uploading file: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error uploading file: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file. Please contact support.",
        )

    except Exception as e:
        logger.error(f"Unexpected error uploading file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file. Please contact support.",
        )
