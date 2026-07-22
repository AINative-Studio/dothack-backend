"""
Pydantic schemas for integration endpoints.

Defines request and response models for Luma integration operations.
"""

from typing import Optional

from pydantic import BaseModel, Field


class LumaConnectRequest(BaseModel):
    """Request schema for connecting a Luma account via API key."""
    api_key: str = Field(..., min_length=10, description="Luma API key")


class SyncOptionsUpdateRequest(BaseModel):
    """Request schema for updating sync preferences."""
    events: bool = Field(default=True, description="Sync events from Luma")
    guests: bool = Field(default=True, description="Sync guests from Luma events")
    contacts: bool = Field(default=False, description="Sync contacts from Luma")


class ImportEventRequest(BaseModel):
    """Request schema for importing a Luma event as a hackathon."""
    luma_event_id: str = Field(..., description="Luma event API ID")


class SyncGuestsRequest(BaseModel):
    """Request schema for syncing Luma event guests into a hackathon."""
    luma_event_id: str = Field(..., description="Luma event API ID")
    hackathon_id: str = Field(..., description="Target hackathon ID")


class LumaConnectResponse(BaseModel):
    """Response schema for a successful Luma connection."""
    success: bool
    integration_id: str
    calendar_name: Optional[str] = None
    status: str
    message: str


class LumaStatusResponse(BaseModel):
    """Response schema for Luma connection status."""
    connected: bool
    integration_id: Optional[str] = None
    calendar_name: Optional[str] = None
    status: Optional[str] = None
    sync_options: Optional[dict] = None
    last_synced_at: Optional[str] = None


class LumaEventSummary(BaseModel):
    """Summary of a single Luma event."""
    event_id: str
    name: str
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    location: Optional[str] = None
    is_online: bool = False
    cover_url: Optional[str] = None
    guest_count: int = 0
    url: Optional[str] = None


class LumaEventsListResponse(BaseModel):
    """Response schema for listing Luma events."""
    events: list[LumaEventSummary]
    total: int


class ImportEventResponse(BaseModel):
    """Response schema for importing a Luma event as a hackathon."""
    success: bool
    hackathon_id: str
    hackathon_name: str
    message: str


class SyncGuestsResponse(BaseModel):
    """Response schema for syncing guests from a Luma event."""
    success: bool
    imported: int
    skipped: int
    total: int
    message: str


class LumaContactSummary(BaseModel):
    """Summary of a single Luma contact."""
    email: str
    name: Optional[str] = None
    event_count: int = 0


class LumaContactsListResponse(BaseModel):
    """Response schema for listing Luma contacts."""
    contacts: list[LumaContactSummary]
    total: int
