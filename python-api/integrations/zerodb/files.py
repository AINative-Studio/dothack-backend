"""
ZeroDB Files API Integration

Provides methods for file upload, download, and management using ZeroDB Files API.
"""

import base64
from typing import Any, Dict, List, Optional


class FilesAPI:
    """
    ZeroDB Files API operations.

    Provides methods for:
    - Uploading files with metadata
    - Generating presigned download URLs
    - Listing files by folder/filters
    - Deleting files
    - Retrieving file metadata

    All methods are async and use the parent ZeroDBClient for HTTP requests.
    """

    def __init__(self, client):
        """
        Initialize Files API wrapper.

        Args:
            client: Parent ZeroDBClient instance
        """
        self.client = client

    async def upload_file(
        self,
        file_name: str,
        file_content: bytes,
        content_type: str = "application/octet-stream",
        folder: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Upload a file to ZeroDB storage.

        Args:
            file_name: Name of the file
            file_content: File content as bytes
            content_type: MIME type of the file
            folder: Optional virtual folder path (e.g., "teams/logos")
            metadata: Optional metadata dictionary (e.g., {"team_id": "123"})

        Returns:
            Dict containing:
                - file_id: Unique file identifier
                - file_name: Name of the uploaded file
                - content_type: MIME type
                - size: File size in bytes
                - folder: Virtual folder path
                - metadata: File metadata
                - created_at: Upload timestamp
                - url: Optional public URL (if enabled)

        Raises:
            ZeroDBError: If upload fails
            ZeroDBAuthError: If authentication fails

        Example:
            >>> with open("logo.png", "rb") as f:
            >>>     result = await client.files.upload_file(
            >>>         file_name="team_logo.png",
            >>>         file_content=f.read(),
            >>>         content_type="image/png",
            >>>         folder="teams/logos",
            >>>         metadata={"team_id": "abc-123"}
            >>>     )
            >>> print(result["file_id"])
        """
        # Encode file content as base64
        file_content_b64 = base64.b64encode(file_content).decode("utf-8")

        # Prepare request payload
        payload = {
            "file_name": file_name,
            "file_content": file_content_b64,
            "content_type": content_type,
        }

        if folder:
            payload["folder"] = folder

        if metadata:
            payload["metadata"] = metadata

        # Make API request
        path = f"/v1/public/projects/{self.client.project_id}/files/upload"
        return await self.client._request("POST", path, json=payload)

    async def generate_presigned_url(
        self,
        file_id: str,
        expiration_seconds: int = 3600,
    ) -> Dict[str, Any]:
        """
        Generate a presigned URL for secure file download.

        Args:
            file_id: Unique file identifier
            expiration_seconds: URL expiration time in seconds (default: 1 hour)

        Returns:
            Dict containing:
                - url: Presigned download URL
                - expires_at: URL expiration timestamp
                - file_id: File identifier

        Raises:
            ZeroDBNotFound: If file doesn't exist
            ZeroDBError: If generation fails

        Example:
            >>> result = await client.files.generate_presigned_url(
            >>>     file_id="file_abc123",
            >>>     expiration_seconds=1800  # 30 minutes
            >>> )
            >>> download_url = result["url"]
        """
        path = f"/v1/public/projects/{self.client.project_id}/files/{file_id}/presigned-url"
        params = {"expiration_seconds": expiration_seconds}
        return await self.client._request("GET", path, params=params)

    async def list_files(
        self,
        folder: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        List files in project storage with optional filters.

        Args:
            folder: Filter by virtual folder path
            content_type: Filter by MIME type (e.g., "image/png")
            limit: Maximum number of files to return (default: 100)
            offset: Pagination offset (default: 0)

        Returns:
            Dict containing:
                - files: List of file objects
                - total: Total number of files matching filters
                - limit: Items per page
                - offset: Current offset

        Raises:
            ZeroDBError: If listing fails

        Example:
            >>> result = await client.files.list_files(
            >>>     folder="teams/logos",
            >>>     content_type="image/png",
            >>>     limit=50
            >>> )
            >>> for file in result["files"]:
            >>>     print(file["file_name"])
        """
        path = f"/v1/public/projects/{self.client.project_id}/files"
        params = {"limit": limit, "offset": offset}

        if folder:
            params["folder"] = folder

        if content_type:
            params["content_type"] = content_type

        return await self.client._request("GET", path, params=params)

    async def delete_file(self, file_id: str) -> Dict[str, Any]:
        """
        Delete a file from ZeroDB storage.

        Args:
            file_id: Unique file identifier

        Returns:
            Dict containing:
                - success: True if deleted
                - file_id: Deleted file identifier
                - message: Confirmation message

        Raises:
            ZeroDBNotFound: If file doesn't exist
            ZeroDBError: If deletion fails

        Example:
            >>> result = await client.files.delete_file("file_abc123")
            >>> print(result["message"])
        """
        path = f"/v1/public/projects/{self.client.project_id}/files/{file_id}"
        return await self.client._request("DELETE", path)

    async def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Get file metadata without downloading content.

        Args:
            file_id: Unique file identifier

        Returns:
            Dict containing:
                - file_id: Unique identifier
                - file_name: Name of the file
                - content_type: MIME type
                - size: File size in bytes
                - folder: Virtual folder path
                - metadata: Custom metadata
                - created_at: Upload timestamp

        Raises:
            ZeroDBNotFound: If file doesn't exist
            ZeroDBError: If retrieval fails

        Example:
            >>> metadata = await client.files.get_file_metadata("file_abc123")
            >>> print(f"Size: {metadata['size']} bytes")
        """
        path = f"/v1/public/projects/{self.client.project_id}/files/{file_id}/metadata"
        return await self.client._request("GET", path)

    async def download_file(
        self,
        file_id: str,
        return_base64: bool = True,
    ) -> Dict[str, Any]:
        """
        Download file content from ZeroDB storage.

        Args:
            file_id: Unique file identifier
            return_base64: If True, returns base64-encoded content (default: True)

        Returns:
            Dict containing:
                - file_id: Unique identifier
                - file_name: Name of the file
                - content_type: MIME type
                - content: File content (base64-encoded if return_base64=True)
                - size: File size in bytes

        Raises:
            ZeroDBNotFound: If file doesn't exist
            ZeroDBError: If download fails

        Example:
            >>> result = await client.files.download_file("file_abc123")
            >>> content_bytes = base64.b64decode(result["content"])
        """
        path = f"/v1/public/projects/{self.client.project_id}/files/{file_id}/download"
        params = {"return_base64": return_base64}
        return await self.client._request("GET", path, params=params)
