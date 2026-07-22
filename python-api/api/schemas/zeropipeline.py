"""
Pydantic schemas for ZeroPipeline CRM integration endpoints.

Defines request and response models for ZeroPipeline integration operations
including pipeline, deal, customer, and analytics data.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ZeroPipelineConnectRequest(BaseModel):
    """Request schema for connecting a ZeroPipeline account via API key."""
    api_key: str = Field(..., min_length=10, description="ZeroPipeline API key")


class ZeroPipelineSyncOptionsRequest(BaseModel):
    """Request schema for updating ZeroPipeline sync preferences."""
    pipelines: bool = Field(default=True, description="Sync pipelines from ZeroPipeline")
    deals: bool = Field(default=True, description="Sync deals from ZeroPipeline")
    customers: bool = Field(default=True, description="Sync customers from ZeroPipeline")
    tasks: bool = Field(default=False, description="Sync tasks from ZeroPipeline")


class ImportCustomersRequest(BaseModel):
    """Request schema for importing ZeroPipeline customers as hackathon participants."""
    pipeline_id: Optional[str] = Field(
        default=None, description="Optional pipeline ID to filter customers by"
    )
    hackathon_id: str = Field(..., description="Target hackathon ID")


class ZeroPipelineConnectResponse(BaseModel):
    """Response schema for a successful ZeroPipeline connection."""
    success: bool
    integration_id: str
    account_name: Optional[str] = None
    status: str
    message: str


class ZeroPipelineStatusResponse(BaseModel):
    """Response schema for ZeroPipeline connection status."""
    connected: bool
    integration_id: Optional[str] = None
    account_name: Optional[str] = None
    status: Optional[str] = None
    sync_options: Optional[dict] = None
    last_synced_at: Optional[str] = None


class PipelineSummary(BaseModel):
    """Summary of a single ZeroPipeline pipeline."""
    pipeline_id: str
    name: str
    stage_count: int = 0
    deal_count: int = 0


class PipelinesListResponse(BaseModel):
    """Response schema for listing ZeroPipeline pipelines."""
    pipelines: list[PipelineSummary]
    total: int


class DealSummary(BaseModel):
    """Summary of a single ZeroPipeline deal."""
    deal_id: str
    title: str
    value: Optional[float] = None
    currency: Optional[str] = "USD"
    stage: Optional[str] = None
    status: Optional[str] = None
    customer_name: Optional[str] = None


class DealsListResponse(BaseModel):
    """Response schema for listing ZeroPipeline deals."""
    deals: list[DealSummary]
    total: int


class CustomerSummary(BaseModel):
    """Summary of a single ZeroPipeline customer."""
    customer_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None


class CustomersListResponse(BaseModel):
    """Response schema for listing ZeroPipeline customers."""
    customers: list[CustomerSummary]
    total: int


class ImportCustomersResponse(BaseModel):
    """Response schema for importing customers into a hackathon."""
    success: bool
    imported: int
    skipped: int
    total: int
    message: str


class DashboardSummaryResponse(BaseModel):
    """Response schema for ZeroPipeline analytics dashboard summary."""
    total_deals: int = 0
    total_customers: int = 0
    total_revenue: Optional[float] = None
    pipeline_count: int = 0
