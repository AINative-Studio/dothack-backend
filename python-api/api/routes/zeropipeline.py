"""
API routes for ZeroPipeline CRM integration.

Provides endpoints for connecting, syncing, and importing data from ZeroPipeline.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_current_user, get_zerodb_client
from api.schemas.zeropipeline import (
    CustomersListResponse,
    DashboardSummaryResponse,
    DealsListResponse,
    ImportCustomersRequest,
    ImportCustomersResponse,
    PipelinesListResponse,
    ZeroPipelineConnectRequest,
    ZeroPipelineConnectResponse,
    ZeroPipelineStatusResponse,
    ZeroPipelineSyncOptionsRequest,
)
from integrations.zerodb.client import ZeroDBClient
from services.zeropipeline_integration_service import ZeroPipelineIntegrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])


@router.post(
    "/zeropipeline/connect",
    response_model=ZeroPipelineConnectResponse,
    responses={
        400: {"description": "Invalid ZeroPipeline API key"},
        401: {"description": "Not authenticated"},
        502: {"description": "ZeroPipeline API unreachable"},
    },
)
async def connect_zeropipeline(
    request: ZeroPipelineConnectRequest,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """Connect a ZeroPipeline account by verifying and storing an API key."""
    logger.info(f"User {current_user.get('id')} connecting ZeroPipeline integration")
    svc = ZeroPipelineIntegrationService(zerodb)
    result = await svc.connect(current_user["id"], request.api_key)
    return ZeroPipelineConnectResponse(**result)


@router.get(
    "/zeropipeline/status",
    response_model=ZeroPipelineStatusResponse,
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def get_zeropipeline_status(
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """Get the current ZeroPipeline connection status for the authenticated user."""
    svc = ZeroPipelineIntegrationService(zerodb)
    result = await svc.get_status(current_user["id"])
    return ZeroPipelineStatusResponse(**result)


@router.delete(
    "/zeropipeline/disconnect",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "ZeroPipeline not connected"},
    },
)
async def disconnect_zeropipeline(
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """Disconnect the ZeroPipeline integration and delete the stored API key."""
    logger.info(f"User {current_user.get('id')} disconnecting ZeroPipeline integration")
    svc = ZeroPipelineIntegrationService(zerodb)
    return await svc.disconnect(current_user["id"])


@router.put(
    "/zeropipeline/sync-options",
    response_model=ZeroPipelineStatusResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "ZeroPipeline not connected"},
    },
)
async def update_zeropipeline_sync_options(
    request: ZeroPipelineSyncOptionsRequest,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """Update which data types are synced from ZeroPipeline."""
    svc = ZeroPipelineIntegrationService(zerodb)
    options = request.model_dump()
    result = await svc.update_sync_options(current_user["id"], options)
    return ZeroPipelineStatusResponse(**result)


@router.get(
    "/zeropipeline/pipelines",
    response_model=PipelinesListResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "ZeroPipeline not connected"},
    },
)
async def list_zeropipeline_pipelines(
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """List pipelines from the user's connected ZeroPipeline account."""
    svc = ZeroPipelineIntegrationService(zerodb)
    result = await svc.list_pipelines(current_user["id"])
    return PipelinesListResponse(**result)


@router.get(
    "/zeropipeline/deals",
    response_model=DealsListResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "ZeroPipeline not connected"},
    },
)
async def list_zeropipeline_deals(
    pipeline_id: Optional[str] = Query(default=None, description="Filter deals by pipeline ID"),
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """List deals from the user's connected ZeroPipeline account."""
    svc = ZeroPipelineIntegrationService(zerodb)
    result = await svc.list_deals(current_user["id"], pipeline_id=pipeline_id)
    return DealsListResponse(**result)


@router.get(
    "/zeropipeline/customers",
    response_model=CustomersListResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "ZeroPipeline not connected"},
    },
)
async def list_zeropipeline_customers(
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """List customers from the user's connected ZeroPipeline account."""
    svc = ZeroPipelineIntegrationService(zerodb)
    result = await svc.list_customers(current_user["id"])
    return CustomersListResponse(**result)


@router.post(
    "/zeropipeline/import-customers",
    response_model=ImportCustomersResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not an organizer of this hackathon"},
        404: {"description": "ZeroPipeline not connected"},
    },
)
async def import_zeropipeline_customers(
    request: ImportCustomersRequest,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """Import customers from ZeroPipeline into an existing hackathon as participants."""
    logger.info(
        f"User {current_user.get('id')} importing customers from ZeroPipeline "
        f"into hackathon {request.hackathon_id}"
    )
    svc = ZeroPipelineIntegrationService(zerodb)
    result = await svc.import_customers(
        current_user["id"], request.hackathon_id, pipeline_id=request.pipeline_id
    )
    return ImportCustomersResponse(**result)


@router.get(
    "/zeropipeline/dashboard",
    response_model=DashboardSummaryResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "ZeroPipeline not connected"},
    },
)
async def get_zeropipeline_dashboard(
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """Get analytics dashboard summary from ZeroPipeline."""
    svc = ZeroPipelineIntegrationService(zerodb)
    result = await svc.get_dashboard(current_user["id"])
    return DashboardSummaryResponse(**result)
