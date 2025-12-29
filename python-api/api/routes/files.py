"""
File Upload and Management API Routes

Provides REST endpoints for file uploads (team logos, submission files)
and file management operations using ZeroDB Files API.
"""

import logging
from typing import Any, Dict

from api.dependencies import get_current_user
from api.schemas.files import (
    ErrorResponse,
    FileDeleteResponse,
    FileListResponse,
    FileMetadataResponse,
    FileUploadResponse,
    PresignedURLResponse,
    SubmissionFileUploadRequest,
)
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBNotFound
from services.file_service import (
    delete_file,
    generate_download_url,
    get_file_metadata,
    list_team_files,
    upload_submission_file,
    upload_team_logo,
)

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/files", tags=["Files"])


# Dependency: Get ZeroDB client
async def get_zerodb_client() -> ZeroDBClient:
    """
    Dependency to provide ZeroDB client instance.

    Returns:
        ZeroDBClient instance configured with environment credentials

    Raises:
        HTTPException: 503 if ZeroDB client cannot be initialized
    """
    try:
        client = ZeroDBClient()
        return client
    except ValueError as e:
        logger.error(f"Failed to initialize ZeroDB client: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please contact support.",
        )


@router.post(
    "/teams/{team_id}/logo",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Team logo uploaded successfully"},
        400: {"model": ErrorResponse, "description": "Invalid file or validation error"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        413: {"model": ErrorResponse, "description": "File too large"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Upload Team Logo",
    description="""
    Upload a team logo image.

    - Max file size: 10MB
    - Allowed types: PNG, JPG, JPEG, GIF
    - Requires authentication

    **Authorization:** User must be authenticated
    """,
)
async def upload_team_logo_endpoint(
    team_id: str,
    file: UploadFile = File(..., description="Team logo image file"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Upload a team logo.

    Args:
        team_id: UUID of the team
        file: Uploaded file (multipart/form-data)
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        File upload response with file_id and metadata

    Raises:
        HTTPException: 400 if validation fails, 413 if file too large, 500 on error
    """
    try:
        # Read file content
        file_content = await file.read()

        # Upload logo
        result = await upload_team_logo(
            zerodb_client=zerodb_client,
            team_id=team_id,
            file_content=file_content,
            filename=file.filename or "logo.png",
        )

        return result

    except ValueError as e:
        # Validation error
        logger.error(f"Team logo validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ZeroDBError as e:
        logger.error(f"Failed to upload team logo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file. Please try again.",
        )
    finally:
        # Close file
        await file.close()


@router.post(
    "/submissions/{submission_id}/files",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Submission file uploaded successfully"},
        400: {"model": ErrorResponse, "description": "Invalid file or validation error"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        413: {"model": ErrorResponse, "description": "File too large"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Upload Submission File",
    description="""
    Upload a submission artifact (screenshot, video, or document).

    - Max file size: 10MB
    - Allowed types: Images (PNG, JPG, JPEG, GIF), Videos (MP4, MOV), PDFs
    - Requires authentication

    **Authorization:** User must be authenticated
    """,
)
async def upload_submission_file_endpoint(
    submission_id: str,
    file_type: str = Query(..., description="File type (image, video, pdf)"),
    file: UploadFile = File(..., description="Submission file"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Upload a submission file.

    Args:
        submission_id: UUID of the submission
        file_type: Type of file (image, video, pdf)
        file: Uploaded file (multipart/form-data)
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        File upload response with file_id and metadata

    Raises:
        HTTPException: 400 if validation fails, 413 if file too large, 500 on error
    """
    try:
        # Read file content
        file_content = await file.read()

        # Upload file
        result = await upload_submission_file(
            zerodb_client=zerodb_client,
            submission_id=submission_id,
            file_content=file_content,
            filename=file.filename or "file",
            file_type=file_type,
        )

        return result

    except ValueError as e:
        # Validation error
        logger.error(f"Submission file validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ZeroDBError as e:
        logger.error(f"Failed to upload submission file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file. Please try again.",
        )
    finally:
        # Close file
        await file.close()


@router.get(
    "/{file_id}/download",
    response_model=PresignedURLResponse,
    responses={
        200: {"description": "Presigned URL generated successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "File not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Get File Download URL",
    description="""
    Generate a presigned URL for secure file download.

    - URL expires after specified time (default: 1 hour)
    - Requires authentication

    **Authorization:** User must be authenticated
    """,
)
async def get_file_download_url_endpoint(
    file_id: str,
    expiration_seconds: int = Query(3600, description="URL expiration time in seconds", ge=60, le=86400),
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Get presigned download URL for a file.

    Args:
        file_id: Unique file identifier
        expiration_seconds: URL expiration time (60-86400 seconds)
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        Presigned URL response with URL and expiration

    Raises:
        HTTPException: 404 if file not found, 500 on error
    """
    try:
        result = await generate_download_url(
            zerodb_client=zerodb_client,
            file_id=file_id,
            expiration_seconds=expiration_seconds,
        )

        return result

    except ZeroDBNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_id}",
        )
    except ZeroDBError as e:
        logger.error(f"Failed to generate download URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL. Please try again.",
        )


@router.get(
    "/teams/{team_id}",
    response_model=FileListResponse,
    responses={
        200: {"description": "Files retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="List Team Files",
    description="""
    List all files for a specific team.

    - Supports pagination
    - Requires authentication

    **Authorization:** User must be authenticated
    """,
)
async def list_team_files_endpoint(
    team_id: str,
    limit: int = Query(100, description="Maximum files to return", ge=1, le=1000),
    offset: int = Query(0, description="Pagination offset", ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    List all files for a team.

    Args:
        team_id: UUID of the team
        limit: Maximum files to return (1-1000)
        offset: Pagination offset
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        File list response with files array and pagination info

    Raises:
        HTTPException: 500 on error
    """
    try:
        result = await list_team_files(
            zerodb_client=zerodb_client,
            team_id=team_id,
            limit=limit,
            offset=offset,
        )

        return result

    except ZeroDBError as e:
        logger.error(f"Failed to list team files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list files. Please try again.",
        )


@router.delete(
    "/{file_id}",
    response_model=FileDeleteResponse,
    responses={
        200: {"description": "File deleted successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "File not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Delete File",
    description="""
    Delete a file from storage.

    - Permanently removes the file
    - Requires authentication

    **Authorization:** User must be authenticated
    """,
)
async def delete_file_endpoint(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Delete a file.

    Args:
        file_id: Unique file identifier
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        File deletion confirmation

    Raises:
        HTTPException: 404 if file not found, 500 on error
    """
    try:
        result = await delete_file(
            zerodb_client=zerodb_client,
            file_id=file_id,
        )

        return result

    except ZeroDBNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_id}",
        )
    except ZeroDBError as e:
        logger.error(f"Failed to delete file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file. Please try again.",
        )


@router.get(
    "/{file_id}/metadata",
    response_model=FileMetadataResponse,
    responses={
        200: {"description": "Metadata retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "File not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Get File Metadata",
    description="""
    Get file metadata without downloading content.

    - Returns file details and custom metadata
    - Requires authentication

    **Authorization:** User must be authenticated
    """,
)
async def get_file_metadata_endpoint(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Get file metadata.

    Args:
        file_id: Unique file identifier
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        File metadata response

    Raises:
        HTTPException: 404 if file not found, 500 on error
    """
    try:
        result = await get_file_metadata(
            zerodb_client=zerodb_client,
            file_id=file_id,
        )

        return result

    except ZeroDBNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_id}",
        )
    except ZeroDBError as e:
        logger.error(f"Failed to get file metadata: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get file metadata. Please try again.",
        )
