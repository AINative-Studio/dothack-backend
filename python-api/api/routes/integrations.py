"""
API routes for third-party integrations.

Provides endpoints for connecting, syncing, and importing data from Luma.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_current_user, get_zerodb_client
from api.schemas.integration import (
    ImportEventRequest,
    ImportEventResponse,
    LumaConnectRequest,
    LumaConnectResponse,
    LumaContactsListResponse,
    LumaEventsListResponse,
    LumaStatusResponse,
    SyncGuestsRequest,
    SyncGuestsResponse,
    SyncOptionsUpdateRequest,
)
from integrations.zerodb.client import ZeroDBClient
from services.luma_integration_service import LumaIntegrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])


@router.post(
    "/luma/connect",
    response_model=LumaConnectResponse,
    responses={
        400: {"description": "Invalid Luma API key"},
        401: {"description": "Not authenticated"},
        502: {"description": "Luma API unreachable"},
    },
)
async def connect_luma(
    request: LumaConnectRequest,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """Connect a Luma account by verifying and storing an API key."""
    logger.info(f"User {current_user.get('id')} connecting Luma integration")
    svc = LumaIntegrationService(zerodb)
    result = await svc.connect(current_user["id"], request.api_key)
    return LumaConnectResponse(**result)


@router.get(
    "/luma/status",
    response_model=LumaStatusResponse,
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def get_luma_status(
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """Get the current Luma connection status for the authenticated user."""
    svc = LumaIntegrationService(zerodb)
    result = await svc.get_status(current_user["id"])
    return LumaStatusResponse(**result)


@router.delete(
    "/luma/disconnect",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Luma not connected"},
    },
)
async def disconnect_luma(
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """Disconnect the Luma integration and delete the stored API key."""
    logger.info(f"User {current_user.get('id')} disconnecting Luma integration")
    svc = LumaIntegrationService(zerodb)
    return await svc.disconnect(current_user["id"])


@router.put(
    "/luma/sync-options",
    response_model=LumaStatusResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Luma not connected"},
    },
)
async def update_sync_options(
    request: SyncOptionsUpdateRequest,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """Update which data types are synced from Luma."""
    svc = LumaIntegrationService(zerodb)
    options = request.model_dump()
    result = await svc.update_sync_options(current_user["id"], options)
    return LumaStatusResponse(**result)


@router.get(
    "/luma/events",
    response_model=LumaEventsListResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Luma not connected"},
    },
)
async def list_luma_events(
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """List events from the user's connected Luma calendar."""
    svc = LumaIntegrationService(zerodb)
    result = await svc.list_luma_events(current_user["id"])
    return LumaEventsListResponse(**result)


@router.post(
    "/luma/import-event",
    response_model=ImportEventResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Luma not connected"},
        502: {"description": "Luma API error"},
    },
)
async def import_luma_event(
    request: ImportEventRequest,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """Import a Luma event as a draft hackathon."""
    logger.info(
        f"User {current_user.get('id')} importing Luma event {request.luma_event_id}"
    )
    svc = LumaIntegrationService(zerodb)
    result = await svc.import_event(current_user["id"], request.luma_event_id)
    return ImportEventResponse(**result)


@router.post(
    "/luma/sync-guests",
    response_model=SyncGuestsResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not an organizer of this hackathon"},
        404: {"description": "Luma not connected"},
    },
)
async def sync_luma_guests(
    request: SyncGuestsRequest,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """Sync guests from a Luma event into an existing hackathon."""
    logger.info(
        f"User {current_user.get('id')} syncing guests from Luma event "
        f"{request.luma_event_id} into hackathon {request.hackathon_id}"
    )
    svc = LumaIntegrationService(zerodb)
    result = await svc.sync_guests(
        current_user["id"], request.luma_event_id, request.hackathon_id
    )
    return SyncGuestsResponse(**result)


@router.get(
    "/luma/contacts",
    response_model=LumaContactsListResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Luma not connected"},
    },
)
async def list_luma_contacts(
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """List historical contacts from the user's Luma calendar."""
    svc = LumaIntegrationService(zerodb)
    result = await svc.list_contacts(current_user["id"])
    return LumaContactsListResponse(**result)
