"""
Invitation Service

Provides business logic for hackathon invitation management including
token generation, expiration handling, and participant provisioning.
"""

import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

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

# Invitation token validity period
INVITATION_EXPIRY_DAYS = 7


async def create_invitations(
    zerodb_client: ZeroDBClient,
    hackathon_id: str,
    emails: List[str],
    role: str,
    invited_by: str,
) -> Dict[str, Any]:
    """
    Create invitation(s) for hackathon participants.

    Generates secure tokens for each invitation and stores them in the database.
    Prevents duplicate invitations for the same email+hackathon combination.

    Args:
        zerodb_client: ZeroDB client instance
        hackathon_id: UUID of the hackathon
        emails: List of email addresses to invite (normalized to lowercase)
        role: Role for invited participants (JUDGE, MENTOR, BUILDER)
        invited_by: User ID of the organizer sending invitations

    Returns:
        Dict with keys:
        - invitations: List of created invitation objects
        - created_count: Number of invitations created
        - skipped_count: Number skipped (duplicates)
        - skipped_emails: List of emails skipped

    Raises:
        HTTPException: 404 if hackathon not found
        HTTPException: 400 for validation errors
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 500ms for typical operations (1-10 invitations)

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> result = await create_invitations(
        ...     zerodb_client=client,
        ...     hackathon_id="hack-123",
        ...     emails=["judge1@example.com", "judge2@example.com"],
        ...     role="JUDGE",
        ...     invited_by="user-456"
        ... )
        >>> print(result['created_count'])
        2
    """
    try:
        # Step 1: Validate hackathon exists
        logger.debug(f"Validating hackathon {hackathon_id} exists")
        hackathons = await zerodb_client.tables.query_rows(
            "hackathons",
            filter={"hackathon_id": hackathon_id, "is_deleted": False},
        )

        if not hackathons or len(hackathons) == 0:
            logger.warning(f"Hackathon {hackathon_id} not found")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Hackathon {hackathon_id} not found",
            )

        # Step 2: Validate role
        valid_roles = ["JUDGE", "MENTOR", "BUILDER"]
        if role not in valid_roles:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{role}'. Must be one of: {', '.join(valid_roles)}",
            )

        # Step 3: Check for existing invitations and participants
        logger.debug(f"Checking for existing invitations for hackathon {hackathon_id}")
        existing_invitations = await zerodb_client.tables.query_rows(
            "invitations",
            filter={"hackathon_id": hackathon_id},
        )

        # Get existing participants to check if already joined
        existing_participants = await zerodb_client.tables.query_rows(
            "hackathon_participants",
            filter={"hackathon_id": hackathon_id},
        )

        # Build sets of existing emails (case-insensitive)
        invited_emails = {inv.get("email", "").lower() for inv in existing_invitations
                         if inv.get("status") in ["PENDING", "ACCEPTED"]}
        participant_emails = set()
        for p in existing_participants:
            metadata = p.get("metadata", {})
            email = metadata.get("ainative_user_email", "").lower()
            if email:
                participant_emails.add(email)

        # Step 4: Create invitations
        now = datetime.utcnow()
        expires_at = now + timedelta(days=INVITATION_EXPIRY_DAYS)

        created_invitations = []
        skipped_emails = []

        for email in emails:
            email_lower = email.lower()

            # Skip if already invited or already a participant
            if email_lower in invited_emails or email_lower in participant_emails:
                logger.info(f"Skipping duplicate invitation for {email}")
                skipped_emails.append(email)
                continue

            # Generate secure token
            token = secrets.token_urlsafe(32)
            invitation_id = str(uuid.uuid4())

            invitation_row = {
                "invitation_id": invitation_id,
                "hackathon_id": hackathon_id,
                "email": email_lower,
                "role": role,
                "token": token,
                "invited_by": invited_by,
                "status": "PENDING",
                "expires_at": expires_at.isoformat(),
                "accepted_at": None,
                "declined_at": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            logger.info(f"Creating invitation {invitation_id} for {email} as {role}")
            await zerodb_client.tables.insert_rows(
                "invitations",
                rows=[invitation_row],
            )

            created_invitations.append(invitation_row)
            invited_emails.add(email_lower)  # Add to set to prevent duplicates within this batch

            # TODO: Send email notification (integration point for email service)
            logger.info(f"Email would be sent to {email} with token {token}")

        logger.info(
            f"Created {len(created_invitations)} invitations for hackathon {hackathon_id}, "
            f"skipped {len(skipped_emails)}"
        )

        return {
            "invitations": created_invitations,
            "created_count": len(created_invitations),
            "skipped_count": len(skipped_emails),
            "skipped_emails": skipped_emails,
        }

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout creating invitations: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error creating invitations: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invitations. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error creating invitations: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invitations. Please contact support.",
        )


