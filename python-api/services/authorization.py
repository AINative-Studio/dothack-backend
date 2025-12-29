"""
Authorization Service

Provides role-based access control for hackathon participants.
Queries ZeroDB hackathon_participants table to verify user roles.
"""

import logging
from typing import Literal

from fastapi import HTTPException, status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)

# Configure logger
logger = logging.getLogger(__name__)

# Type for valid roles
RoleType = Literal["organizer", "judge", "builder"]


async def check_role(
    zerodb_client: ZeroDBClient,
    user_id: str,
    hackathon_id: str,
    required_role: RoleType,
) -> bool:
    """
    Check if user has required role for hackathon.

    Queries the hackathon_participants table in ZeroDB to verify that the user
    has the specified role for the given hackathon. Raises HTTPException if
    authorization fails.

    Args:
        zerodb_client: ZeroDB client instance
        user_id: User ID to check
        hackathon_id: Hackathon ID to check
        required_role: Role required (organizer, judge, or builder)

    Returns:
        True if user has the required role

    Raises:
        HTTPException: 403 if user doesn't have required role
        HTTPException: 500 if database error occurs
        HTTPException: 504 if request times out

    Performance:
        Should complete in < 100ms for typical queries

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> await check_role(client, "user-123", "hack-456", "organizer")
        True
    """
    try:
        # Query hackathon_participants table
        rows = await zerodb_client.tables.query_rows(
            "hackathon_participants",
            filter={
                "user_id": user_id,
                "hackathon_id": hackathon_id,
            },
        )

        # Check if user is a participant
        if not rows or len(rows) == 0:
            logger.warning(
                f"Authorization failed: User {user_id} is not a participant "
                f"in hackathon {hackathon_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a participant in this hackathon",
            )

        # Check if user has required role
        participant = rows[0]
        user_role = participant.get("role")

        if user_role != required_role:
            logger.warning(
                f"Authorization failed: User {user_id} has role '{user_role}' "
                f"but requires '{required_role}' for hackathon {hackathon_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}",
            )

        # Authorization successful
        logger.info(
            f"Authorization successful: User {user_id} has role '{required_role}' "
            f"for hackathon {hackathon_id}"
        )
        return True

    except HTTPException:
        # Re-raise HTTPException as-is (from authorization failures above)
        raise

    except ZeroDBTimeoutError as e:
        logger.error(
            f"Timeout checking authorization for user {user_id} "
            f"in hackathon {hackathon_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Authorization check timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error checking authorization for user {user_id} "
            f"in hackathon {hackathon_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify permissions. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error checking authorization for user {user_id} "
            f"in hackathon {hackathon_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify permissions. Please contact support.",
        )


async def check_organizer(
    zerodb_client: ZeroDBClient,
    user_id: str,
    hackathon_id: str,
) -> bool:
    """
    Check if user is an organizer for the hackathon.

    Convenience wrapper around check_role() for organizer role.

    Args:
        zerodb_client: ZeroDB client instance
        user_id: User ID to check
        hackathon_id: Hackathon ID to check

    Returns:
        True if user is an organizer

    Raises:
        HTTPException: 403 if user is not an organizer

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> await check_organizer(client, "user-123", "hack-456")
        True
    """
    return await check_role(
        zerodb_client=zerodb_client,
        user_id=user_id,
        hackathon_id=hackathon_id,
        required_role="organizer",
    )


async def check_judge(
    zerodb_client: ZeroDBClient,
    user_id: str,
    hackathon_id: str,
) -> bool:
    """
    Check if user is a judge for the hackathon.

    Convenience wrapper around check_role() for judge role.

    Args:
        zerodb_client: ZeroDB client instance
        user_id: User ID to check
        hackathon_id: Hackathon ID to check

    Returns:
        True if user is a judge

    Raises:
        HTTPException: 403 if user is not a judge

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> await check_judge(client, "user-789", "hack-456")
        True
    """
    return await check_role(
        zerodb_client=zerodb_client,
        user_id=user_id,
        hackathon_id=hackathon_id,
        required_role="judge",
    )


async def check_builder(
    zerodb_client: ZeroDBClient,
    user_id: str,
    hackathon_id: str,
) -> bool:
    """
    Check if user is a builder for the hackathon.

    Convenience wrapper around check_role() for builder role.

    Args:
        zerodb_client: ZeroDB client instance
        user_id: User ID to check
        hackathon_id: Hackathon ID to check

    Returns:
        True if user is a builder

    Raises:
        HTTPException: 403 if user is not a builder

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> await check_builder(client, "user-999", "hack-456")
        True
    """
    return await check_role(
        zerodb_client=zerodb_client,
        user_id=user_id,
        hackathon_id=hackathon_id,
        required_role="builder",
    )
