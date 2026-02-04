"""
Invitations API Routes

RESTful API endpoints for hackathon invitation management.
Supports email-based invitations with secure token generation.
"""

import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_current_user_optional, get_zerodb_client
from api.schemas.invitation import (
    ErrorResponse,
    InvitationAcceptRequest,
    InvitationCreateRequest,
    InvitationDeclineRequest,
    InvitationListResponse,
    InvitationResponse,
)
from integrations.zerodb.client import ZeroDBClient
from services import invitation_service


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1",
    tags=["Invitations"],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)


@router.post(
    "/hackathons/{hackathon_id}/invitations",
    response_model=InvitationListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create invitations",
    description="""
    Create invitation(s) for hackathon participants.

    **Authentication Required:** Yes
    **Permissions:** ORGANIZER role for the hackathon

    Sends invitation emails with secure tokens that expire in 7 days.
    Prevents duplicate invitations for the same email+hackathon.
    """,
)
async def create_invitations(
    hackathon_id: str,
    request: InvitationCreateRequest,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> InvitationListResponse:
    """Create one or more invitations."""
    logger.info(
        f"User {current_user['id']} creating {len(request.emails)} invitation(s) "
        f"for hackathon {hackathon_id} with role {request.role}"
    )

    result = await invitation_service.create_invitations(
        zerodb_client=zerodb,
        hackathon_id=hackathon_id,
        emails=request.emails,
        role=request.role.value,
        invited_by=current_user["id"],
    )

    return InvitationListResponse(
        invitations=[InvitationResponse(**inv) for inv in result["invitations"]],
        total=result["total"],
        created=result["created"],
        skipped=result.get("skipped", 0),
    )


@router.get(
    "/hackathons/{hackathon_id}/invitations",
    response_model=InvitationListResponse,
    summary="List invitations",
    description="""
    List all invitations for a hackathon.

    **Authentication Required:** Yes
    **Permissions:** ORGANIZER role for the hackathon
    """,
)
async def list_invitations(
    hackathon_id: str,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> InvitationListResponse:
    """List all invitations for a hackathon."""
    logger.info(f"User {current_user['id']} listing invitations for hackathon {hackathon_id}")

    result = await invitation_service.list_invitations(
        zerodb_client=zerodb,
        hackathon_id=hackathon_id,
        user_id=current_user["id"],
    )

    return InvitationListResponse(
        invitations=[InvitationResponse(**inv) for inv in result["invitations"]],
        total=result["total"],
        created=0,
        skipped=0,
    )


@router.get(
    "/invitations/{invitation_id}",
    response_model=InvitationResponse,
    summary="Get invitation",
    description="""
    Get a single invitation by ID.

    **Authentication Required:** Yes
    **Permissions:** ORGANIZER who created it, or invited user
    """,
)
async def get_invitation(
    invitation_id: str,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> InvitationResponse:
    """Get a single invitation."""
    logger.info(f"User {current_user['id']} retrieving invitation {invitation_id}")

    invitation = await invitation_service.get_invitation(
        zerodb_client=zerodb,
        invitation_id=invitation_id,
        user_id=current_user["id"],
    )

    return InvitationResponse(**invitation)


@router.get(
    "/invitations/token/{token}",
    response_model=InvitationResponse,
    summary="Get invitation by token (PUBLIC)",
    description="""
    Get invitation details by token.

    **Authentication Required:** NO (public endpoint)
    **Permissions:** Anyone with the token

    Used by invitation recipients to view invitation details before accepting.
    """,
)
async def get_invitation_by_token(
    token: str,
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> InvitationResponse:
    """Get invitation by token (public access)."""
    logger.info(f"Anonymous user retrieving invitation by token")

    invitation = await invitation_service.get_invitation_by_token(
        zerodb_client=zerodb,
        token=token,
    )

    return InvitationResponse(**invitation)


@router.post(
    "/invitations/accept",
    response_model=InvitationResponse,
    summary="Accept invitation (PUBLIC)",
    description="""
    Accept a hackathon invitation using the token.

    **Authentication Required:** NO (public endpoint)
    **Permissions:** Anyone with valid token

    Auto-provisions participant record and adds to hackathon with specified role.
    """,
)
async def accept_invitation(
    request: InvitationAcceptRequest,
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> InvitationResponse:
    """Accept an invitation."""
    logger.info(f"Accepting invitation with token (email: {request.email})")

    invitation = await invitation_service.accept_invitation(
        zerodb_client=zerodb,
        token=request.token,
        email=request.email,
        name=request.name,
    )

    return InvitationResponse(**invitation)


@router.post(
    "/invitations/decline",
    response_model=InvitationResponse,
    summary="Decline invitation (PUBLIC)",
    description="""
    Decline a hackathon invitation.

    **Authentication Required:** NO (public endpoint)
    **Permissions:** Anyone with valid token
    """,
)
async def decline_invitation(
    request: InvitationDeclineRequest,
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> InvitationResponse:
    """Decline an invitation."""
    logger.info(f"Declining invitation with token")

    invitation = await invitation_service.decline_invitation(
        zerodb_client=zerodb,
        token=request.token,
    )

    return InvitationResponse(**invitation)


@router.post(
    "/invitations/{invitation_id}/resend",
    response_model=InvitationResponse,
    summary="Resend invitation email",
    description="""
    Resend invitation email with fresh expiration date.

    **Authentication Required:** Yes
    **Permissions:** ORGANIZER who created the invitation
    """,
)
async def resend_invitation(
    invitation_id: str,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> InvitationResponse:
    """Resend an invitation email."""
    logger.info(f"User {current_user['id']} resending invitation {invitation_id}")

    invitation = await invitation_service.resend_invitation(
        zerodb_client=zerodb,
        invitation_id=invitation_id,
        user_id=current_user["id"],
    )

    return InvitationResponse(**invitation)


@router.delete(
    "/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel invitation",
    description="""
    Cancel a pending invitation.

    **Authentication Required:** Yes
    **Permissions:** ORGANIZER who created the invitation

    Can only cancel PENDING invitations.
    """,
)
async def cancel_invitation(
    invitation_id: str,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> None:
    """Cancel an invitation."""
    logger.info(f"User {current_user['id']} canceling invitation {invitation_id}")

    await invitation_service.cancel_invitation(
        zerodb_client=zerodb,
        invitation_id=invitation_id,
        user_id=current_user["id"],
    )

    return None
