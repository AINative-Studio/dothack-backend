"""
Dashboard API Routes

Role-based dashboard aggregation endpoints for organizers, builders, and judges.
Provides summary statistics and recent activity feeds.
"""

import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_zerodb_client
from api.schemas.dashboard import (
    BuilderDashboardResponse,
    ErrorResponse,
    HackathonOverviewResponse,
    JudgeDashboardResponse,
    OrganizerDashboardResponse,
)
from integrations.zerodb.client import ZeroDBClient
from services import dashboard_service


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["Dashboard"],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)


@router.get(
    "/organizer",
    response_model=OrganizerDashboardResponse,
    summary="Organizer dashboard",
    description="""
    Get organizer dashboard with aggregated statistics.

    **Authentication Required:** Yes
    **Permissions:** User with ORGANIZER role

    Returns:
    - List of hackathons they organize
    - Total participants, teams, submissions
    - Pending judgments count
    - Recent activity feed
    """,
)
async def get_organizer_dashboard(
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> OrganizerDashboardResponse:
    """Get organizer dashboard."""
    logger.info(f"User {current_user['id']} accessing organizer dashboard")

    dashboard = await dashboard_service.get_organizer_dashboard(
        zerodb_client=zerodb,
        user_id=current_user["id"],
    )

    return OrganizerDashboardResponse(**dashboard)


@router.get(
    "/builder",
    response_model=BuilderDashboardResponse,
    summary="Builder dashboard",
    description="""
    Get builder dashboard with participation info.

    **Authentication Required:** Yes
    **Permissions:** User with BUILDER role

    Returns:
    - List of registered hackathons
    - My teams and submissions
    - Upcoming deadlines
    - Project status
    """,
)
async def get_builder_dashboard(
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> BuilderDashboardResponse:
    """Get builder dashboard."""
    logger.info(f"User {current_user['id']} accessing builder dashboard")

    dashboard = await dashboard_service.get_builder_dashboard(
        zerodb_client=zerodb,
        user_id=current_user["id"],
    )

    return BuilderDashboardResponse(**dashboard)


@router.get(
    "/judge",
    response_model=JudgeDashboardResponse,
    summary="Judge dashboard",
    description="""
    Get judge dashboard with judging assignments.

    **Authentication Required:** Yes
    **Permissions:** User with JUDGE role

    Returns:
    - Assigned hackathons
    - Submissions to judge
    - Completed judgments count
    - Pending submissions list
    """,
)
async def get_judge_dashboard(
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> JudgeDashboardResponse:
    """Get judge dashboard."""
    logger.info(f"User {current_user['id']} accessing judge dashboard")

    dashboard = await dashboard_service.get_judge_dashboard(
        zerodb_client=zerodb,
        user_id=current_user["id"],
    )

    return JudgeDashboardResponse(**dashboard)


@router.get(
    "/hackathons/{hackathon_id}",
    response_model=HackathonOverviewResponse,
    summary="Hackathon overview",
    description="""
    Get comprehensive hackathon overview with statistics.

    **Authentication Required:** Yes
    **Permissions:** ORGANIZER or ADMIN

    Returns:
    - Hackathon details
    - Participant/team/submission counts
    - Track distribution
    - Recent activity feed
    """,
)
async def get_hackathon_overview(
    hackathon_id: str,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> HackathonOverviewResponse:
    """Get hackathon overview dashboard."""
    logger.info(
        f"User {current_user['id']} accessing overview for hackathon {hackathon_id}"
    )

    dashboard = await dashboard_service.get_hackathon_overview(
        zerodb_client=zerodb,
        hackathon_id=hackathon_id,
        user_id=current_user["id"],
    )

    return HackathonOverviewResponse(**dashboard)
