"""
Hackathon theme service for managing theme categories and statistics.

Handles CRUD operations, statistics calculation, and theme management.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status

from integrations.zerodb.client import ZeroDBClient


logger = logging.getLogger(__name__)


async def get_theme_by_name(
    theme_name: str,
    zerodb: ZeroDBClient,
    exclude_id: Optional[str] = None
) -> Optional[Dict]:
    """
    Get theme by name for duplicate checking.

    Args:
        theme_name: Theme name to search for
        zerodb: ZeroDB client instance
        exclude_id: Theme ID to exclude from check (for updates)

    Returns:
        Theme dict if found, None otherwise
    """
    try:
        response = await zerodb.tables.query_rows(
            table_id="hackathon_themes",
            filter={"theme_name": theme_name},
            limit=1
        )

        if response and response.get("rows"):
            theme = response["rows"][0]
            if exclude_id and theme.get("id") == exclude_id:
                return None
            return theme
        return None

    except Exception as e:
        logger.error(f"Error checking theme name: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check theme name: {str(e)}"
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
            table_id="hackathon_themes",
            filter={},
            limit=1000  # Get all themes
        )

        if not response or not response.get("rows"):
            return 1

        # Find max display_order
        max_order = max(
            (theme.get("display_order", 0) for theme in response["rows"]),
            default=0
        )
        return max_order + 1

    except Exception as e:
        logger.error(f"Error getting next display order: {str(e)}")
        return 1


async def create_theme(
    theme_name: str,
    description: Optional[str],
    icon: Optional[str],
    display_order: Optional[int],
    zerodb: ZeroDBClient
) -> Dict:
    """
    Create a new hackathon theme.

    Args:
        theme_name: Unique theme name
        description: Theme description
        icon: Icon emoji or name
        display_order: Display order (auto-assigned if not provided)
        zerodb: ZeroDB client instance

    Returns:
        Created theme data

    Raises:
        HTTPException: If theme name already exists or database error
    """
    # Check for duplicate theme name
    existing = await get_theme_by_name(theme_name, zerodb)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Theme '{theme_name}' already exists"
        )

    # Assign display order if not provided
    if display_order is None:
        display_order = await get_next_display_order(zerodb)

    try:
        theme_id = str(uuid4())
        now = datetime.utcnow().isoformat()

        theme_data = {
            "id": theme_id,
            "theme_name": theme_name,
            "description": description,
            "icon": icon,
            "hackathon_count": 0,
            "total_prizes": "0.00",
            "display_order": display_order,
            "created_at": now,
            "updated_at": now
        }

        await zerodb.tables.insert_rows(
            table_id="hackathon_themes",
            rows=[theme_data]
        )

        logger.info(f"Created theme {theme_id}: {theme_name}")
        return theme_data

    except Exception as e:
        logger.error(f"Error creating theme: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create theme: {str(e)}"
        )


async def get_theme(theme_id: str, zerodb: ZeroDBClient) -> Dict:
    """
    Get a theme by ID.

    Args:
        theme_id: UUID of the theme
        zerodb: ZeroDB client instance

    Returns:
        Theme data

    Raises:
        HTTPException: If theme not found or database error
    """
    try:
        response = await zerodb.tables.query_rows(
            table_id="hackathon_themes",
            filter={"id": theme_id},
            limit=1
        )

        if not response or not response.get("rows"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Theme {theme_id} not found"
            )

        return response["rows"][0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving theme: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve theme: {str(e)}"
        )


async def list_themes(zerodb: ZeroDBClient) -> Dict:
    """
    List all themes ordered by display_order.

    Args:
        zerodb: ZeroDB client instance

    Returns:
        Dict with themes list and total count

    Raises:
        HTTPException: If database error occurs
    """
    try:
        response = await zerodb.tables.query_rows(
            table_id="hackathon_themes",
            filter={},
            limit=1000
        )

        themes = response.get("rows", [])

        # Sort by display_order
        themes.sort(key=lambda x: x.get("display_order", 999))

        return {
            "themes": themes,
            "total": len(themes)
        }

    except Exception as e:
        logger.error(f"Error listing themes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list themes: {str(e)}"
        )


async def update_theme(
    theme_id: str,
    update_data: Dict,
    zerodb: ZeroDBClient
) -> Dict:
    """
    Update a theme's details.

    Args:
        theme_id: UUID of the theme
        update_data: Dict of fields to update
        zerodb: ZeroDB client instance

    Returns:
        Updated theme data

    Raises:
        HTTPException: If theme not found, duplicate name, or database error
    """
    # Get current theme
    theme = await get_theme(theme_id, zerodb)

    # Check for duplicate theme name if updating name
    if "theme_name" in update_data:
        existing = await get_theme_by_name(
            update_data["theme_name"],
            zerodb,
            exclude_id=theme_id
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Theme '{update_data['theme_name']}' already exists"
            )

    try:
        # Merge updates
        update_data["updated_at"] = datetime.utcnow().isoformat()
        theme.update(update_data)

        # Update in database
        await zerodb.tables.update_rows(
            table_id="hackathon_themes",
            filter={"id": theme_id},
            update={"$set": update_data}
        )

        logger.info(f"Updated theme {theme_id}")
        return theme

    except Exception as e:
        logger.error(f"Error updating theme: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update theme: {str(e)}"
        )


async def update_theme_order(
    theme_id: str,
    new_order: int,
    zerodb: ZeroDBClient
) -> Dict:
    """
    Update a theme's display order.

    Args:
        theme_id: UUID of the theme
        new_order: New display order
        zerodb: ZeroDB client instance

    Returns:
        Updated theme data

    Raises:
        HTTPException: If theme not found or database error
    """
    return await update_theme(theme_id, {"display_order": new_order}, zerodb)


async def delete_theme(theme_id: str, zerodb: ZeroDBClient) -> None:
    """
    Delete a theme.

    Args:
        theme_id: UUID of the theme
        zerodb: ZeroDB client instance

    Raises:
        HTTPException: If theme not found or database error
    """
    # Verify theme exists
    await get_theme(theme_id, zerodb)

    try:
        await zerodb.tables.delete_rows(
            table_id="hackathon_themes",
            filter={"id": theme_id}
        )

        logger.info(f"Deleted theme {theme_id}")

    except Exception as e:
        logger.error(f"Error deleting theme: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete theme: {str(e)}"
        )


async def refresh_theme_statistics(theme_id: str, zerodb: ZeroDBClient) -> Dict:
    """
    Refresh statistics for a theme by counting hackathons and summing prizes.

    Args:
        theme_id: UUID of the theme
        zerodb: ZeroDB client instance

    Returns:
        Updated theme data with refreshed statistics

    Raises:
        HTTPException: If theme not found or database error
    """
    # Get theme
    theme = await get_theme(theme_id, zerodb)

    try:
        # Query hackathons with this theme
        response = await zerodb.tables.query_rows(
            table_id="hackathons",
            filter={"theme_id": theme_id},
            limit=10000
        )

        hackathons = response.get("rows", [])
        hackathon_count = len(hackathons)

        # Sum prizes
        total_prizes = sum(
            Decimal(str(h.get("total_prizes", 0)))
            for h in hackathons
        )

        # Update theme statistics
        update_data = {
            "hackathon_count": hackathon_count,
            "total_prizes": str(total_prizes),
            "updated_at": datetime.utcnow().isoformat()
        }

        theme.update(update_data)

        await zerodb.tables.update_rows(
            table_id="hackathon_themes",
            filter={"id": theme_id},
            update={"$set": update_data}
        )

        logger.info(f"Refreshed statistics for theme {theme_id}: "
                   f"{hackathon_count} hackathons, ${total_prizes} prizes")
        return theme

    except Exception as e:
        logger.error(f"Error refreshing theme statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh statistics: {str(e)}"
        )


async def refresh_all_theme_statistics(zerodb: ZeroDBClient) -> List[Dict]:
    """
    Refresh statistics for all themes.

    Args:
        zerodb: ZeroDB client instance

    Returns:
        List of updated themes

    Raises:
        HTTPException: If database error occurs
    """
    try:
        # Get all themes
        themes_response = await list_themes(zerodb)
        themes = themes_response["themes"]

        # Refresh each theme
        updated_themes = []
        for theme in themes:
            try:
                updated_theme = await refresh_theme_statistics(theme["id"], zerodb)
                updated_themes.append(updated_theme)
            except Exception as e:
                logger.error(f"Failed to refresh theme {theme['id']}: {str(e)}")
                continue

        logger.info(f"Refreshed statistics for {len(updated_themes)} themes")
        return updated_themes

    except Exception as e:
        logger.error(f"Error refreshing all theme statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh all statistics: {str(e)}"
        )
