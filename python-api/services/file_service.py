"""
File Upload and Management Service

Provides business logic for file uploads, downloads, and management
using ZeroDB Files API with comprehensive validation.
"""

import logging
import mimetypes
from typing import Any, Dict, List, Optional, Tuple

from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBNotFound

# Configure logger
logger = logging.getLogger(__name__)

# File validation constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
ALLOWED_EXTENSIONS = {
    "image": ["png", "jpg", "jpeg", "gif"],
    "pdf": ["pdf"],
    "video": ["mp4", "mov"],
}

# MIME type mappings
MIME_TYPE_MAP = {
    # Images
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    # PDF
    "pdf": "application/pdf",
    # Videos
    "mp4": "video/mp4",
    "mov": "video/quicktime",
}


def validate_file(
    filename: str,
    file_size: int,
    allowed_types: Optional[List[str]] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Validate file based on name, size, and type.

    Args:
        filename: Name of the file to validate
        file_size: Size of the file in bytes
        allowed_types: List of allowed file type categories (image, pdf, video)
                      If None, all types are allowed

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if file is valid
        - (False, error_message) if validation fails

    Example:
        >>> is_valid, error = validate_file("logo.png", 5000000, ["image"])
        >>> if not is_valid:
        >>>     raise ValueError(error)
    """
    # Check file size
    if file_size > MAX_FILE_SIZE:
        size_mb = MAX_FILE_SIZE / (1024 * 1024)
        return False, f"File size exceeds maximum allowed size of {size_mb}MB"

    if file_size <= 0:
        return False, "File size must be greater than 0 bytes"

    # Extract file extension
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if not extension:
        return False, "File must have an extension"

    # Build list of allowed extensions
    if allowed_types:
        allowed_extensions = []
        for file_type in allowed_types:
            if file_type in ALLOWED_EXTENSIONS:
                allowed_extensions.extend(ALLOWED_EXTENSIONS[file_type])
    else:
        # All types allowed
        allowed_extensions = [ext for exts in ALLOWED_EXTENSIONS.values() for ext in exts]

    # Check if extension is allowed
    if extension not in allowed_extensions:
        return False, f"File type '{extension}' not allowed. Allowed types: {', '.join(allowed_extensions)}"

    return True, None


def get_content_type(filename: str) -> str:
    """
    Get MIME content type from filename.

    Args:
        filename: Name of the file

    Returns:
        MIME content type string (e.g., "image/png")
        Defaults to "application/octet-stream" if unknown

    Example:
        >>> content_type = get_content_type("logo.png")
        >>> # Returns: "image/png"
    """
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # Try custom MIME map first
    if extension in MIME_TYPE_MAP:
        return MIME_TYPE_MAP[extension]

    # Fall back to mimetypes library
    guessed_type, _ = mimetypes.guess_type(filename)
    return guessed_type or "application/octet-stream"


def get_file_category(filename: str) -> Optional[str]:
    """
    Get file category (image, pdf, video) from filename.

    Args:
        filename: Name of the file

    Returns:
        File category string or None if unknown

    Example:
        >>> category = get_file_category("logo.png")
        >>> # Returns: "image"
    """
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    for category, extensions in ALLOWED_EXTENSIONS.items():
        if extension in extensions:
            return category

    return None


async def upload_team_logo(
    zerodb_client: ZeroDBClient,
    team_id: str,
    file_content: bytes,
    filename: str,
) -> Dict[str, Any]:
    """
    Upload a team logo to ZeroDB storage.

    Args:
        zerodb_client: Initialized ZeroDB client
        team_id: UUID of the team
        file_content: Logo file content as bytes
        filename: Name of the logo file

    Returns:
        Dict containing upload result with file_id, url, etc.

    Raises:
        ValueError: If validation fails
        ZeroDBError: If upload fails

    Example:
        >>> result = await upload_team_logo(
        >>>     client, "team-123", logo_bytes, "logo.png"
        >>> )
        >>> file_id = result["file_id"]
    """
    # Validate file
    is_valid, error = validate_file(filename, len(file_content), allowed_types=["image"])
    if not is_valid:
        logger.error(f"Team logo validation failed: {error}")
        raise ValueError(error)

    # Get content type
    content_type = get_content_type(filename)

    # Upload to ZeroDB
    try:
        result = await zerodb_client.files.upload_file(
            file_name=filename,
            file_content=file_content,
            content_type=content_type,
            folder=f"teams/{team_id}/logos",
            metadata={
                "team_id": team_id,
                "file_type": "team_logo",
            },
        )

        logger.info(f"Team logo uploaded successfully: {result['file_id']} for team {team_id}")
        return result

    except ZeroDBError as e:
        logger.error(f"Failed to upload team logo: {str(e)}")
        raise


async def upload_submission_file(
    zerodb_client: ZeroDBClient,
    submission_id: str,
    file_content: bytes,
    filename: str,
    file_type: str,
) -> Dict[str, Any]:
    """
    Upload a submission file (screenshot, video, or document).

    Args:
        zerodb_client: Initialized ZeroDB client
        submission_id: UUID of the submission
        file_content: File content as bytes
        filename: Name of the file
        file_type: Type of file (image, video, pdf)

    Returns:
        Dict containing upload result with file_id, url, etc.

    Raises:
        ValueError: If validation fails or invalid file_type
        ZeroDBError: If upload fails

    Example:
        >>> result = await upload_submission_file(
        >>>     client, "sub-123", video_bytes, "demo.mp4", "video"
        >>> )
    """
    # Validate file type
    if file_type not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Invalid file_type '{file_type}'. Must be one of: {list(ALLOWED_EXTENSIONS.keys())}")

    # Validate file
    is_valid, error = validate_file(filename, len(file_content), allowed_types=[file_type])
    if not is_valid:
        logger.error(f"Submission file validation failed: {error}")
        raise ValueError(error)

    # Get content type
    content_type = get_content_type(filename)

    # Upload to ZeroDB
    try:
        result = await zerodb_client.files.upload_file(
            file_name=filename,
            file_content=file_content,
            content_type=content_type,
            folder=f"submissions/{submission_id}/{file_type}s",
            metadata={
                "submission_id": submission_id,
                "file_type": file_type,
            },
        )

        logger.info(
            f"Submission file uploaded: {result['file_id']} for submission {submission_id} (type: {file_type})"
        )
        return result

    except ZeroDBError as e:
        logger.error(f"Failed to upload submission file: {str(e)}")
        raise


async def generate_download_url(
    zerodb_client: ZeroDBClient,
    file_id: str,
    expiration_seconds: int = 3600,
) -> Dict[str, Any]:
    """
    Generate a presigned URL for secure file download.

    Args:
        zerodb_client: Initialized ZeroDB client
        file_id: Unique file identifier
        expiration_seconds: URL expiration time in seconds (default: 1 hour)

    Returns:
        Dict containing presigned URL and expiration info

    Raises:
        ZeroDBNotFound: If file doesn't exist
        ZeroDBError: If generation fails

    Example:
        >>> result = await generate_download_url(client, "file_abc", 1800)
        >>> download_url = result["url"]
    """
    try:
        result = await zerodb_client.files.generate_presigned_url(
            file_id=file_id,
            expiration_seconds=expiration_seconds,
        )

        logger.info(f"Generated presigned URL for file {file_id} (expires in {expiration_seconds}s)")
        return result

    except ZeroDBNotFound:
        logger.error(f"File not found: {file_id}")
        raise
    except ZeroDBError as e:
        logger.error(f"Failed to generate presigned URL: {str(e)}")
        raise


async def list_team_files(
    zerodb_client: ZeroDBClient,
    team_id: str,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    List all files for a specific team.

    Args:
        zerodb_client: Initialized ZeroDB client
        team_id: UUID of the team
        limit: Maximum number of files to return
        offset: Pagination offset

    Returns:
        Dict containing files list and pagination info

    Raises:
        ZeroDBError: If listing fails

    Example:
        >>> result = await list_team_files(client, "team-123", limit=50)
        >>> for file in result["files"]:
        >>>     print(file["file_name"])
    """
    try:
        result = await zerodb_client.files.list_files(
            folder=f"teams/{team_id}",
            limit=limit,
            offset=offset,
        )

        logger.info(f"Listed {len(result.get('files', []))} files for team {team_id}")
        return result

    except ZeroDBError as e:
        logger.error(f"Failed to list team files: {str(e)}")
        raise


async def delete_file(
    zerodb_client: ZeroDBClient,
    file_id: str,
) -> Dict[str, Any]:
    """
    Delete a file from ZeroDB storage.

    Args:
        zerodb_client: Initialized ZeroDB client
        file_id: Unique file identifier

    Returns:
        Dict containing deletion confirmation

    Raises:
        ZeroDBNotFound: If file doesn't exist
        ZeroDBError: If deletion fails

    Example:
        >>> result = await delete_file(client, "file_abc123")
        >>> print(result["message"])
    """
    try:
        result = await zerodb_client.files.delete_file(file_id=file_id)

        logger.info(f"File deleted: {file_id}")
        return result

    except ZeroDBNotFound:
        logger.error(f"File not found: {file_id}")
        raise
    except ZeroDBError as e:
        logger.error(f"Failed to delete file: {str(e)}")
        raise


async def get_file_metadata(
    zerodb_client: ZeroDBClient,
    file_id: str,
) -> Dict[str, Any]:
    """
    Get metadata for a file without downloading content.

    Args:
        zerodb_client: Initialized ZeroDB client
        file_id: Unique file identifier

    Returns:
        Dict containing file metadata

    Raises:
        ZeroDBNotFound: If file doesn't exist
        ZeroDBError: If retrieval fails

    Example:
        >>> metadata = await get_file_metadata(client, "file_abc")
        >>> print(f"Size: {metadata['size']} bytes")
    """
    try:
        result = await zerodb_client.files.get_file_metadata(file_id=file_id)

        logger.info(f"Retrieved metadata for file {file_id}")
        return result

    except ZeroDBNotFound:
        logger.error(f"File not found: {file_id}")
        raise
    except ZeroDBError as e:
        logger.error(f"Failed to get file metadata: {str(e)}")
        raise
