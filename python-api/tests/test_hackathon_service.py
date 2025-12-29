"""
Tests for Hackathon Service

Comprehensive test suite for hackathon CRUD operations.
Tests authorization, validation, error handling, and edge cases.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from integrations.zerodb.exceptions import (
    ZeroDBAuthError,
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)
from services.hackathon_service import (
    create_hackathon,
    delete_hackathon,
    get_hackathon,
    list_hackathons,
    update_hackathon,
)


# Fixtures
@pytest.fixture
def mock_zerodb_client():
    """Create a mock ZeroDB client."""
    client = MagicMock()
    client.tables = MagicMock()
    client.project_id = "test-project-123"
    return client


@pytest.fixture
def sample_hackathon_data():
    """Sample hackathon data for testing (matches existing service signature)."""
    now = datetime.utcnow()
    return {
        "name": "AI Hackathon 2024",
        "description": "Build AI-powered applications",  # Required in existing implementation
        "organizer_id": str(uuid.uuid4()),
        "start_date": now + timedelta(days=30),
        "end_date": now + timedelta(days=32),
        "location": "virtual",
        "registration_deadline": now + timedelta(days=25),
        "max_participants": 100,
        "website_url": "https://aihack2024.com",
        "prizes": {"first": 10000, "second": 5000, "third": 2500},
        "rules": "All participants must follow code of conduct",
        "status": "draft",
    }


@pytest.fixture
def sample_hackathon_row(sample_hackathon_data):
    """Sample hackathon row from ZeroDB."""
    hackathon_id = str(uuid.uuid4())
    now = datetime.utcnow()
    # Convert datetimes to ISO strings (as stored in ZeroDB)
    row_data = {
        **sample_hackathon_data,
        "start_date": sample_hackathon_data["start_date"].isoformat(),
        "end_date": sample_hackathon_data["end_date"].isoformat(),
        "registration_deadline": sample_hackathon_data["registration_deadline"].isoformat()
            if sample_hackathon_data.get("registration_deadline") else None,
    }
    return {
        "hackathon_id": hackathon_id,
        **row_data,
        "is_deleted": False,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }


# Tests for create_hackathon()
class TestCreateHackathon:
    """Tests for hackathon creation."""

    @pytest.mark.asyncio
    async def test_create_hackathon_success(self, mock_zerodb_client, sample_hackathon_data):
        """Test successful hackathon creation."""
        # Arrange
        mock_zerodb_client.tables.insert_rows = AsyncMock(
            return_value={"success": True, "row_ids": [str(uuid.uuid4())]}
        )

        # Act
        result = await create_hackathon(
            zerodb_client=mock_zerodb_client,
            **sample_hackathon_data,
        )

        # Assert
        assert "hackathon_id" in result
        assert result["name"] == sample_hackathon_data["name"]
        assert mock_zerodb_client.tables.insert_rows.call_count == 2  # hackathon + participant

    @pytest.mark.asyncio
    async def test_create_hackathon_invalid_dates(self, mock_zerodb_client, sample_hackathon_data):
        """Test creation fails when end_date is before start_date."""
        # Arrange
        sample_hackathon_data["end_date"] = sample_hackathon_data["start_date"] - timedelta(days=1)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_hackathon(
                zerodb_client=mock_zerodb_client,
                **sample_hackathon_data,
            )

        assert exc_info.value.status_code == 400
        assert "end_date" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_create_hackathon_invalid_registration_deadline(
        self, mock_zerodb_client, sample_hackathon_data
    ):
        """Test creation fails when registration_deadline is after start_date."""
        # Arrange
        sample_hackathon_data["registration_deadline"] = (
            sample_hackathon_data["start_date"] + timedelta(days=1)
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_hackathon(
                zerodb_client=mock_zerodb_client,
                **sample_hackathon_data,
            )

        assert exc_info.value.status_code == 400
        assert "registration_deadline" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_create_hackathon_invalid_status(self, mock_zerodb_client, sample_hackathon_data):
        """Test creation fails with invalid status."""
        # Arrange
        sample_hackathon_data["status"] = "invalid_status"

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_hackathon(
                zerodb_client=mock_zerodb_client,
                **sample_hackathon_data,
            )

        assert exc_info.value.status_code == 400
        assert "status" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_create_hackathon_database_timeout(
        self, mock_zerodb_client, sample_hackathon_data
    ):
        """Test creation handles database timeout."""
        # Arrange
        mock_zerodb_client.tables.insert_rows = AsyncMock(
            side_effect=ZeroDBTimeoutError("Request timeout")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_hackathon(
                zerodb_client=mock_zerodb_client,
                **sample_hackathon_data,
            )

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_create_hackathon_database_error(
        self, mock_zerodb_client, sample_hackathon_data
    ):
        """Test creation handles database errors."""
        # Arrange
        mock_zerodb_client.tables.insert_rows = AsyncMock(
            side_effect=ZeroDBError("Database error")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_hackathon(
                zerodb_client=mock_zerodb_client,
                **sample_hackathon_data,
            )

        assert exc_info.value.status_code == 500


# Tests for get_hackathon()
class TestGetHackathon:
    """Tests for retrieving a hackathon."""

    @pytest.mark.asyncio
    async def test_get_hackathon_success(self, mock_zerodb_client, sample_hackathon_row):
        """Test successfully retrieving a hackathon."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        mock_zerodb_client.tables.query_rows = AsyncMock(
            return_value=[sample_hackathon_row]
        )

        # Act
        result = await get_hackathon(
            zerodb_client=mock_zerodb_client,
            hackathon_id=hackathon_id,
        )

        # Assert
        assert result["hackathon_id"] == hackathon_id
        assert result["name"] == sample_hackathon_row["name"]
        mock_zerodb_client.tables.query_rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_hackathon_not_found(self, mock_zerodb_client):
        """Test retrieving non-existent hackathon."""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_zerodb_client.tables.query_rows = AsyncMock(return_value=[])

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_hackathon(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
            )

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_get_hackathon_deleted(self, mock_zerodb_client, sample_hackathon_row):
        """Test retrieving soft-deleted hackathon (should fail by default)."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        sample_hackathon_row["is_deleted"] = True
        mock_zerodb_client.tables.query_rows = AsyncMock(
            return_value=[sample_hackathon_row]
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_hackathon(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                include_deleted=False,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_hackathon_database_timeout(self, mock_zerodb_client):
        """Test get handles database timeout."""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=ZeroDBTimeoutError("Request timeout")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_hackathon(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
            )

        assert exc_info.value.status_code == 504


# Tests for list_hackathons()
class TestListHackathons:
    """Tests for listing hackathons."""

    @pytest.mark.asyncio
    async def test_list_hackathons_success(self, mock_zerodb_client, sample_hackathon_row):
        """Test successfully listing hackathons."""
        # Arrange
        hackathons = [sample_hackathon_row, {**sample_hackathon_row, "hackathon_id": str(uuid.uuid4())}]
        mock_zerodb_client.tables.query_rows = AsyncMock(return_value=hackathons)

        # Act
        result = await list_hackathons(
            zerodb_client=mock_zerodb_client,
            skip=0,
            limit=10,
        )

        # Assert
        assert "hackathons" in result
        assert "total" in result
        assert result["total"] == 2
        assert len(result["hackathons"]) == 2

    @pytest.mark.asyncio
    async def test_list_hackathons_with_status_filter(
        self, mock_zerodb_client, sample_hackathon_row
    ):
        """Test listing hackathons with status filter."""
        # Arrange
        mock_zerodb_client.tables.query_rows = AsyncMock(
            return_value=[sample_hackathon_row]
        )

        # Act
        result = await list_hackathons(
            zerodb_client=mock_zerodb_client,
            status_filter="draft",
            skip=0,
            limit=10,
        )

        # Assert
        assert result["total"] == 1
        # Verify filter was passed
        call_args = mock_zerodb_client.tables.query_rows.call_args
        assert call_args[1]["filter"]["status"] == "draft"

    @pytest.mark.asyncio
    async def test_list_hackathons_empty_result(self, mock_zerodb_client):
        """Test listing hackathons returns empty list."""
        # Arrange
        mock_zerodb_client.tables.query_rows = AsyncMock(return_value=[])

        # Act
        result = await list_hackathons(
            zerodb_client=mock_zerodb_client,
            skip=0,
            limit=10,
        )

        # Assert
        assert result["hackathons"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_list_hackathons_pagination(self, mock_zerodb_client, sample_hackathon_row):
        """Test hackathon listing with pagination."""
        # Arrange
        hackathons = [sample_hackathon_row] * 100
        mock_zerodb_client.tables.query_rows = AsyncMock(return_value=hackathons)

        # Act
        result = await list_hackathons(
            zerodb_client=mock_zerodb_client,
            skip=10,
            limit=20,
        )

        # Assert
        assert result["skip"] == 10
        assert result["limit"] == 20
        assert len(result["hackathons"]) == 20  # Should return 20 items from skip=10

    @pytest.mark.asyncio
    async def test_list_hackathons_invalid_pagination(self, mock_zerodb_client):
        """Test list with invalid pagination parameters."""
        # Act & Assert - negative skip
        with pytest.raises(HTTPException) as exc_info:
            await list_hackathons(
                zerodb_client=mock_zerodb_client,
                skip=-1,
                limit=10,
            )

        assert exc_info.value.status_code == 400

        # Act & Assert - limit too large
        with pytest.raises(HTTPException) as exc_info:
            await list_hackathons(
                zerodb_client=mock_zerodb_client,
                skip=0,
                limit=2000,
            )

        assert exc_info.value.status_code == 400


# Tests for update_hackathon()
class TestUpdateHackathon:
    """Tests for updating hackathons."""

    @pytest.mark.asyncio
    async def test_update_hackathon_success(
        self, mock_zerodb_client, sample_hackathon_row
    ):
        """Test successfully updating a hackathon."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        organizer_id = sample_hackathon_row["organizer_id"]
        update_data = {
            "name": "Updated Hackathon Name",
            "description": "Updated description",
        }

        # Mock get existing hackathon
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": organizer_id, "role": "organizer", "hackathon_id": hackathon_id}],  # Auth check
                [sample_hackathon_row],  # Get hackathon (first call in update)
                [{**sample_hackathon_row, **update_data}],  # Get updated hackathon
            ]
        )

        # Mock update operation
        mock_zerodb_client.tables.update_rows = AsyncMock(return_value={"success": True})

        # Act
        result = await update_hackathon(
            zerodb_client=mock_zerodb_client,
            hackathon_id=hackathon_id,
            user_id=organizer_id,
            update_data=update_data,
        )

        # Assert
        assert result["name"] == update_data["name"]
        mock_zerodb_client.tables.update_rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_hackathon_not_found(self, mock_zerodb_client):
        """Test updating non-existent hackathon."""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # Mock authorization success
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": user_id, "role": "organizer", "hackathon_id": hackathon_id}],  # Auth
                [],  # Hackathon not found
            ]
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_hackathon(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                user_id=user_id,
                update_data={"name": "New Name"},
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_hackathon_unauthorized(
        self, mock_zerodb_client, sample_hackathon_row
    ):
        """Test updating hackathon without organizer permission."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        unauthorized_user_id = str(uuid.uuid4())

        # Mock authorization failure
        mock_zerodb_client.tables.query_rows = AsyncMock(
            return_value=[]  # No participant record - unauthorized
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_hackathon(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                user_id=unauthorized_user_id,
                update_data={"name": "Hacked Name"},
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_hackathon_invalid_dates(
        self, mock_zerodb_client, sample_hackathon_row
    ):
        """Test update fails with invalid date range."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        organizer_id = sample_hackathon_row["organizer_id"]

        # Mock authorization and get hackathon
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": organizer_id, "role": "organizer", "hackathon_id": hackathon_id}],
                [sample_hackathon_row],
            ]
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_hackathon(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                user_id=organizer_id,
                update_data={"end_date": datetime.fromisoformat(sample_hackathon_row["start_date"]) - timedelta(days=1)},
            )

        assert exc_info.value.status_code == 400
        assert "end_date" in str(exc_info.value.detail).lower()


