"""
Export Service

Provides comprehensive data export and reporting capabilities including:
- JSON, CSV, and PDF export formats
- RLHF feedback data export
- Hackathon archival for completed events
"""

import csv
import io
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting hackathon data in various formats."""

    def __init__(self, zerodb_client: ZeroDBClient):
        """
        Initialize export service.

        Args:
            zerodb_client: ZeroDB client instance
        """
        self.zerodb = zerodb_client

    async def export_hackathon_json(
        self,
        hackathon_id: str,
        include_participants: bool = True,
        include_submissions: bool = True,
        include_teams: bool = True,
        include_judgments: bool = False,
    ) -> Dict[str, Any]:
        """
        Export hackathon data to JSON format.

        Args:
            hackathon_id: Hackathon identifier
            include_participants: Include participant data
            include_submissions: Include submission data
            include_teams: Include team data
            include_judgments: Include judgment/scoring data

        Returns:
            Dict containing complete hackathon data in JSON-serializable format

        Raises:
            HTTPException: 404 if hackathon not found, 500 for other errors

        Example:
            >>> export = await service.export_hackathon_json(
            ...     "hack-123",
            ...     include_participants=True,
            ...     include_submissions=True
            ... )
            >>> export['hackathon']['name']
            'AI Hackathon 2025'
        """
        try:
            # Fetch hackathon data
            hackathon = await self._get_hackathon(hackathon_id)

            export_data = {
                "hackathon": hackathon,
                "export_metadata": {
                    "exported_at": datetime.utcnow().isoformat(),
                    "format": "json",
                    "hackathon_id": hackathon_id,
                },
            }

            # Fetch related data based on flags
            if include_participants:
                participants = await self._get_participants(hackathon_id)
                export_data["participants"] = participants
                export_data["participant_count"] = len(participants)

            if include_submissions:
                submissions = await self._get_submissions(hackathon_id)
                export_data["submissions"] = submissions
                export_data["submission_count"] = len(submissions)

            if include_teams:
                teams = await self._get_teams(hackathon_id)
                export_data["teams"] = teams
                export_data["team_count"] = len(teams)

            if include_judgments:
                judgments = await self._get_judgments(hackathon_id)
                export_data["judgments"] = judgments
                export_data["judgment_count"] = len(judgments)

            logger.info(f"Successfully exported hackathon {hackathon_id} to JSON")
            return export_data

        except ZeroDBNotFound:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hackathon {hackathon_id} not found",
            )
        except (ZeroDBError, ZeroDBTimeoutError) as e:
            logger.error(f"Error exporting hackathon {hackathon_id} to JSON: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to export hackathon data",
            )

    async def export_hackathon_csv(
        self,
        hackathon_id: str,
        include_participants: bool = True,
        include_submissions: bool = True,
        include_teams: bool = True,
    ) -> str:
        """
        Export hackathon data to CSV format.

        Creates multiple CSV sections for different data types.

        Args:
            hackathon_id: Hackathon identifier
            include_participants: Include participant data
            include_submissions: Include submission data
            include_teams: Include team data

        Returns:
            CSV string with multiple sections

        Raises:
            HTTPException: 404 if hackathon not found, 500 for other errors

        Example:
            >>> csv_data = await service.export_hackathon_csv("hack-123")
            >>> 'Hackathon Information' in csv_data
            True
        """
        try:
            hackathon = await self._get_hackathon(hackathon_id)

            output = io.StringIO()

            # Hackathon Information Section
            output.write("=== Hackathon Information ===\n")
            hackathon_writer = csv.writer(output)
            hackathon_writer.writerow(["Field", "Value"])
            for key, value in hackathon.items():
                if value is not None:
                    hackathon_writer.writerow([key, str(value)])
            output.write("\n")

            # Participants Section
            if include_participants:
                output.write("=== Participants ===\n")
                participants = await self._get_participants(hackathon_id)
                if participants:
                    participant_writer = csv.DictWriter(
                        output,
                        fieldnames=participants[0].keys(),
                    )
                    participant_writer.writeheader()
                    participant_writer.writerows(participants)
                    output.write(f"\nTotal Participants: {len(participants)}\n\n")

            # Submissions Section
            if include_submissions:
                output.write("=== Submissions ===\n")
                submissions = await self._get_submissions(hackathon_id)
                if submissions:
                    submission_writer = csv.DictWriter(
                        output,
                        fieldnames=submissions[0].keys(),
                    )
                    submission_writer.writeheader()
                    submission_writer.writerows(submissions)
                    output.write(f"\nTotal Submissions: {len(submissions)}\n\n")

            # Teams Section
            if include_teams:
                output.write("=== Teams ===\n")
                teams = await self._get_teams(hackathon_id)
                if teams:
                    team_writer = csv.DictWriter(output, fieldnames=teams[0].keys())
                    team_writer.writeheader()
                    team_writer.writerows(teams)
                    output.write(f"\nTotal Teams: {len(teams)}\n\n")

            csv_content = output.getvalue()
            output.close()

            logger.info(f"Successfully exported hackathon {hackathon_id} to CSV")
            return csv_content

        except ZeroDBNotFound:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hackathon {hackathon_id} not found",
            )
        except (ZeroDBError, ZeroDBTimeoutError) as e:
            logger.error(f"Error exporting hackathon {hackathon_id} to CSV: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to export hackathon data",
            )

    async def generate_pdf_report(
        self,
        hackathon_id: str,
        include_participants: bool = True,
        include_submissions: bool = True,
        include_teams: bool = True,
        include_judgments: bool = False,
    ) -> bytes:
        """
        Generate PDF report for hackathon.

        Creates a comprehensive PDF report with all hackathon data.
        Note: This is a simplified implementation. For production, use
        libraries like ReportLab, WeasyPrint, or pdfkit.

        Args:
            hackathon_id: Hackathon identifier
            include_participants: Include participant data
            include_submissions: Include submission data
            include_teams: Include team data
            include_judgments: Include judgment/scoring data

        Returns:
            PDF file as bytes

        Raises:
            HTTPException: 404 if hackathon not found, 500 for other errors

        Example:
            >>> pdf_bytes = await service.generate_pdf_report("hack-123")
            >>> len(pdf_bytes) > 0
            True
        """
        try:
            # Get all data
            json_data = await self.export_hackathon_json(
                hackathon_id,
                include_participants,
                include_submissions,
                include_teams,
                include_judgments,
            )

            # For now, return a simple text-based "PDF" (JSON formatted)
            # In production, use ReportLab or WeasyPrint for proper PDF generation
            report_text = self._generate_text_report(json_data)
            pdf_bytes = report_text.encode("utf-8")

            logger.info(f"Successfully generated PDF report for hackathon {hackathon_id}")
            return pdf_bytes

        except ZeroDBNotFound:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hackathon {hackathon_id} not found",
            )
        except (ZeroDBError, ZeroDBTimeoutError) as e:
            logger.error(f"Error generating PDF for hackathon {hackathon_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate PDF report",
            )

    async def export_rlhf_data(
        self,
        hackathon_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_feedback_only: bool = False,
        format: str = "json",
    ) -> Dict[str, Any]:
        """
        Export RLHF feedback data for a hackathon.

        Args:
            hackathon_id: Hackathon identifier
            start_date: Filter interactions from this date onwards
            end_date: Filter interactions up to this date
            include_feedback_only: Only export interactions with user feedback
            format: Export format (json or csv)

        Returns:
            Dict containing RLHF data and export metadata

        Raises:
            HTTPException: 404 if hackathon not found, 500 for other errors

        Example:
            >>> rlhf_export = await service.export_rlhf_data(
            ...     "hack-123",
            ...     include_feedback_only=True
            ... )
            >>> rlhf_export['total_interactions'] > 0
            True
        """
        try:
            # Verify hackathon exists
            await self._get_hackathon(hackathon_id)

            # Fetch RLHF interactions
            interactions = await self._get_rlhf_interactions(
                hackathon_id,
                start_date,
                end_date,
                include_feedback_only,
            )

            # Calculate statistics
            total_interactions = len(interactions)
            interactions_with_feedback = sum(
                1 for i in interactions if i.get("feedback") is not None
            )

            export_data = {
                "hackathon_id": hackathon_id,
                "total_interactions": total_interactions,
                "interactions_with_feedback": interactions_with_feedback,
                "feedback_rate": (
                    interactions_with_feedback / total_interactions
                    if total_interactions > 0
                    else 0.0
                ),
                "export_metadata": {
                    "exported_at": datetime.utcnow().isoformat(),
                    "format": format,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "include_feedback_only": include_feedback_only,
                },
            }

            if format == "json":
                export_data["interactions"] = interactions
            elif format == "csv":
                export_data["csv_data"] = self._convert_rlhf_to_csv(interactions)

            logger.info(
                f"Successfully exported {total_interactions} RLHF interactions "
                f"for hackathon {hackathon_id}"
            )
            return export_data

        except ZeroDBNotFound:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hackathon {hackathon_id} not found",
            )
        except (ZeroDBError, ZeroDBTimeoutError) as e:
            logger.error(f"Error exporting RLHF data for {hackathon_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to export RLHF data",
            )

    async def archive_hackathon(
        self,
        hackathon_id: str,
        delete_after_archive: bool = False,
        include_analytics: bool = True,
    ) -> Dict[str, Any]:
        """
        Archive a completed hackathon.

        Creates a comprehensive archive including all hackathon data,
        submissions, teams, participants, judgments, and RLHF data.

        Args:
            hackathon_id: Hackathon identifier
            delete_after_archive: Delete original data after successful archival
            include_analytics: Include analytics and summary statistics

        Returns:
            Dict with archive details and download URL

        Raises:
            HTTPException: 400 if hackathon not completed, 404 if not found,
                          500 for other errors

        Example:
            >>> archive = await service.archive_hackathon("hack-123")
            >>> archive['archive_id']
            'archive-abc-456'
        """
        try:
            # Verify hackathon exists and is completed
            hackathon = await self._get_hackathon(hackathon_id)

            if hackathon.get("status") not in ["completed", "cancelled"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only completed or cancelled hackathons can be archived",
                )

            # Generate archive ID
            archive_id = f"archive-{uuid.uuid4()}"

            # Collect all data
            archive_data = {
                "archive_id": archive_id,
                "hackathon_id": hackathon_id,
                "hackathon": hackathon,
            }

            # Collect all related data
            participants = await self._get_participants(hackathon_id)
            submissions = await self._get_submissions(hackathon_id)
            teams = await self._get_teams(hackathon_id)
            judgments = await self._get_judgments(hackathon_id)
            rlhf_data = await self._get_rlhf_interactions(hackathon_id)

            archive_data.update(
                {
                    "participants": participants,
                    "submissions": submissions,
                    "teams": teams,
                    "judgments": judgments,
                    "rlhf_interactions": rlhf_data,
                }
            )

            # Add analytics if requested
            if include_analytics:
                archive_data["analytics"] = self._generate_analytics(
                    hackathon,
                    participants,
                    submissions,
                    teams,
                    judgments,
                )

            # Store archive in ZeroDB files
            archive_json = json.dumps(archive_data, indent=2, default=str)
            archive_bytes = archive_json.encode("utf-8")

            # Upload to ZeroDB file storage
            file_result = await self.zerodb.files.upload(
                file_name=f"{archive_id}.json",
                file_content=archive_bytes,
                folder="archives",
                metadata={
                    "hackathon_id": hackathon_id,
                    "archive_id": archive_id,
                    "archived_at": datetime.utcnow().isoformat(),
                },
            )

            # Generate presigned URL
            url_result = await self.zerodb.files.generate_presigned_url(
                file_id=file_result["file_id"],
                expiration_seconds=2592000,  # 30 days
            )

            # Optionally delete original data
            original_deleted = False
            if delete_after_archive:
                await self._delete_hackathon_data(hackathon_id)
                original_deleted = True

            result = {
                "success": True,
                "hackathon_id": hackathon_id,
                "archive_id": archive_id,
                "archive_url": url_result["presigned_url"],
                "archive_size_bytes": len(archive_bytes),
                "items_archived": {
                    "hackathon": 1,
                    "participants": len(participants),
                    "submissions": len(submissions),
                    "teams": len(teams),
                    "judgments": len(judgments),
                    "rlhf_interactions": len(rlhf_data),
                },
                "original_deleted": original_deleted,
                "expires_at": datetime.utcnow() + timedelta(days=30),
                "archived_at": datetime.utcnow(),
            }

            logger.info(
                f"Successfully archived hackathon {hackathon_id} as {archive_id}"
            )
            return result

        except ZeroDBNotFound:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hackathon {hackathon_id} not found",
            )
        except (ZeroDBError, ZeroDBTimeoutError) as e:
            logger.error(f"Error archiving hackathon {hackathon_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to archive hackathon",
            )

    # Private helper methods

    async def _get_hackathon(self, hackathon_id: str) -> Dict[str, Any]:
        """Fetch hackathon by ID."""
        filter_query = {"hackathon_id": hackathon_id, "deleted_at": None}
        result = await self.zerodb.tables.query(
            table_id="hackathons",
            filter=filter_query,
            limit=1,
        )

        if not result.get("rows"):
            raise ZeroDBNotFound(f"Hackathon {hackathon_id} not found")

        return result["rows"][0]

    async def _get_participants(self, hackathon_id: str) -> List[Dict[str, Any]]:
        """Fetch all participants for a hackathon."""
        try:
            result = await self.zerodb.tables.query(
                table_id="hackathon_participants",
                filter={"hackathon_id": hackathon_id, "deleted_at": None},
                limit=10000,
            )
            return result.get("rows", [])
        except (ZeroDBError, ZeroDBNotFound):
            return []

    async def _get_submissions(self, hackathon_id: str) -> List[Dict[str, Any]]:
        """Fetch all submissions for a hackathon."""
        try:
            result = await self.zerodb.tables.query(
                table_id="submissions",
                filter={"hackathon_id": hackathon_id, "deleted_at": None},
                limit=10000,
            )
            return result.get("rows", [])
        except (ZeroDBError, ZeroDBNotFound):
            return []

    async def _get_teams(self, hackathon_id: str) -> List[Dict[str, Any]]:
        """Fetch all teams for a hackathon."""
        try:
            result = await self.zerodb.tables.query(
                table_id="teams",
                filter={"hackathon_id": hackathon_id, "deleted_at": None},
                limit=10000,
            )
            return result.get("rows", [])
        except (ZeroDBError, ZeroDBNotFound):
            return []

    async def _get_judgments(self, hackathon_id: str) -> List[Dict[str, Any]]:
        """Fetch all judgments for a hackathon."""
        try:
            result = await self.zerodb.tables.query(
                table_id="judgments",
                filter={"hackathon_id": hackathon_id, "deleted_at": None},
                limit=10000,
            )
            return result.get("rows", [])
        except (ZeroDBError, ZeroDBNotFound):
            return []

    async def _get_rlhf_interactions(
        self,
        hackathon_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_feedback_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Fetch RLHF interactions for a hackathon."""
        try:
            # Build filter query
            filter_query = {}
            if hackathon_id:
                filter_query["context.hackathon_id"] = hackathon_id

            # Query RLHF interactions from ZeroDB
            result = await self.zerodb.rlhf.list_interactions(
                limit=10000,
            )

            interactions = result.get("interactions", [])

            # Apply filters
            if start_date:
                interactions = [
                    i
                    for i in interactions
                    if datetime.fromisoformat(i["created_at"]) >= start_date
                ]

            if end_date:
                interactions = [
                    i
                    for i in interactions
                    if datetime.fromisoformat(i["created_at"]) <= end_date
                ]

            if include_feedback_only:
                interactions = [i for i in interactions if i.get("feedback")]

            return interactions

        except (ZeroDBError, ZeroDBNotFound):
            return []

    async def _delete_hackathon_data(self, hackathon_id: str) -> None:
        """Delete all hackathon data (for post-archive cleanup)."""
        try:
            # Soft delete hackathon and related data
            await self.zerodb.tables.update(
                table_id="hackathons",
                filter={"hackathon_id": hackathon_id},
                update={"deleted_at": datetime.utcnow().isoformat()},
            )

            # Delete related data
            for table in ["hackathon_participants", "submissions", "teams", "judgments"]:
                await self.zerodb.tables.update(
                    table_id=table,
                    filter={"hackathon_id": hackathon_id},
                    update={"deleted_at": datetime.utcnow().isoformat()},
                )

        except (ZeroDBError, ZeroDBNotFound) as e:
            logger.warning(f"Error deleting hackathon data: {e}")

    def _generate_text_report(self, data: Dict[str, Any]) -> str:
        """Generate text-based report from JSON data."""
        report_lines = [
            "=" * 80,
            "HACKATHON REPORT",
            "=" * 80,
            "",
            f"Generated: {data['export_metadata']['exported_at']}",
            "",
            "HACKATHON INFORMATION",
            "-" * 80,
        ]

        hackathon = data["hackathon"]
        for key, value in hackathon.items():
            if value is not None:
                report_lines.append(f"{key}: {value}")

        report_lines.extend(["", "STATISTICS", "-" * 80])

        if "participant_count" in data:
            report_lines.append(f"Total Participants: {data['participant_count']}")
        if "submission_count" in data:
            report_lines.append(f"Total Submissions: {data['submission_count']}")
        if "team_count" in data:
            report_lines.append(f"Total Teams: {data['team_count']}")
        if "judgment_count" in data:
            report_lines.append(f"Total Judgments: {data['judgment_count']}")

        report_lines.extend(["", "=" * 80])

        return "\n".join(report_lines)

    def _convert_rlhf_to_csv(self, interactions: List[Dict[str, Any]]) -> str:
        """Convert RLHF interactions to CSV format."""
        output = io.StringIO()

        if not interactions:
            return ""

        # Flatten nested feedback data
        flattened = []
        for interaction in interactions:
            row = {
                "interaction_id": interaction.get("interaction_id"),
                "prompt": interaction.get("prompt"),
                "response": interaction.get("response"),
                "agent_id": interaction.get("agent_id"),
                "session_id": interaction.get("session_id"),
                "created_at": interaction.get("created_at"),
            }

            # Add feedback fields if present
            feedback = interaction.get("feedback", {})
            if feedback:
                row["feedback_type"] = feedback.get("feedback_type")
                row["rating"] = feedback.get("rating")
                row["comment"] = feedback.get("comment")

            # Add context fields
            context = interaction.get("context", {})
            for key, value in context.items():
                row[f"context_{key}"] = value

            flattened.append(row)

        # Write CSV
        if flattened:
            writer = csv.DictWriter(output, fieldnames=flattened[0].keys())
            writer.writeheader()
            writer.writerows(flattened)

        csv_content = output.getvalue()
        output.close()
        return csv_content

    def _generate_analytics(
        self,
        hackathon: Dict[str, Any],
        participants: List[Dict[str, Any]],
        submissions: List[Dict[str, Any]],
        teams: List[Dict[str, Any]],
        judgments: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate analytics summary for archive."""
        return {
            "total_participants": len(participants),
            "total_submissions": len(submissions),
            "total_teams": len(teams),
            "total_judgments": len(judgments),
            "submission_rate": (
                len(submissions) / len(participants) if participants else 0.0
            ),
            "average_team_size": (
                len(participants) / len(teams) if teams else 0.0
            ),
            "hackathon_duration_days": (
                (
                    datetime.fromisoformat(hackathon["end_date"])
                    - datetime.fromisoformat(hackathon["start_date"])
                ).days
                if hackathon.get("start_date") and hackathon.get("end_date")
                else 0
            ),
            "status": hackathon.get("status"),
            "location": hackathon.get("location"),
        }
