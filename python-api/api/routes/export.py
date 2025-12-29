"""
Export API Endpoints

Provides endpoints for exporting hackathon data and RLHF feedback in various formats.
"""

import logging
from datetime import datetime
from typing import Optional

from api.dependencies import get_zerodb_client
from api.schemas.export import (
    ArchiveRequest,
    ArchiveResponse,
    ExportFormat,
    ExportRequest,
    ExportResponse,
    RLHFExportRequest,
    RLHFExportResponse,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from integrations.zerodb.client import ZeroDBClient
from services.export_service import ExportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hackathons", tags=["export"])


@router.get(
    "/{hackathon_id}/export",
    response_model=ExportResponse,
    summary="Export hackathon data",
    description="""
    Export hackathon data in JSON, CSV, or PDF format.

    - **JSON**: Returns complete data inline
    - **CSV**: Returns pre-signed URL for download
    - **PDF**: Returns pre-signed URL for download

    Includes hackathon details, participants, submissions, teams, and optionally judgments.
    """,
)
async def export_hackathon(
    hackathon_id: str,
    format: ExportFormat = Query(
        ExportFormat.JSON,
        description="Export format: json, csv, or pdf"
    ),
    include_participants: bool = Query(
        True,
        description="Include participant data in export"
    ),
    include_submissions: bool = Query(
        True,
        description="Include submission data in export"
    ),
    include_teams: bool = Query(
        True,
        description="Include team data in export"
    ),
    include_judgments: bool = Query(
        False,
        description="Include judgment/scoring data in export"
    ),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> ExportResponse:
    """
    Export hackathon data in the requested format.

    Args:
        hackathon_id: Hackathon identifier
        format: Export format (json, csv, pdf)
        include_participants: Include participant data
        include_submissions: Include submission data
        include_teams: Include team data
        include_judgments: Include judgment data
        zerodb_client: ZeroDB client dependency

    Returns:
        ExportResponse with data or download URL

    Raises:
        HTTPException: 404 if hackathon not found, 500 for errors
    """
    logger.info(
        f"Exporting hackathon {hackathon_id} in {format} format "
        f"(participants={include_participants}, submissions={include_submissions}, "
        f"teams={include_teams}, judgments={include_judgments})"
    )

    export_service = ExportService(zerodb_client)

    try:
        if format == ExportFormat.JSON:
            # Export as JSON - return inline
            data = await export_service.export_hackathon_json(
                hackathon_id,
                include_participants,
                include_submissions,
                include_teams,
                include_judgments,
            )

            import json
            data_str = json.dumps(data, default=str)
            file_size = len(data_str.encode("utf-8"))

            return ExportResponse(
                success=True,
                format="json",
                data=data,
                file_size_bytes=file_size,
                generated_at=datetime.utcnow(),
            )

        elif format == ExportFormat.CSV:
            # Export as CSV - upload to storage and return URL
            csv_data = await export_service.export_hackathon_csv(
                hackathon_id,
                include_participants,
                include_submissions,
                include_teams,
            )

            # Upload CSV to ZeroDB file storage
            csv_bytes = csv_data.encode("utf-8")
            file_result = await zerodb_client.files.upload(
                file_name=f"hackathon_{hackathon_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
                file_content=csv_bytes,
                folder="exports",
                metadata={
                    "hackathon_id": hackathon_id,
                    "format": "csv",
                    "exported_at": datetime.utcnow().isoformat(),
                },
            )

            # Generate presigned URL (valid for 7 days)
            url_result = await zerodb_client.files.generate_presigned_url(
                file_id=file_result["file_id"],
                expiration_seconds=604800,  # 7 days
            )

            return ExportResponse(
                success=True,
                format="csv",
                file_url=url_result["presigned_url"],
                file_size_bytes=len(csv_bytes),
                expires_at=datetime.utcnow()
                + __import__("datetime").timedelta(days=7),
                generated_at=datetime.utcnow(),
            )

        elif format == ExportFormat.PDF:
            # Generate PDF - upload to storage and return URL
            pdf_bytes = await export_service.generate_pdf_report(
                hackathon_id,
                include_participants,
                include_submissions,
                include_teams,
                include_judgments,
            )

            # Upload PDF to ZeroDB file storage
            file_result = await zerodb_client.files.upload(
                file_name=f"hackathon_{hackathon_id}_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf",
                file_content=pdf_bytes,
                folder="exports",
                content_type="application/pdf",
                metadata={
                    "hackathon_id": hackathon_id,
                    "format": "pdf",
                    "exported_at": datetime.utcnow().isoformat(),
                },
            )

            # Generate presigned URL (valid for 7 days)
            url_result = await zerodb_client.files.generate_presigned_url(
                file_id=file_result["file_id"],
                expiration_seconds=604800,  # 7 days
            )

            return ExportResponse(
                success=True,
                format="pdf",
                file_url=url_result["presigned_url"],
                file_size_bytes=len(pdf_bytes),
                expires_at=datetime.utcnow()
                + __import__("datetime").timedelta(days=7),
                generated_at=datetime.utcnow(),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error exporting hackathon {hackathon_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export hackathon data",
        )


@router.get(
    "/{hackathon_id}/rlhf/export",
    response_model=RLHFExportResponse,
    summary="Export RLHF feedback data",
    description="""
    Export RLHF (Reinforcement Learning from Human Feedback) interaction data
    for a specific hackathon.

    Supports filtering by date range and feedback status.
    Export formats: JSON (inline) or CSV (download URL).
    """,
)
async def export_rlhf_data(
    hackathon_id: str,
    start_date: Optional[datetime] = Query(
        None,
        description="Filter interactions from this date onwards"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Filter interactions up to this date"
    ),
    include_feedback_only: bool = Query(
        False,
        description="Only export interactions with user feedback"
    ),
    format: ExportFormat = Query(
        ExportFormat.JSON,
        description="Export format: json or csv"
    ),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> RLHFExportResponse:
    """
    Export RLHF feedback data for a hackathon.

    Args:
        hackathon_id: Hackathon identifier
        start_date: Filter from this date
        end_date: Filter to this date
        include_feedback_only: Only interactions with feedback
        format: Export format (json or csv)
        zerodb_client: ZeroDB client dependency

    Returns:
        RLHFExportResponse with data or download URL

    Raises:
        HTTPException: 400 for invalid format, 404 if not found, 500 for errors
    """
    logger.info(
        f"Exporting RLHF data for hackathon {hackathon_id} "
        f"(format={format}, feedback_only={include_feedback_only})"
    )

    if format == ExportFormat.PDF:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF format not supported for RLHF export. Use JSON or CSV.",
        )

    export_service = ExportService(zerodb_client)

    try:
        export_data = await export_service.export_rlhf_data(
            hackathon_id,
            start_date,
            end_date,
            include_feedback_only,
            format=format.value,
        )

        if format == ExportFormat.JSON:
            # Return JSON inline
            import json
            data_str = json.dumps(export_data, default=str)
            file_size = len(data_str.encode("utf-8"))

            return RLHFExportResponse(
                success=True,
                format="json",
                total_interactions=export_data["total_interactions"],
                interactions_with_feedback=export_data["interactions_with_feedback"],
                data=export_data.get("interactions", []),
                file_size_bytes=file_size,
                generated_at=datetime.utcnow(),
            )

        elif format == ExportFormat.CSV:
            # Upload CSV and return URL
            csv_data = export_data["csv_data"]
            csv_bytes = csv_data.encode("utf-8")

            file_result = await zerodb_client.files.upload(
                file_name=f"rlhf_{hackathon_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
                file_content=csv_bytes,
                folder="exports",
                metadata={
                    "hackathon_id": hackathon_id,
                    "format": "csv",
                    "type": "rlhf",
                    "exported_at": datetime.utcnow().isoformat(),
                },
            )

            url_result = await zerodb_client.files.generate_presigned_url(
                file_id=file_result["file_id"],
                expiration_seconds=604800,  # 7 days
            )

            return RLHFExportResponse(
                success=True,
                format="csv",
                total_interactions=export_data["total_interactions"],
                interactions_with_feedback=export_data["interactions_with_feedback"],
                file_url=url_result["presigned_url"],
                file_size_bytes=len(csv_bytes),
                expires_at=datetime.utcnow()
                + __import__("datetime").timedelta(days=7),
                generated_at=datetime.utcnow(),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error exporting RLHF data for {hackathon_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export RLHF data",
        )


@router.post(
    "/{hackathon_id}/archive",
    response_model=ArchiveResponse,
    summary="Archive completed hackathon",
    description="""
    Archive a completed or cancelled hackathon.

    Creates a comprehensive archive including:
    - Hackathon details
    - All participants
    - All submissions
    - All teams
    - All judgments
    - RLHF interactions
    - Analytics summary

    The archive is stored in ZeroDB file storage with a 30-day expiration.
    Optionally deletes the original data after archival.
    """,
)
async def archive_hackathon(
    hackathon_id: str,
    request: ArchiveRequest,
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> ArchiveResponse:
    """
    Archive a completed hackathon.

    Args:
        hackathon_id: Hackathon identifier
        request: Archive request with options
        zerodb_client: ZeroDB client dependency

    Returns:
        ArchiveResponse with archive details and download URL

    Raises:
        HTTPException: 400 if not completed/cancelled or confirm=False,
                      404 if not found, 500 for errors
    """
    logger.info(
        f"Archiving hackathon {hackathon_id} "
        f"(delete_after={request.delete_after_archive})"
    )

    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Archive confirmation required. Set 'confirm' to true.",
        )

    export_service = ExportService(zerodb_client)

    try:
        result = await export_service.archive_hackathon(
            hackathon_id,
            request.delete_after_archive,
            request.include_analytics,
        )

        return ArchiveResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error archiving hackathon {hackathon_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive hackathon",
        )
