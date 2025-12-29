"""
Export API Schemas

Request and response models for hackathon data export and reporting endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExportFormat(str, Enum):
    """Export format enumeration."""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"


class ExportRequest(BaseModel):
    """Request schema for exporting hackathon data."""

    format: ExportFormat = Field(
        ...,
        description="Export format: json, csv, or pdf"
    )
    include_participants: bool = Field(
        default=True,
        description="Include participant data in export"
    )
    include_submissions: bool = Field(
        default=True,
        description="Include submission data in export"
    )
    include_teams: bool = Field(
        default=True,
        description="Include team data in export"
    )
    include_judgments: bool = Field(
        default=False,
        description="Include judgment/scoring data in export"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "format": "json",
                "include_participants": True,
                "include_submissions": True,
                "include_teams": True,
                "include_judgments": False
            }
        }


class ExportResponse(BaseModel):
    """Response schema for export operations."""

    success: bool
    format: str
    file_url: Optional[str] = Field(
        None,
        description="Pre-signed URL for downloading the export (for PDF/CSV)"
    )
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Inline export data (for JSON format)"
    )
    file_size_bytes: Optional[int] = Field(
        None,
        ge=0,
        description="Size of the exported file in bytes"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="When the download URL expires (for file-based exports)"
    )
    generated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "format": "json",
                "data": {
                    "hackathon": {
                        "hackathon_id": "hack-123",
                        "name": "AI Hackathon 2025",
                        "status": "completed"
                    },
                    "participants": 150,
                    "submissions": 45,
                    "teams": 30
                },
                "file_size_bytes": 25600,
                "generated_at": "2024-12-28T10:00:00Z"
            }
        }


class RLHFExportRequest(BaseModel):
    """Request schema for exporting RLHF feedback data."""

    start_date: Optional[datetime] = Field(
        None,
        description="Filter interactions from this date onwards"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Filter interactions up to this date"
    )
    include_feedback_only: bool = Field(
        default=False,
        description="Only export interactions with user feedback"
    )
    format: ExportFormat = Field(
        default=ExportFormat.JSON,
        description="Export format (JSON or CSV only for RLHF)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z",
                "include_feedback_only": True,
                "format": "json"
            }
        }


class RLHFExportResponse(BaseModel):
    """Response schema for RLHF export operations."""

    success: bool
    format: str
    total_interactions: int = Field(..., ge=0)
    interactions_with_feedback: int = Field(..., ge=0)
    file_url: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    file_size_bytes: Optional[int] = Field(None, ge=0)
    expires_at: Optional[datetime] = None
    generated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "format": "json",
                "total_interactions": 250,
                "interactions_with_feedback": 200,
                "data": [
                    {
                        "interaction_id": "int-123",
                        "prompt": "Recommend submissions",
                        "response": "Here are 5 recommendations",
                        "feedback": {
                            "type": "rating",
                            "rating": 5
                        }
                    }
                ],
                "file_size_bytes": 51200,
                "generated_at": "2024-12-28T10:00:00Z"
            }
        }


class ArchiveRequest(BaseModel):
    """Request schema for archiving a completed hackathon."""

    confirm: bool = Field(
        ...,
        description="Must be True to confirm archival (safety check)"
    )
    delete_after_archive: bool = Field(
        default=False,
        description="Delete original data after successful archival"
    )
    include_analytics: bool = Field(
        default=True,
        description="Include analytics and summary statistics in archive"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "confirm": True,
                "delete_after_archive": False,
                "include_analytics": True
            }
        }


class ArchiveResponse(BaseModel):
    """Response schema for hackathon archival operations."""

    success: bool
    hackathon_id: str
    archive_id: str = Field(
        ...,
        description="Unique identifier for the archive"
    )
    archive_url: str = Field(
        ...,
        description="Pre-signed URL for downloading the complete archive"
    )
    archive_size_bytes: int = Field(..., ge=0)
    items_archived: Dict[str, int] = Field(
        ...,
        description="Count of each item type archived"
    )
    original_deleted: bool = Field(
        default=False,
        description="Whether original data was deleted after archival"
    )
    expires_at: datetime = Field(
        ...,
        description="When the archive download URL expires"
    )
    archived_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "hackathon_id": "hack-123",
                "archive_id": "archive-abc-456",
                "archive_url": "https://storage.example.com/archives/archive-abc-456.zip",
                "archive_size_bytes": 1048576,
                "items_archived": {
                    "hackathon": 1,
                    "participants": 150,
                    "submissions": 45,
                    "teams": 30,
                    "judgments": 135,
                    "rlhf_interactions": 250
                },
                "original_deleted": False,
                "expires_at": "2025-01-28T10:00:00Z",
                "archived_at": "2024-12-28T10:00:00Z"
            }
        }


class ExportStatusResponse(BaseModel):
    """Response schema for checking export job status."""

    export_id: str
    status: str = Field(
        ...,
        pattern="^(pending|processing|completed|failed)$",
        description="Current status of the export job"
    )
    progress_percent: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Export progress percentage"
    )
    file_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "export_id": "export-xyz-789",
                "status": "completed",
                "progress_percent": 100,
                "file_url": "https://storage.example.com/exports/export-xyz-789.pdf",
                "created_at": "2024-12-28T09:55:00Z",
                "completed_at": "2024-12-28T10:00:00Z"
            }
        }
