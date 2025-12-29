"""
Hackathon Service

Provides CRUD operations for hackathons with participant management,
status validation, and soft delete functionality.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from fastapi import status as http_status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)
from services.authorization import check_organizer

# Configure logger
logger = logging.getLogger(__name__)


async def create_hackathon(
    zerodb_client: ZeroDBClient,
    name: str,
    description: Optional[str],
    organizer_id: str,
    start_date: datetime,
    end_date: datetime,
    location: str,
    registration_deadline: Optional[datetime] = None,
    max_participants: Optional[int] = None,
    website_url: Optional[str] = None,
    prizes: Optional[Dict[str, Any]] = None,
    rules: Optional[str] = None,
    status: str = "draft",
) -> Dict[str, Any]:
    """
    Create a new hackathon and automatically add creator as ORGANIZER.

    This function handles the complete hackathon creation workflow:
    1. Validates input data (dates, status)
    2. Creates hackathon record in ZeroDB
    3. Automatically adds creator as ORGANIZER in hackathon_participants
    4. Returns the created hackathon

    Args:
        zerodb_client: ZeroDB client instance
        name: Hackathon name (required, 3-200 chars)
        description: Detailed description (optional, max 5000 chars)
        organizer_id: UUID of the creating user
        start_date: When hackathon begins
        end_date: When hackathon ends
        location: Physical location or "virtual"
        registration_deadline: Optional registration cutoff
        max_participants: Optional participant limit (>= 1)
        website_url: Optional website URL
        prizes: Optional prize information as dict
        rules: Optional rules text
        status: Initial status (default: "draft")

    Returns:
        Dict with hackathon data including hackathon_id

    Raises:
        HTTPException: 400 for validation errors
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 300ms for typical operations

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> hackathon = await create_hackathon(
        ...     zerodb_client=client,
        ...     name="AI Hackathon 2025",
        ...     description="Build AI apps",
        ...     organizer_id="user-123",
        ...     start_date=datetime(2025, 3, 1),
        ...     end_date=datetime(2025, 3, 3),
        ...     location="San Francisco",
        ...     status="draft"
        ... )
        >>> print(hackathon['hackathon_id'])
        'hack-abc-123'
    """
    try:
        # Step 1: Validate status
        valid_statuses = ["draft", "upcoming", "active", "judging", "completed", "cancelled"]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}",
            )

        # Step 2: Validate dates
        if end_date <= start_date:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="end_date must be after start_date",
            )

        if registration_deadline and registration_deadline > start_date:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="registration_deadline must be before or equal to start_date",
            )

        # Step 3: Create hackathon record
        hackathon_id = str(uuid.uuid4())
        now = datetime.utcnow()

        hackathon_row = {
            "hackathon_id": hackathon_id,
            "name": name.strip(),
            "description": description,
            "organizer_id": organizer_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "registration_deadline": registration_deadline.isoformat() if registration_deadline else None,
            "max_participants": max_participants,
            "location": location.strip(),
            "website_url": website_url,
            "prizes": prizes,
            "rules": rules,
            "status": status,
            "is_deleted": False,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        logger.info(f"Creating hackathon: {name} (ID: {hackathon_id})")
        await zerodb_client.tables.insert_rows(
            "hackathons",
            rows=[hackathon_row],
        )

        # Step 4: Add creator as ORGANIZER participant
        participant_id = str(uuid.uuid4())
        participant_row = {
            "participant_id": participant_id,
            "hackathon_id": hackathon_id,
            "user_id": organizer_id,
            "role": "ORGANIZER",
            "status": "approved",
            "joined_at": now.isoformat(),
        }

        logger.info(f"Adding creator {organizer_id} as ORGANIZER for hackathon {hackathon_id}")
        await zerodb_client.tables.insert_rows(
            "hackathon_participants",
            rows=[participant_row],
        )

        logger.info(
            f"Successfully created hackathon {hackathon_id} with ORGANIZER {organizer_id}"
        )

        return {
            **hackathon_row,
            "hackathon_id": hackathon_id,
        }

    except HTTPException:
        # Re-raise HTTPException as-is
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout creating hackathon: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Hackathon creation timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error creating hackathon: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create hackathon. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error creating hackathon: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create hackathon. Please contact support.",
        )


async def get_hackathon(
    zerodb_client: ZeroDBClient,
    hackathon_id: str,
    include_deleted: bool = False,
) -> Dict[str, Any]:
    """
    Get a single hackathon by ID.

    Retrieves hackathon details from ZeroDB. By default, excludes soft-deleted hackathons.

    Args:
        zerodb_client: ZeroDB client instance
        hackathon_id: UUID of the hackathon
        include_deleted: If True, include soft-deleted hackathons

    Returns:
        Dict with hackathon data

    Raises:
        HTTPException: 404 if hackathon not found or is deleted
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 100ms for typical queries

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> hackathon = await get_hackathon(client, "hack-123")
        >>> print(hackathon['name'])
        'AI Hackathon 2025'
    """
    try:
        logger.debug(f"Retrieving hackathon {hackathon_id}")

        hackathons = await zerodb_client.tables.query_rows(
            "hackathons",
            filter={"hackathon_id": hackathon_id},
        )

        if not hackathons or len(hackathons) == 0:
            logger.warning(f"Hackathon {hackathon_id} not found")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Hackathon {hackathon_id} not found",
            )

        hackathon = hackathons[0]

        # Check if soft-deleted
        if hackathon.get("is_deleted", False) and not include_deleted:
            logger.warning(f"Hackathon {hackathon_id} is deleted")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Hackathon {hackathon_id} not found",
            )

        logger.info(f"Retrieved hackathon {hackathon_id}: {hackathon.get('name')}")
        return hackathon

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout retrieving hackathon {hackathon_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error retrieving hackathon {hackathon_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve hackathon. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error retrieving hackathon {hackathon_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve hackathon. Please contact support.",
        )


async def list_hackathons(
    zerodb_client: ZeroDBClient,
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    include_deleted: bool = False,
) -> Dict[str, Any]:
    """
    List hackathons with pagination and filtering.

    Retrieves paginated list of hackathons. Supports filtering by status.
    Excludes soft-deleted hackathons by default.

    Args:
        zerodb_client: ZeroDB client instance
        skip: Number of records to skip (default: 0)
        limit: Maximum records to return (default: 100, max: 1000)
        status_filter: Optional filter by status
        include_deleted: If True, include soft-deleted hackathons

    Returns:
        Dict with keys:
        - hackathons: List of hackathon objects
        - total: Total number of matching hackathons
        - skip: Number skipped
        - limit: Limit applied

    Raises:
        HTTPException: 400 for invalid pagination parameters
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 500ms for typical queries

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> result = await list_hackathons(client, skip=0, limit=10, status_filter="active")
        >>> print(f"Found {result['total']} active hackathons")
        Found 5 active hackathons
    """
    try:
        # Validate pagination
        if skip < 0:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="skip must be >= 0",
            )

        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="limit must be between 1 and 1000",
            )

        logger.info(f"Listing hackathons (skip={skip}, limit={limit}, status={status_filter})")

        # Build filter
        query_filter = {}
        if status_filter:
            query_filter["status"] = status_filter
        if not include_deleted:
            query_filter["is_deleted"] = False

        # Query hackathons
        all_hackathons = await zerodb_client.tables.query_rows(
            "hackathons",
            filter=query_filter if query_filter else None,
        )

        total = len(all_hackathons)

        # Apply pagination
        hackathons = all_hackathons[skip : skip + limit]

        logger.info(f"Retrieved {len(hackathons)} of {total} hackathons")

        return {
            "hackathons": hackathons,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout listing hackathons: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error listing hackathons: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list hackathons. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error listing hackathons: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list hackathons. Please contact support.",
        )


async def update_hackathon(
    zerodb_client: ZeroDBClient,
    hackathon_id: str,
    user_id: str,
    update_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Update a hackathon (ORGANIZER only).

    Updates hackathon fields. Only users with ORGANIZER role can update.
    Validates status transitions and date consistency.

    Args:
        zerodb_client: ZeroDB client instance
        hackathon_id: UUID of hackathon to update
        user_id: UUID of user attempting update
        update_data: Dict of fields to update

    Returns:
        Dict with updated hackathon data

    Raises:
        HTTPException: 403 if user is not ORGANIZER
        HTTPException: 404 if hackathon not found
        HTTPException: 400 for validation errors
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 300ms for typical operations

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> updated = await update_hackathon(
        ...     zerodb_client=client,
        ...     hackathon_id="hack-123",
        ...     user_id="user-456",
        ...     update_data={"status": "active", "max_participants": 100}
        ... )
        >>> print(updated['status'])
        'active'
    """
    try:
        # Step 1: Check authorization (ORGANIZER role required)
        logger.info(f"Checking ORGANIZER authorization for user {user_id} on hackathon {hackathon_id}")
        await check_organizer(
            zerodb_client=zerodb_client,
            user_id=user_id,
            hackathon_id=hackathon_id,
        )

        # Step 2: Get current hackathon
        hackathon = await get_hackathon(zerodb_client, hackathon_id)

        # Step 3: Validate update data
        if "status" in update_data:
            valid_statuses = ["draft", "upcoming", "active", "judging", "completed", "cancelled"]
            if update_data["status"] not in valid_statuses:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
                )

        # Validate dates if both are provided in update or one is provided
        start_date = update_data.get("start_date")
        end_date = update_data.get("end_date")

        # Convert to datetime if provided as strings
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        # Get existing dates if not being updated
        if start_date is None and "start_date" in hackathon:
            existing_start = hackathon["start_date"]
            if isinstance(existing_start, str):
                start_date = datetime.fromisoformat(existing_start.replace('Z', '+00:00'))
        if end_date is None and "end_date" in hackathon:
            existing_end = hackathon["end_date"]
            if isinstance(existing_end, str):
                end_date = datetime.fromisoformat(existing_end.replace('Z', '+00:00'))

        if start_date and end_date and end_date <= start_date:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="end_date must be after start_date",
            )

        # Step 4: Prepare update
        update_fields = {}
        for key, value in update_data.items():
            if value is not None:  # Only update non-None values
                # Convert datetime to ISO string for ZeroDB
                if isinstance(value, datetime):
                    update_fields[key] = value.isoformat()
                else:
                    update_fields[key] = value

        # Add updated_at timestamp
        update_fields["updated_at"] = datetime.utcnow().isoformat()

        # Step 5: Perform update
        logger.info(f"Updating hackathon {hackathon_id} with fields: {list(update_fields.keys())}")
        await zerodb_client.tables.update_rows(
            "hackathons",
            filter={"hackathon_id": hackathon_id},
            update={"$set": update_fields},
        )

        # Step 6: Get updated hackathon
        updated_hackathon = await get_hackathon(zerodb_client, hackathon_id)

        logger.info(f"Successfully updated hackathon {hackathon_id}")
        return updated_hackathon

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout updating hackathon {hackathon_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Update timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error updating hackathon {hackathon_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update hackathon. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error updating hackathon {hackathon_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update hackathon. Please contact support.",
        )


async def delete_hackathon(
    zerodb_client: ZeroDBClient,
    hackathon_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Soft delete a hackathon (ORGANIZER only).

    Marks hackathon as deleted (is_deleted=True) instead of removing the record.
    This preserves data integrity and allows for recovery if needed.

    Args:
        zerodb_client: ZeroDB client instance
        hackathon_id: UUID of hackathon to delete
        user_id: UUID of user attempting deletion

    Returns:
        Dict with deletion confirmation:
        - success: True
        - hackathon_id: ID of deleted hackathon
        - message: Confirmation message

    Raises:
        HTTPException: 403 if user is not ORGANIZER
        HTTPException: 404 if hackathon not found
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 200ms for typical operations

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> result = await delete_hackathon(
        ...     zerodb_client=client,
        ...     hackathon_id="hack-123",
        ...     user_id="user-456"
        ... )
        >>> print(result['success'])
        True
    """
    try:
        # Step 1: Check authorization (ORGANIZER role required)
        logger.info(f"Checking ORGANIZER authorization for user {user_id} on hackathon {hackathon_id}")
        await check_organizer(
            zerodb_client=zerodb_client,
            user_id=user_id,
            hackathon_id=hackathon_id,
        )

        # Step 2: Verify hackathon exists and is not already deleted
        hackathon = await get_hackathon(zerodb_client, hackathon_id)

        if hackathon.get("is_deleted", False):
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Hackathon {hackathon_id} not found",
            )

        # Step 3: Soft delete (mark as deleted)
        logger.info(f"Soft deleting hackathon {hackathon_id}")
        await zerodb_client.tables.update_rows(
            "hackathons",
            filter={"hackathon_id": hackathon_id},
            update={
                "$set": {
                    "is_deleted": True,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            },
        )

        logger.info(f"Successfully soft deleted hackathon {hackathon_id}")

        return {
            "success": True,
            "hackathon_id": hackathon_id,
            "message": "Hackathon successfully deleted",
        }

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout deleting hackathon {hackathon_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Deletion timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error deleting hackathon {hackathon_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete hackathon. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error deleting hackathon {hackathon_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete hackathon. Please contact support.",
        )
