"""
Participant Management Routes

API endpoints for hackathon participant operations.
"""

import logging
from typing import Optional
from uuid import UUID

from api.dependencies import get_current_user
from fastapi import APIRouter, Depends, HTTPException, Query, status
from integrations.zerodb.client import ZeroDBClient
from models.participants import (
    InviteJudgesRequest,
    InviteJudgesResponse,
    JoinHackathonResponse,
    LeaveHackathonResponse,
    ListParticipantsResponse,
    ParticipantResponse,
)
from services.authorization import check_organizer
from services.participants_service import ParticipantsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/hackathons", tags=["Participants"])


def get_zerodb_client() -> ZeroDBClient:
    """
    Dependency to get ZeroDB client instance.

    Returns:
        Configured ZeroDB client
    """
    return ZeroDBClient()


@router.post(
    "/{hackathon_id}/join",
    response_model=JoinHackathonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join hackathon",
    description="Add current user as BUILDER participant to hackathon",
)
async def join_hackathon(
    hackathon_id: UUID,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> JoinHackathonResponse:
    """
    Join a hackathon as a BUILDER.

    - **hackathon_id**: UUID of hackathon to join

    Returns participant record with role = BUILDER.

    Raises:
    - 404: Hackathon not found
    - 409: User is already a participant
    """
    service = ParticipantsService(zerodb)

    participant = await service.join_hackathon(
        hackathon_id=str(hackathon_id),
        user_id=current_user["id"],
        user_email=current_user["email"],
        user_name=current_user.get("name", ""),
        role="BUILDER",
    )

    return JoinHackathonResponse(
        success=True,
        participant=ParticipantResponse(**participant),
        message=f"Successfully joined hackathon {hackathon_id}",
    )


@router.post(
    "/{hackathon_id}/invite-judges",
    response_model=InviteJudgesResponse,
    status_code=status.HTTP_200_OK,
    summary="Invite judges to hackathon",
    description="Invite judges by email (ORGANIZER only)",
)
async def invite_judges(
    hackathon_id: UUID,
    request: InviteJudgesRequest,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> InviteJudgesResponse:
    """
    Invite judges to hackathon (ORGANIZER only).

    - **hackathon_id**: UUID of hackathon
    - **emails**: List of judge email addresses (1-50)
    - **message**: Optional custom invitation message

    For MVP, this creates placeholder JUDGE participant records.
    In production, this would send email invitations.

    Raises:
    - 403: User is not an organizer for this hackathon
    - 404: Hackathon not found
    """
    # Check if user is organizer
    await check_organizer(zerodb, current_user["id"], str(hackathon_id))

    service = ParticipantsService(zerodb)

    result = await service.invite_judges(
        hackathon_id=str(hackathon_id),
        organizer_id=current_user["id"],
        judge_emails=[str(email) for email in request.emails],
        message=request.message,
    )

    return InviteJudgesResponse(
        success=True,
        invited_count=result["invited_count"],
        invited_emails=result["invited_emails"],
        message=f"Successfully invited {result['invited_count']} judges",
    )


@router.get(
    "/{hackathon_id}/participants",
    response_model=ListParticipantsResponse,
    status_code=status.HTTP_200_OK,
    summary="List hackathon participants",
    description="Get all participants in a hackathon, optionally filtered by role",
)
async def list_participants(
    hackathon_id: UUID,
    role: Optional[str] = Query(
        None,
        description="Filter by role (BUILDER, ORGANIZER, JUDGE, MENTOR)",
        regex="^(BUILDER|ORGANIZER|JUDGE|MENTOR)$",
    ),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> ListParticipantsResponse:
    """
    List all participants in a hackathon.

    - **hackathon_id**: UUID of hackathon
    - **role**: Optional role filter (BUILDER, ORGANIZER, JUDGE, MENTOR)

    This endpoint is public (no authentication required) to allow
    viewing participant lists.

    Returns list of participants with email and name enriched from metadata.
    """
    service = ParticipantsService(zerodb)

    participants = await service.list_participants(
        hackathon_id=str(hackathon_id),
        role=role,
    )

    participant_models = [ParticipantResponse(**p) for p in participants]

    return ListParticipantsResponse(
        hackathon_id=str(hackathon_id),
        total_count=len(participant_models),
        participants=participant_models,
    )


@router.delete(
    "/{hackathon_id}/leave",
    response_model=LeaveHackathonResponse,
    status_code=status.HTTP_200_OK,
    summary="Leave hackathon",
    description="Remove current user from hackathon participants",
)
async def leave_hackathon(
    hackathon_id: UUID,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> LeaveHackathonResponse:
    """
    Leave a hackathon.

    - **hackathon_id**: UUID of hackathon to leave

    Business rule: Users cannot leave after submitting a project.

    Raises:
    - 404: User is not a participant
    - 409: User has submitted a project (cannot leave)
    """
    service = ParticipantsService(zerodb)

    await service.leave_hackathon(
        hackathon_id=str(hackathon_id),
        user_id=current_user["id"],
    )

    return LeaveHackathonResponse(
        success=True,
        message=f"Successfully left hackathon {hackathon_id}",
    )