# Tests for delete_hackathon()
class TestDeleteHackathon:
    """Tests for deleting hackathons."""

    @pytest.mark.asyncio
    async def test_delete_hackathon_success(
        self, mock_zerodb_client, sample_hackathon_row
    ):
        """Test successfully deleting a hackathon."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        organizer_id = sample_hackathon_row["organizer_id"]

        # Mock get hackathon and auth check
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": organizer_id, "role": "organizer", "hackathon_id": hackathon_id}],  # Auth
                [sample_hackathon_row],  # Get hackathon
            ]
        )

        # Mock delete operation
        mock_zerodb_client.tables.update_rows = AsyncMock(
            return_value={"success": True}
        )

        # Act
        result = await delete_hackathon(
            zerodb_client=mock_zerodb_client,
            hackathon_id=hackathon_id,
            user_id=organizer_id,
        )

        # Assert
        assert result["success"] is True
        assert result["hackathon_id"] == hackathon_id
        mock_zerodb_client.tables.update_rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_hackathon_not_found(self, mock_zerodb_client):
        """Test deleting non-existent hackathon."""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # Mock authorization success
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": user_id, "role": "organizer", "hackathon_id": hackathon_id}],  # Auth
                [],  # Hackathon not found
            ]
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_hackathon(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                user_id=user_id,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_hackathon_unauthorized(
        self, mock_zerodb_client, sample_hackathon_row
    ):
        """Test deleting hackathon without organizer permission."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        unauthorized_user_id = str(uuid.uuid4())

        # Mock get hackathon
        mock_zerodb_client.tables.query_rows = AsyncMock(
            return_value=[]  # No participant - unauthorized
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_hackathon(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                user_id=unauthorized_user_id,
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_hackathon_already_deleted(
        self, mock_zerodb_client, sample_hackathon_row
    ):
        """Test deleting already deleted hackathon."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        organizer_id = sample_hackathon_row["organizer_id"]
        sample_hackathon_row["is_deleted"] = True

        # Mock authorization and get hackathon
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": organizer_id, "role": "organizer", "hackathon_id": hackathon_id}],
                [sample_hackathon_row],
            ]
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_hackathon(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                user_id=organizer_id,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_hackathon_database_error(
        self, mock_zerodb_client, sample_hackathon_row
    ):
        """Test delete handles database errors."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        organizer_id = sample_hackathon_row["organizer_id"]

        # Mock get hackathon and auth
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": organizer_id, "role": "organizer", "hackathon_id": hackathon_id}],
                [sample_hackathon_row],
            ]
        )

        # Mock delete failure
        mock_zerodb_client.tables.update_rows = AsyncMock(
            side_effect=ZeroDBError("Database error")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_hackathon(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                user_id=organizer_id,
            )

        assert exc_info.value.status_code == 500