async def list_invitations(
    zerodb_client: ZeroDBClient,
    hackathon_id: str,
) -> Dict[str, Any]:
    """
    List all invitations for a hackathon.

    Retrieves all invitations regardless of status (PENDING, ACCEPTED, DECLINED, EXPIRED).

    Args:
        zerodb_client: ZeroDB client instance
        hackathon_id: UUID of the hackathon

    Returns:
        Dict with keys:
        - invitations: List of invitation objects
        - total: Total number of invitations

    Raises:
        HTTPException: 404 if hackathon not found
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 200ms for typical queries

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> result = await list_invitations(client, "hack-123")
        >>> print(result['total'])
        15
    """
    try:
        # Validate hackathon exists
        hackathons = await zerodb_client.tables.query_rows(
            "hackathons",
            filter={"hackathon_id": hackathon_id, "is_deleted": False},
        )

        if not hackathons or len(hackathons) == 0:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Hackathon {hackathon_id} not found",
            )

        # Query invitations
        logger.debug(f"Listing invitations for hackathon {hackathon_id}")
        invitations = await zerodb_client.tables.query_rows(
            "invitations",
            filter={"hackathon_id": hackathon_id},
        )

        logger.info(f"Retrieved {len(invitations)} invitations for hackathon {hackathon_id}")

        return {
            "invitations": invitations,
            "total": len(invitations),
        }

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout listing invitations: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error listing invitations: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list invitations. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error listing invitations: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list invitations. Please contact support.",
        )


async def get_invitation(
    zerodb_client: ZeroDBClient,
    invitation_id: str,
) -> Dict[str, Any]:
    """
    Get a single invitation by ID.

    Retrieves invitation details from ZeroDB.

    Args:
        zerodb_client: ZeroDB client instance
        invitation_id: UUID of the invitation

    Returns:
        Dict with invitation data

    Raises:
        HTTPException: 404 if invitation not found
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 100ms for typical queries

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> invitation = await get_invitation(client, "inv-123")
        >>> print(invitation['email'])
        'judge@example.com'
    """
    try:
        logger.debug(f"Retrieving invitation {invitation_id}")

        invitations = await zerodb_client.tables.query_rows(
            "invitations",
            filter={"invitation_id": invitation_id},
        )

        if not invitations or len(invitations) == 0:
            logger.warning(f"Invitation {invitation_id} not found")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Invitation {invitation_id} not found",
            )

        invitation = invitations[0]
        logger.info(f"Retrieved invitation {invitation_id}")
        return invitation

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout retrieving invitation {invitation_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error retrieving invitation {invitation_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invitation. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error retrieving invitation {invitation_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invitation. Please contact support.",
        )


async def get_invitation_by_token(
    zerodb_client: ZeroDBClient,
    token: str,
) -> Dict[str, Any]:
    """
    Get invitation by token (PUBLIC endpoint).

    Validates token and checks expiration. This is a public endpoint
    used by invitation email recipients.

    Args:
        zerodb_client: ZeroDB client instance
        token: Invitation token from email link

    Returns:
        Dict with invitation data

    Raises:
        HTTPException: 404 if token not found or invitation expired
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 100ms for typical queries

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> invitation = await get_invitation_by_token(client, "abc123...")
        >>> print(invitation['role'])
        'JUDGE'
    """
    try:
        logger.debug(f"Retrieving invitation by token")

        invitations = await zerodb_client.tables.query_rows(
            "invitations",
            filter={"token": token},
        )

        if not invitations or len(invitations) == 0:
            logger.warning(f"Invitation token not found")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Invalid invitation token",
            )

        invitation = invitations[0]

        # Check if expired
        expires_at_str = invitation.get("expires_at")
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if datetime.utcnow() > expires_at:
                # Update status to EXPIRED if still PENDING
                if invitation.get("status") == "PENDING":
                    await zerodb_client.tables.update_rows(
                        "invitations",
                        filter={"invitation_id": invitation["invitation_id"]},
                        update={"$set": {"status": "EXPIRED", "updated_at": datetime.utcnow().isoformat()}},
                    )
                    invitation["status"] = "EXPIRED"

                logger.warning(f"Invitation token expired")
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail="Invitation has expired",
                )

        logger.info(f"Retrieved invitation by token for {invitation.get('email')}")
        return invitation

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout retrieving invitation by token: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error retrieving invitation by token: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invitation. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error retrieving invitation by token: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invitation. Please contact support.",
        )


