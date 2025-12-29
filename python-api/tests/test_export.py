"""
Tests for Export Service and Endpoints

Comprehensive test suite for hackathon data export functionality including
JSON, CSV, PDF exports, RLHF data export, and hackathon archival.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from api.schemas.export import (
    ArchiveRequest,
    ExportFormat,
    RLHFExportRequest,
)
from fastapi import HTTPException, status
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBNotFound
from services.export_service import ExportService


# Fixtures


@pytest.fixture
def mock_zerodb_client():
    """Mock ZeroDB client with all necessary attributes."""
    mock_client = MagicMock()

    # Mock tables interface
    mock_client.tables = MagicMock()
    mock_client.tables.query = AsyncMock()
    mock_client.tables.update = AsyncMock()

    # Mock files interface
    mock_client.files = MagicMock()
    mock_client.files.upload = AsyncMock()
    mock_client.files.generate_presigned_url = AsyncMock()

    # Mock RLHF interface
    mock_client.rlhf = MagicMock()
    mock_client.rlhf.list_interactions = AsyncMock()

    return mock_client


@pytest.fixture
def export_service(mock_zerodb_client):
    """Create ExportService instance with mocked client."""
    return ExportService(mock_zerodb_client)


@pytest.fixture
def sample_hackathon():
    """Sample hackathon data."""
    return {
        "hackathon_id": "hack-123",
        "name": "AI Hackathon 2025",
        "description": "Build AI applications",
        "organizer_id": "org-456",
        "start_date": "2025-03-01T00:00:00",
        "end_date": "2025-03-03T23:59:59",
        "location": "San Francisco",
        "status": "completed",
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-03-03T23:59:59",
    }


@pytest.fixture
def sample_participants():
    """Sample participants data."""
    return [
        {
            "participant_id": "part-1",
            "hackathon_id": "hack-123",
            "user_id": "user-1",
            "role": "PARTICIPANT",
            "registered_at": "2025-02-01T00:00:00",
        },
        {
            "participant_id": "part-2",
            "hackathon_id": "hack-123",
            "user_id": "user-2",
            "role": "PARTICIPANT",
            "registered_at": "2025-02-02T00:00:00",
        },
    ]


@pytest.fixture
def sample_submissions():
    """Sample submissions data."""
    return [
        {
            "submission_id": "sub-1",
            "hackathon_id": "hack-123",
            "team_id": "team-1",
            "title": "AI Assistant",
            "submitted_at": "2025-03-03T20:00:00",
        }
    ]


@pytest.fixture
def sample_teams():
    """Sample teams data."""
    return [
        {
            "team_id": "team-1",
            "hackathon_id": "hack-123",
            "name": "Team Alpha",
            "created_at": "2025-02-15T00:00:00",
        }
    ]


@pytest.fixture
def sample_rlhf_interactions():
    """Sample RLHF interactions data."""
    return [
        {
            "interaction_id": "int-1",
            "prompt": "Recommend submissions for judge-1",
            "response": "Recommended 5 submissions",
            "context": {"hackathon_id": "hack-123", "user_id": "judge-1"},
            "agent_id": "recommendations_service",
            "created_at": "2025-03-04T10:00:00",
            "feedback": {"feedback_type": "rating", "rating": 5},
        },
        {
            "interaction_id": "int-2",
            "prompt": "Search for AI projects",
            "response": "Found 10 AI projects",
            "context": {"hackathon_id": "hack-123"},
            "agent_id": "search_service",
            "created_at": "2025-03-04T11:00:00",
            "feedback": None,
        },
    ]


# Tests for export_hackathon_json


@pytest.mark.asyncio
async def test_export_hackathon_json_success(
    export_service,
    mock_zerodb_client,
    sample_hackathon,
    sample_participants,
    sample_submissions,
    sample_teams,
):
    """Test successful JSON export with all data."""
    # Mock database queries
    mock_zerodb_client.tables.query.side_effect = [
        {"rows": [sample_hackathon]},  # Hackathon
        {"rows": sample_participants},  # Participants
        {"rows": sample_submissions},  # Submissions
        {"rows": sample_teams},  # Teams
        {"rows": []},  # Judgments
    ]

    result = await export_service.export_hackathon_json(
        "hack-123",
        include_participants=True,
        include_submissions=True,
        include_teams=True,
        include_judgments=True,
    )

    assert result["hackathon"] == sample_hackathon
    assert result["participants"] == sample_participants
    assert result["participant_count"] == 2
    assert result["submissions"] == sample_submissions
    assert result["submission_count"] == 1
    assert result["teams"] == sample_teams
    assert result["team_count"] == 1
    assert "export_metadata" in result
    assert result["export_metadata"]["format"] == "json"


@pytest.mark.asyncio
async def test_export_hackathon_json_minimal(
    export_service, mock_zerodb_client, sample_hackathon
):
    """Test JSON export with minimal data (hackathon only)."""
    mock_zerodb_client.tables.query.return_value = {"rows": [sample_hackathon]}

    result = await export_service.export_hackathon_json(
        "hack-123",
        include_participants=False,
        include_submissions=False,
        include_teams=False,
        include_judgments=False,
    )

    assert result["hackathon"] == sample_hackathon
    assert "participants" not in result
    assert "submissions" not in result
    assert "teams" not in result


@pytest.mark.asyncio
async def test_export_hackathon_json_not_found(export_service, mock_zerodb_client):
    """Test JSON export for non-existent hackathon."""
    mock_zerodb_client.tables.query.return_value = {"rows": []}

    with pytest.raises(HTTPException) as exc_info:
        await export_service.export_hackathon_json("nonexistent")

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_export_hackathon_json_database_error(
    export_service, mock_zerodb_client
):
    """Test JSON export with database error."""
    mock_zerodb_client.tables.query.side_effect = ZeroDBError("Database error")

    with pytest.raises(HTTPException) as exc_info:
        await export_service.export_hackathon_json("hack-123")

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# Tests for export_hackathon_csv


@pytest.mark.asyncio
async def test_export_hackathon_csv_success(
    export_service,
    mock_zerodb_client,
    sample_hackathon,
    sample_participants,
    sample_submissions,
):
    """Test successful CSV export."""
    mock_zerodb_client.tables.query.side_effect = [
        {"rows": [sample_hackathon]},
        {"rows": sample_participants},
        {"rows": sample_submissions},
        {"rows": []},
    ]

    result = await export_service.export_hackathon_csv(
        "hack-123",
        include_participants=True,
        include_submissions=True,
        include_teams=True,
    )

    assert isinstance(result, str)
    assert "=== Hackathon Information ===" in result
    assert "=== Participants ===" in result
    assert "=== Submissions ===" in result
    assert "hack-123" in result
    assert "AI Hackathon 2025" in result


@pytest.mark.asyncio
async def test_export_hackathon_csv_empty_sections(
    export_service, mock_zerodb_client, sample_hackathon
):
    """Test CSV export with empty participants/submissions."""
    mock_zerodb_client.tables.query.side_effect = [
        {"rows": [sample_hackathon]},
        {"rows": []},  # No participants
        {"rows": []},  # No submissions
        {"rows": []},  # No teams
    ]

    result = await export_service.export_hackathon_csv("hack-123")

    assert isinstance(result, str)
    assert "=== Hackathon Information ===" in result


# Tests for generate_pdf_report


@pytest.mark.asyncio
async def test_generate_pdf_report_success(
    export_service, mock_zerodb_client, sample_hackathon, sample_participants
):
    """Test PDF report generation."""
    mock_zerodb_client.tables.query.side_effect = [
        {"rows": [sample_hackathon]},
        {"rows": sample_participants},
        {"rows": []},
        {"rows": []},
        {"rows": []},
    ]

    result = await export_service.generate_pdf_report(
        "hack-123",
        include_participants=True,
    )

    assert isinstance(result, bytes)
    assert len(result) > 0

    # Verify content (decoded for text-based PDF)
    content = result.decode("utf-8")
    assert "HACKATHON REPORT" in content
    assert "hack-123" in content


# Tests for export_rlhf_data


@pytest.mark.asyncio
async def test_export_rlhf_data_json(
    export_service,
    mock_zerodb_client,
    sample_hackathon,
    sample_rlhf_interactions,
):
    """Test RLHF data export in JSON format."""
    mock_zerodb_client.tables.query.return_value = {"rows": [sample_hackathon]}
    mock_zerodb_client.rlhf.list_interactions.return_value = {
        "interactions": sample_rlhf_interactions
    }

    result = await export_service.export_rlhf_data(
        "hack-123", include_feedback_only=False, format="json"
    )

    assert result["hackathon_id"] == "hack-123"
    assert result["total_interactions"] == 2
    assert result["interactions_with_feedback"] == 1
    assert result["feedback_rate"] == 0.5
    assert len(result["interactions"]) == 2


@pytest.mark.asyncio
async def test_export_rlhf_data_feedback_only(
    export_service,
    mock_zerodb_client,
    sample_hackathon,
    sample_rlhf_interactions,
):
    """Test RLHF export with feedback_only filter."""
    mock_zerodb_client.tables.query.return_value = {"rows": [sample_hackathon]}
    mock_zerodb_client.rlhf.list_interactions.return_value = {
        "interactions": sample_rlhf_interactions
    }

    result = await export_service.export_rlhf_data(
        "hack-123", include_feedback_only=True, format="json"
    )

    # Should filter to only interactions with feedback
    assert result["total_interactions"] == 1
    assert result["interactions_with_feedback"] == 1
    assert all(i.get("feedback") for i in result["interactions"])


@pytest.mark.asyncio
async def test_export_rlhf_data_csv(
    export_service,
    mock_zerodb_client,
    sample_hackathon,
    sample_rlhf_interactions,
):
    """Test RLHF data export in CSV format."""
    mock_zerodb_client.tables.query.return_value = {"rows": [sample_hackathon]}
    mock_zerodb_client.rlhf.list_interactions.return_value = {
        "interactions": sample_rlhf_interactions
    }

    result = await export_service.export_rlhf_data(
        "hack-123", format="csv"
    )

    assert "csv_data" in result
    csv_content = result["csv_data"]
    assert isinstance(csv_content, str)
    assert "interaction_id" in csv_content


@pytest.mark.asyncio
async def test_export_rlhf_data_date_filter(
    export_service,
    mock_zerodb_client,
    sample_hackathon,
    sample_rlhf_interactions,
):
    """Test RLHF export with date filtering."""
    mock_zerodb_client.tables.query.return_value = {"rows": [sample_hackathon]}
    mock_zerodb_client.rlhf.list_interactions.return_value = {
        "interactions": sample_rlhf_interactions
    }

    start_date = datetime(2025, 3, 4, 10, 30, 0)
    end_date = datetime(2025, 3, 4, 23, 59, 59)

    result = await export_service.export_rlhf_data(
        "hack-123",
        start_date=start_date,
        end_date=end_date,
        format="json",
    )

    # Should filter by date range
    assert result["total_interactions"] == 1


# Tests for archive_hackathon


@pytest.mark.asyncio
async def test_archive_hackathon_success(
    export_service,
    mock_zerodb_client,
    sample_hackathon,
    sample_participants,
    sample_submissions,
    sample_teams,
    sample_rlhf_interactions,
):
    """Test successful hackathon archival."""
    # Mock database queries
    mock_zerodb_client.tables.query.side_effect = [
        {"rows": [sample_hackathon]},  # Get hackathon
        {"rows": sample_participants},  # Get participants
        {"rows": sample_submissions},  # Get submissions
        {"rows": sample_teams},  # Get teams
        {"rows": []},  # Get judgments
    ]

    mock_zerodb_client.rlhf.list_interactions.return_value = {
        "interactions": sample_rlhf_interactions
    }

    mock_zerodb_client.files.upload.return_value = {
        "file_id": "file-123",
        "success": True,
    }

    mock_zerodb_client.files.generate_presigned_url.return_value = {
        "presigned_url": "https://storage.example.com/archives/archive-123.json"
    }

    result = await export_service.archive_hackathon(
        "hack-123",
        delete_after_archive=False,
        include_analytics=True,
    )

    assert result["success"] is True
    assert result["hackathon_id"] == "hack-123"
    assert "archive_id" in result
    assert "archive_url" in result
    assert result["items_archived"]["hackathon"] == 1
    assert result["items_archived"]["participants"] == 2
    assert result["items_archived"]["submissions"] == 1
    assert result["original_deleted"] is False

    # Verify file upload was called
    mock_zerodb_client.files.upload.assert_called_once()


@pytest.mark.asyncio
async def test_archive_hackathon_with_delete(
    export_service,
    mock_zerodb_client,
    sample_hackathon,
    sample_participants,
):
    """Test archival with original data deletion."""
    mock_zerodb_client.tables.query.side_effect = [
        {"rows": [sample_hackathon]},
        {"rows": sample_participants},
        {"rows": []},
        {"rows": []},
        {"rows": []},
    ]

    mock_zerodb_client.rlhf.list_interactions.return_value = {
        "interactions": []
    }

    mock_zerodb_client.files.upload.return_value = {"file_id": "file-123"}
    mock_zerodb_client.files.generate_presigned_url.return_value = {
        "presigned_url": "https://example.com/archive.json"
    }

    result = await export_service.archive_hackathon(
        "hack-123",
        delete_after_archive=True,
        include_analytics=True,
    )

    assert result["original_deleted"] is True
    # Verify soft delete was called
    assert mock_zerodb_client.tables.update.called


@pytest.mark.asyncio
async def test_archive_hackathon_not_completed(
    export_service, mock_zerodb_client, sample_hackathon
):
    """Test archival of non-completed hackathon (should fail)."""
    active_hackathon = {**sample_hackathon, "status": "active"}
    mock_zerodb_client.tables.query.return_value = {"rows": [active_hackathon]}

    with pytest.raises(HTTPException) as exc_info:
        await export_service.archive_hackathon("hack-123")

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "completed or cancelled" in exc_info.value.detail


@pytest.mark.asyncio
async def test_archive_hackathon_not_found(export_service, mock_zerodb_client):
    """Test archival of non-existent hackathon."""
    mock_zerodb_client.tables.query.return_value = {"rows": []}

    with pytest.raises(HTTPException) as exc_info:
        await export_service.archive_hackathon("nonexistent")

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# Tests for helper methods


@pytest.mark.asyncio
async def test_get_hackathon_helper(export_service, mock_zerodb_client, sample_hackathon):
    """Test _get_hackathon helper method."""
    mock_zerodb_client.tables.query.return_value = {"rows": [sample_hackathon]}

    result = await export_service._get_hackathon("hack-123")

    assert result == sample_hackathon
    mock_zerodb_client.tables.query.assert_called_once()


@pytest.mark.asyncio
async def test_get_hackathon_not_found(export_service, mock_zerodb_client):
    """Test _get_hackathon with non-existent hackathon."""
    mock_zerodb_client.tables.query.return_value = {"rows": []}

    with pytest.raises(ZeroDBNotFound):
        await export_service._get_hackathon("nonexistent")


def test_generate_text_report(export_service):
    """Test _generate_text_report helper."""
    data = {
        "hackathon": {
            "hackathon_id": "hack-123",
            "name": "AI Hackathon",
            "status": "completed",
        },
        "participant_count": 150,
        "submission_count": 45,
        "export_metadata": {
            "exported_at": "2025-03-04T10:00:00",
        },
    }

    report = export_service._generate_text_report(data)

    assert "HACKATHON REPORT" in report
    assert "hack-123" in report
    assert "Total Participants: 150" in report
    assert "Total Submissions: 45" in report


def test_convert_rlhf_to_csv(export_service, sample_rlhf_interactions):
    """Test _convert_rlhf_to_csv helper."""
    csv_data = export_service._convert_rlhf_to_csv(sample_rlhf_interactions)

    assert isinstance(csv_data, str)
    assert "interaction_id" in csv_data
    assert "int-1" in csv_data
    assert "int-2" in csv_data


def test_convert_rlhf_to_csv_empty(export_service):
    """Test _convert_rlhf_to_csv with empty data."""
    csv_data = export_service._convert_rlhf_to_csv([])

    assert csv_data == ""


def test_generate_analytics(
    export_service,
    sample_hackathon,
    sample_participants,
    sample_submissions,
    sample_teams,
):
    """Test _generate_analytics helper."""
    analytics = export_service._generate_analytics(
        sample_hackathon,
        sample_participants,
        sample_submissions,
        sample_teams,
        [],
    )

    assert analytics["total_participants"] == 2
    assert analytics["total_submissions"] == 1
    assert analytics["total_teams"] == 1
    assert analytics["submission_rate"] == 0.5
    assert analytics["status"] == "completed"


# Edge Cases


@pytest.mark.asyncio
async def test_export_json_with_empty_related_data(
    export_service, mock_zerodb_client, sample_hackathon
):
    """Test JSON export when hackathon has no participants/submissions."""
    mock_zerodb_client.tables.query.side_effect = [
        {"rows": [sample_hackathon]},
        {"rows": []},  # No participants
        {"rows": []},  # No submissions
        {"rows": []},  # No teams
    ]

    result = await export_service.export_hackathon_json("hack-123")

    assert result["hackathon"] == sample_hackathon
    assert result["participant_count"] == 0
    assert result["submission_count"] == 0
    assert result["team_count"] == 0


@pytest.mark.asyncio
async def test_export_rlhf_no_interactions(
    export_service, mock_zerodb_client, sample_hackathon
):
    """Test RLHF export with no interactions."""
    mock_zerodb_client.tables.query.return_value = {"rows": [sample_hackathon]}
    mock_zerodb_client.rlhf.list_interactions.return_value = {"interactions": []}

    result = await export_service.export_rlhf_data("hack-123")

    assert result["total_interactions"] == 0
    assert result["interactions_with_feedback"] == 0
    assert result["feedback_rate"] == 0.0


@pytest.mark.asyncio
async def test_archive_cancelled_hackathon(
    export_service, mock_zerodb_client, sample_hackathon
):
    """Test archiving a cancelled hackathon (should succeed)."""
    cancelled_hackathon = {**sample_hackathon, "status": "cancelled"}
    mock_zerodb_client.tables.query.side_effect = [
        {"rows": [cancelled_hackathon]},
        {"rows": []},
        {"rows": []},
        {"rows": []},
        {"rows": []},
    ]

    mock_zerodb_client.rlhf.list_interactions.return_value = {"interactions": []}
    mock_zerodb_client.files.upload.return_value = {"file_id": "file-123"}
    mock_zerodb_client.files.generate_presigned_url.return_value = {
        "presigned_url": "https://example.com/archive.json"
    }

    result = await export_service.archive_hackathon("hack-123")

    assert result["success"] is True


# Integration-like Tests


@pytest.mark.asyncio
async def test_full_export_workflow(
    mock_zerodb_client,
    sample_hackathon,
    sample_participants,
    sample_submissions,
):
    """Test complete export workflow: JSON, CSV, PDF."""
    # Test JSON export
    json_service = ExportService(mock_zerodb_client)
    mock_zerodb_client.tables.query.side_effect = [
        {"rows": [sample_hackathon]},
        {"rows": sample_participants},
        {"rows": sample_submissions},
        {"rows": []},
        {"rows": []},
    ]
    json_result = await json_service.export_hackathon_json("hack-123")
    assert json_result["hackathon"] == sample_hackathon

    # Test CSV export
    csv_service = ExportService(mock_zerodb_client)
    mock_zerodb_client.tables.query.side_effect = [
        {"rows": [sample_hackathon]},
        {"rows": sample_participants},
        {"rows": sample_submissions},
        {"rows": []},
    ]
    csv_result = await csv_service.export_hackathon_csv("hack-123")
    assert "hack-123" in csv_result

    # Test PDF export
    pdf_service = ExportService(mock_zerodb_client)
    mock_zerodb_client.tables.query.side_effect = [
        {"rows": [sample_hackathon]},
        {"rows": sample_participants},
        {"rows": sample_submissions},
        {"rows": []},
        {"rows": []},
    ]
    pdf_result = await pdf_service.generate_pdf_report("hack-123")
    assert len(pdf_result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=services.export_service", "--cov-report=term-missing"])
