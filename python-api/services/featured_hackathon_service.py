"""
Featured hackathon service for managing homepage featured entries.

Handles CRUD operations, expiration filtering, and display order management.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status

from integrations.zerodb.client import ZeroDBClient


logger = logging.getLogger(__name__)


async def get_featured_by_hackathon_id(
    hackathon_id: str,
    zerodb: ZeroDBClient,
    exclude_id: Optional[str] = None
) -> Optional[Dict]:
    """
    Get featured entry by hackathon_id for duplicate checking.

    Args:
        hackathon_id: Hackathon UUID to search for
        zerodb: ZeroDB client instance
        exclude_id: Featured entry ID to exclude from check (for updates)

    Returns:
        Featured entry dict if found, None otherwise
    """
    try:
        response = await zerodb.tables.query_rows(
            table_id="featured_hackathons",
            filter={"hackathon_id": hackathon_id},
            limit=1
        )

        if response and response.get("rows"):
            featured = response["rows"][0]
            if exclude_id and featured.get("id") == exclude_id:
                return None
            return featured
        return None

    except Exception as e:
        logger.error(f"Error checking featured hackathon: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check featured hackathon: {str(e)}"
        )


async def verify_hackathon_exists(hackathon_id: str, zerodb: ZeroDBClient) -> bool:
    """
    Verify that a hackathon exists in the database.

    Args:
        hackathon_id: Hackathon UUID to verify
        zerodb: ZeroDB client instance

    Returns:
        True if hackathon exists, raises HTTPException otherwise
    """
    try:
        response = await zerodb.tables.query_rows(
            table_id="hackathons",
            filter={"id": hackathon_id},
            limit=1
        )

        if not response or not response.get("rows"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hackathon {hackathon_id} not found"
            )
        return True

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying hackathon: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify hackathon: {str(e)}"
        )


async def get_next_display_order(zerodb: ZeroDBClient) -> int:
    """
    Get next available display order.

    Args:
        zerodb: ZeroDB client instance

    Returns:
        Next display order number
    """
    try:
        response = await zerodb.tables.query_rows(
            table_id="featured_hackathons",
            filter={},
            limit=1000  # Get all featured hackathons
        )

        if not response or not response.get("rows"):
            return 1

        # Find max display_order
        max_order = max(
            (featured.get("display_order", 0) for featured in response["rows"]),
            default=0
        )
        return max_order + 1

    except Exception as e:
        logger.error(f"Error getting next display order: {str(e)}")
        return 1


async def create_featured(
    hackathon_id: str,
    display_order: int,
    featured_until: Optional[str],
    is_active: bool,
    zerodb: ZeroDBClient
) -> Dict:
    """
    Create a new featured hackathon entry.

    Args:
        hackathon_id: UUID of hackathon to feature
        display_order: Display order on homepage
        featured_until: Optional expiration timestamp
        is_active: Active status
        zerodb: ZeroDB client instance

    Returns:
        Created featured entry data

    Raises:
        HTTPException: If hackathon doesn't exist, already featured, or database error
    """
    # Verify hackathon exists
    await verify_hackathon_exists(hackathon_id, zerodb)

    # Check if already featured
    existing = await get_featured_by_hackathon_id(hackathon_id, zerodb)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Hackathon {hackathon_id} is already featured"
        )

    try:
        featured_id = str(uuid4())
        now = datetime.utcnow().isoformat()

        featured_data = {
            "id": featured_id,
            "hackathon_id": hackathon_id,
            "display_order": display_order,
            "featured_until": featured_until,
            "is_active": is_active,
            "created_at": now,
            "updated_at": now
        }

        await zerodb.tables.insert_rows(
            table_id="featured_hackathons",
            rows=[featured_data]
        )

        logger.info(f"Created featured entry {featured_id} for hackathon {hackathon_id}")
        return featured_data

    except Exception as e:
        logger.error(f"Error creating featured entry: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create featured entry: {str(e)}"
        )


async def get_featured(featured_id: str, zerodb: ZeroDBClient) -> Dict:
    """
    Get a featured entry by ID.

    Args:
        featured_id: UUID of the featured entry
        zerodb: ZeroDB client instance

    Returns:
        Featured entry data

    Raises:
        HTTPException: If featured entry not found or database error
    """
    try:
        response = await zerodb.tables.query_rows(
            table_id="featured_hackathons",
            filter={"id": featured_id},
            limit=1
        )

        if not response or not response.get("rows"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Featured entry {featured_id} not found"
            )

        return response["rows"][0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving featured entry: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve featured entry: {str(e)}"
        )


async def get_hackathon_details(hackathon_id: str, zerodb: ZeroDBClient) -> Optional[Dict]:
    """
    Get hackathon details for a featured entry.

    Args:
        hackathon_id: UUID of the hackathon
        zerodb: ZeroDB client instance

    Returns:
        Hackathon details dict or None if not found
    """
    try:
        response = await zerodb.tables.query_rows(
            table_id="hackathons",
            filter={"id": hackathon_id},
            limit=1
        )

        if response and response.get("rows"):
            return response["rows"][0]
        return None

    except Exception as e:
        logger.error(f"Error retrieving hackathon details: {str(e)}")
        return None


async def list_featured(zerodb: ZeroDBClient, include_hackathon_details: bool = True) -> Dict:
    """
    List all featured hackathons ordered by display_order.

    Filters out:
    - Inactive entries (is_active = false)
    - Expired entries (featured_until < now)

    Args:
        zerodb: ZeroDB client instance
        include_hackathon_details: Whether to include full hackathon data

    Returns:
        Dict with featured list and total count

    Raises:
        HTTPException: If database error occurs
    """
    try:
        response = await zerodb.tables.query_rows(
            table_id="featured_hackathons",
            filter={"is_active": True},
            limit=1000
        )

        featured_entries = response.get("rows", [])
        now = datetime.utcnow()

        # Filter out expired entries
        active_featured = []
        for entry in featured_entries:
            if entry.get("featured_until"):
                try:
                    expiry = datetime.fromisoformat(entry["featured_until"].replace('Z', '+00:00'))
                    if expiry.replace(tzinfo=None) < now:
                        continue  # Skip expired
                except Exception as e:
                    logger.warning(f"Invalid featured_until format for {entry.get('id')}: {e}")
            active_featured.append(entry)

        # Enrich with hackathon details if requested
        if include_hackathon_details:
            for entry in active_featured:
                hackathon = await get_hackathon_details(entry["hackathon_id"], zerodb)
                entry["hackathon"] = hackathon

        # Sort by display_order
        active_featured.sort(key=lambda x: x.get("display_order", 999))

        return {
            "featured": active_featured,
            "total": len(active_featured)
        }

    except Exception as e:
        logger.error(f"Error listing featured hackathons: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list featured hackathons: {str(e)}"
        )


async def update_featured(
    featured_id: str,
    update_data: Dict,
    zerodb: ZeroDBClient
) -> Dict:
    """
    Update a featured entry's details.

    Args:
        featured_id: UUID of the featured entry
        update_data: Dict of fields to update
        zerodb: ZeroDB client instance

    Returns:
        Updated featured entry data

    Raises:
        HTTPException: If featured entry not found or database error
    """
    # Get current featured entry
    featured = await get_featured(featured_id, zerodb)

    try:
        # Merge updates
        update_data["updated_at"] = datetime.utcnow().isoformat()
        featured.update(update_data)

        # Update in database
        await zerodb.tables.update_rows(
            table_id="featured_hackathons",
            filter={"id": featured_id},
            update={"$set": update_data}
        )

        logger.info(f"Updated featured entry {featured_id}")
        return featured

    except Exception as e:
        logger.error(f"Error updating featured entry: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update featured entry: {str(e)}"
        )


async def update_featured_order(
    featured_id: str,
    new_order: int,
    zerodb: ZeroDBClient
) -> Dict:
    """
    Update a featured entry's display order.

    Args:
        featured_id: UUID of the featured entry
        new_order: New display order
        zerodb: ZeroDB client instance

    Returns:
        Updated featured entry data

    Raises:
        HTTPException: If featured entry not found or database error
    """
    return await update_featured(featured_id, {"display_order": new_order}, zerodb)


async def delete_featured(featured_id: str, zerodb: ZeroDBClient) -> None:
    """
    Delete a featured entry (unfeature a hackathon).

    Args:
        featured_id: UUID of the featured entry
        zerodb: ZeroDB client instance

    Raises:
        HTTPException: If featured entry not found or database error
    """
    # Verify featured entry exists
    await get_featured(featured_id, zerodb)

    try:
        await zerodb.tables.delete_rows(
            table_id="featured_hackathons",
            filter={"id": featured_id}
        )

        logger.info(f"Deleted featured entry {featured_id}")

    except Exception as e:
        logger.error(f"Error deleting featured entry: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete featured entry: {str(e)}"
        )