async def accept_invitation(
    zerodb_client: ZeroDBClient,
    token: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Accept an invitation (PUBLIC endpoint).

    Validates token, creates participant record, and updates invitation status.
    This auto-provisions the user as a participant in the hackathon.

    Args:
        zerodb_client: ZeroDB client instance
        token: Invitation token
        user_id: User ID from authentication

    Returns:
        Dict with success message and updated invitation

    Raises:
        HTTPException: 404 if token invalid/expired
        HTTPException: 400 if already accepted/declined
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 300ms for typical operations

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> result = await accept_invitation(client, "abc123...", "user-456")
        >>> print(result['success'])
        True
    """
    try:
        # Get and validate invitation
        invitation = await get_invitation_by_token(zerodb_client, token)

        # Check if already accepted or declined
        status = invitation.get("status")
        if status == "ACCEPTED":
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invitation has already been accepted",
            )
        if status == "DECLINED":
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invitation has already been declined",
            )
        if status == "EXPIRED":
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invitation has expired",
            )

        # Check if user is already a participant
        hackathon_id = invitation.get("hackathon_id")
        existing_participants = await zerodb_client.tables.query_rows(
            "hackathon_participants",
            filter={"hackathon_id": hackathon_id, "user_id": user_id},
        )

        if existing_participants and len(existing_participants) > 0:
            logger.warning(f"User {user_id} already a participant in hackathon {hackathon_id}")
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="User is already a participant in this hackathon",
            )

        # Create participant record
        now = datetime.utcnow()
        participant_id = str(uuid.uuid4())
        participant_row = {
            "participant_id": participant_id,
            "hackathon_id": hackathon_id,
            "user_id": user_id,
            "role": invitation.get("role"),
            "status": "approved",
            "joined_at": now.isoformat(),
        }

        logger.info(f"Creating participant {participant_id} for user {user_id} in hackathon {hackathon_id}")
        await zerodb_client.tables.insert_rows(
            "hackathon_participants",
            rows=[participant_row],
        )

        # Update invitation status
        await zerodb_client.tables.update_rows(
            "invitations",
            filter={"invitation_id": invitation["invitation_id"]},
            update={
                "$set": {
                    "status": "ACCEPTED",
                    "accepted_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
            },
        )

        # Fetch updated invitation
        updated_invitation = await get_invitation(zerodb_client, invitation["invitation_id"])

        logger.info(f"User {user_id} accepted invitation {invitation['invitation_id']}")

        return {
            "success": True,
            "message": f"Successfully joined hackathon as {invitation.get('role')}",
            "invitation": updated_invitation,
        }

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout accepting invitation: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error accepting invitation: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept invitation. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error accepting invitation: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept invitation. Please contact support.",
        )


async def decline_invitation(
    zerodb_client: ZeroDBClient,
    token: str,
) -> Dict[str, Any]:
    """
    Decline an invitation (PUBLIC endpoint).

    Validates token and updates invitation status to DECLINED.

    Args:
        zerodb_client: ZeroDB client instance
        token: Invitation token

    Returns:
        Dict with success message and updated invitation

    Raises:
        HTTPException: 404 if token invalid/expired
        HTTPException: 400 if already accepted/declined
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 200ms for typical operations

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> result = await decline_invitation(client, "abc123...")
        >>> print(result['success'])
        True
    """
    try:
        # Get and validate invitation
        invitation = await get_invitation_by_token(zerodb_client, token)

        # Check if already accepted or declined
        status = invitation.get("status")
        if status == "ACCEPTED":
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invitation has already been accepted",
            )
        if status == "DECLINED":
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invitation has already been declined",
            )

        # Update invitation status
        now = datetime.utcnow()
        await zerodb_client.tables.update_rows(
            "invitations",
            filter={"invitation_id": invitation["invitation_id"]},
            update={
                "$set": {
                    "status": "DECLINED",
                    "declined_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
            },
        )

        # Fetch updated invitation
        updated_invitation = await get_invitation(zerodb_client, invitation["invitation_id"])

        logger.info(f"Invitation {invitation['invitation_id']} declined")

        return {
            "success": True,
            "message": "Invitation declined successfully",
            "invitation": updated_invitation,
        }

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout declining invitation: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error declining invitation: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decline invitation. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error declining invitation: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decline invitation. Please contact support.",
        )


async def cancel_invitation(
    zerodb_client: ZeroDBClient,
    invitation_id: str,
    user_id: str,
    hackathon_id: str,
) -> Dict[str, Any]:
    """
    Cancel an invitation (ORGANIZER only).

    Deletes invitation if still pending. Cannot cancel accepted invitations.

    Args:
        zerodb_client: ZeroDB client instance
        invitation_id: UUID of the invitation
        user_id: User ID attempting cancellation
        hackathon_id: Hackathon ID for authorization check

    Returns:
        Dict with deletion confirmation

    Raises:
        HTTPException: 403 if user is not ORGANIZER
        HTTPException: 404 if invitation not found
        HTTPException: 400 if invitation already accepted
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 200ms for typical operations

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> result = await cancel_invitation(client, "inv-123", "user-456", "hack-789")
        >>> print(result['success'])
        True
    """
    try:
        # Authorization is checked in the route handler via check_organizer

        # Get invitation
        invitation = await get_invitation(zerodb_client, invitation_id)

        # Verify invitation belongs to specified hackathon
        if invitation.get("hackathon_id") != hackathon_id:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Invitation {invitation_id} not found in hackathon {hackathon_id}",
            )

        # Check if already accepted (cannot cancel accepted invitations)
        if invitation.get("status") == "ACCEPTED":
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel an accepted invitation. Remove participant instead.",
            )

        # Delete invitation
        logger.info(f"Cancelling invitation {invitation_id}")
        # Note: Using delete_rows if available, otherwise update status to CANCELLED
        try:
            # Try to use delete operation
            await zerodb_client.tables.update_rows(
                "invitations",
                filter={"invitation_id": invitation_id},
                update={"$set": {"status": "CANCELLED", "updated_at": datetime.utcnow().isoformat()}},
            )
        except Exception:
            # If delete not supported, update status
            await zerodb_client.tables.update_rows(
                "invitations",
                filter={"invitation_id": invitation_id},
                update={"$set": {"status": "CANCELLED", "updated_at": datetime.utcnow().isoformat()}},
            )

        logger.info(f"Successfully cancelled invitation {invitation_id}")

        return {
            "success": True,
            "invitation_id": invitation_id,
            "message": "Invitation cancelled successfully",
        }

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout cancelling invitation {invitation_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error cancelling invitation {invitation_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel invitation. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error cancelling invitation {invitation_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel invitation. Please contact support.",
        )


async def resend_invitation(
    zerodb_client: ZeroDBClient,
    invitation_id: str,
    user_id: str,
    hackathon_id: str,
) -> Dict[str, Any]:
    """
    Resend invitation email (ORGANIZER only).

    Regenerates token and extends expiration for pending invitations.

    Args:
        zerodb_client: ZeroDB client instance
        invitation_id: UUID of the invitation
        user_id: User ID attempting resend
        hackathon_id: Hackathon ID for authorization check

    Returns:
        Dict with success message and updated invitation

    Raises:
        HTTPException: 403 if user is not ORGANIZER
        HTTPException: 404 if invitation not found
        HTTPException: 400 if invitation not pending
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 200ms for typical operations

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> result = await resend_invitation(client, "inv-123", "user-456", "hack-789")
        >>> print(result['success'])
        True
    """
    try:
        # Authorization is checked in the route handler via check_organizer

        # Get invitation
        invitation = await get_invitation(zerodb_client, invitation_id)

        # Verify invitation belongs to specified hackathon
        if invitation.get("hackathon_id") != hackathon_id:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Invitation {invitation_id} not found in hackathon {hackathon_id}",
            )

        # Check if invitation is pending or expired (can resend these)
        status = invitation.get("status")
        if status not in ["PENDING", "EXPIRED"]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot resend invitation with status {status}",
            )

        # Generate new token and extend expiration
        new_token = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        new_expires_at = now + timedelta(days=INVITATION_EXPIRY_DAYS)

        logger.info(f"Resending invitation {invitation_id}")
        await zerodb_client.tables.update_rows(
            "invitations",
            filter={"invitation_id": invitation_id},
            update={
                "$set": {
                    "token": new_token,
                    "status": "PENDING",
                    "expires_at": new_expires_at.isoformat(),
                    "updated_at": now.isoformat(),
                }
            },
        )

        # Fetch updated invitation
        updated_invitation = await get_invitation(zerodb_client, invitation_id)

        # TODO: Send email notification (integration point for email service)
        logger.info(f"Email would be resent to {invitation.get('email')} with token {new_token}")

        logger.info(f"Successfully resent invitation {invitation_id}")

        return {
            "success": True,
            "message": "Invitation resent successfully",
            "invitation": updated_invitation,
        }

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout resending invitation {invitation_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error resending invitation {invitation_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend invitation. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error resending invitation {invitation_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend invitation. Please contact support.",
        )
