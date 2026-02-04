"""
Tests for Prize Service Business Logic

Tests service-level logic for prize management with database operations.
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from services.prize_service import PrizeService


@pytest.fixture
def mock_zerodb_client():
    """Mock ZeroDB client"""
    return AsyncMock()


@pytest.fixture
def prize_service(mock_zerodb_client):
    """Prize service instance with mocked ZeroDB"""
    return PrizeService(mock_zerodb_client)


class TestCreatePrize:
    """Test create_prize service method"""

    @pytest.mark.asyncio
    async def test_create_prize_success(self, prize_service, mock_zerodb_client):
        """Should create prize successfully"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        # Mock hackathon exists
        mock_zerodb_client.tables.query_rows.return_value = [
            {"hackathon_id": hackathon_id, "is_deleted": False}
        ]

        # Mock no duplicate prizes
        async def mock_query(table, filter):
            if table == "hackathons":
                return [{"hackathon_id": hackathon_id, "is_deleted": False}]
            elif table == "prizes":
                return []  # No existing prizes
            return []

        mock_zerodb_client.tables.query_rows.side_effect = mock_query
        mock_zerodb_client.tables.insert_rows.return_value = None

        # Act
        result = await prize_service.create_prize(
            hackathon_id=hackathon_id,
            title="Grand Prize",
            rank=1,
            amount=Decimal("10000.00"),
            currency="USD",
        )

        # Assert
        assert result["title"] == "Grand Prize"
        assert result["rank"] == 1
        assert result["amount"] == Decimal("10000.00")
        assert result["currency"] == "USD"
        assert result["hackathon_id"] == hackathon_id

    @pytest.mark.asyncio
    async def test_create_prize_hackathon_not_found(
        self, prize_service, mock_zerodb_client
    ):
        """Should raise 404 when hackathon not found"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_zerodb_client.tables.query_rows.return_value = []  # Hackathon not found

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await prize_service.create_prize(
                hackathon_id=hackathon_id,
                title="Grand Prize",
                rank=1,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_prize_duplicate_rank(
        self, prize_service, mock_zerodb_client
    ):
        """Should raise 409 when rank already exists"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        async def mock_query(table, filter):
            if table == "hackathons":
                return [{"hackathon_id": hackathon_id, "is_deleted": False}]
            elif table == "prizes" and filter.get("rank") == 1:
                return [
                    {"prize_id": str(uuid.uuid4()), "rank": 1}
                ]  # Duplicate rank
            return []

        mock_zerodb_client.tables.query_rows.side_effect = mock_query

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await prize_service.create_prize(
                hackathon_id=hackathon_id,
                title="Grand Prize",
                rank=1,
            )

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_create_prize_with_track(self, prize_service, mock_zerodb_client):
        """Should create track-specific prize"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        track_id = str(uuid.uuid4())

        async def mock_query(table, filter):
            if table == "hackathons":
                return [{"hackathon_id": hackathon_id, "is_deleted": False}]
            elif table == "tracks":
                return [
                    {"track_id": track_id, "hackathon_id": hackathon_id}
                ]  # Track exists
            elif table == "prizes":
                return []  # No duplicates
            return []

        mock_zerodb_client.tables.query_rows.side_effect = mock_query
        mock_zerodb_client.tables.insert_rows.return_value = None

        # Act
        result = await prize_service.create_prize(
            hackathon_id=hackathon_id,
            title="Best AI Project",
            rank=1,
            track_id=track_id,
        )

        # Assert
        assert result["track_id"] == track_id


class TestListPrizes:
    """Test list_prizes service method"""

    @pytest.mark.asyncio
    async def test_list_prizes_success(self, prize_service, mock_zerodb_client):
        """Should list prizes with prize pool"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        async def mock_query(table, filter):
            if table == "hackathons":
                return [{"hackathon_id": hackathon_id, "is_deleted": False}]
            elif table == "prizes":
                return [
                    {
                        "prize_id": str(uuid.uuid4()),
                        "hackathon_id": hackathon_id,
                        "title": "Grand Prize",
                        "amount": "10000.00",
                        "currency": "USD",
                        "rank": 1,
                        "display_order": 1,
                        "created_at": "2024-01-01T00:00:00",
                        "updated_at": "2024-01-01T00:00:00",
                    },
                    {
                        "prize_id": str(uuid.uuid4()),
                        "hackathon_id": hackathon_id,
                        "title": "Runner Up",
                        "amount": "5000.00",
                        "currency": "USD",
                        "rank": 2,
                        "display_order": 2,
                        "created_at": "2024-01-01T00:00:00",
                        "updated_at": "2024-01-01T00:00:00",
                    },
                ]
            return []

        mock_zerodb_client.tables.query_rows.side_effect = mock_query

        # Act
        result = await prize_service.list_prizes(hackathon_id)

        # Assert
        assert result["total"] == 2
        assert len(result["prizes"]) == 2
        assert result["total_prize_pool"]["USD"] == 15000.00


class TestGetPrize:
    """Test get_prize service method"""

    @pytest.mark.asyncio
    async def test_get_prize_success(self, prize_service, mock_zerodb_client):
        """Should get prize by ID"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_zerodb_client.tables.query_rows.return_value = [
            {
                "prize_id": prize_id,
                "hackathon_id": hackathon_id,
                "title": "Grand Prize",
                "amount": "10000.00",
                "currency": "USD",
                "rank": 1,
                "display_order": 1,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
            }
        ]

        # Act
        result = await prize_service.get_prize(hackathon_id, prize_id)

        # Assert
        assert result["prize_id"] == prize_id
        assert result["title"] == "Grand Prize"

    @pytest.mark.asyncio
    async def test_get_prize_not_found(self, prize_service, mock_zerodb_client):
        """Should raise 404 when prize not found"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        mock_zerodb_client.tables.query_rows.return_value = []

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await prize_service.get_prize(hackathon_id, prize_id)

        assert exc_info.value.status_code == 404


class TestUpdatePrize:
    """Test update_prize service method"""

    @pytest.mark.asyncio
    async def test_update_prize_success(self, prize_service, mock_zerodb_client):
        """Should update prize successfully"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        async def mock_query(table, filter):
            if "prize_id" in filter:
                return [
                    {
                        "prize_id": prize_id,
                        "hackathon_id": hackathon_id,
                        "title": "Updated Prize",
                        "rank": 1,
                        "amount": "15000.00",
                        "currency": "USD",
                        "display_order": 1,
                        "created_at": "2024-01-01T00:00:00",
                        "updated_at": "2024-01-02T00:00:00",
                    }
                ]
            return []

        mock_zerodb_client.tables.query_rows.side_effect = mock_query
        mock_zerodb_client.tables.update_rows.return_value = None

        # Act
        result = await prize_service.update_prize(
            hackathon_id=hackathon_id,
            prize_id=prize_id,
            update_data={"title": "Updated Prize", "amount": Decimal("15000.00")},
        )

        # Assert
        assert result["title"] == "Updated Prize"

    @pytest.mark.asyncio
    async def test_update_prize_not_found(self, prize_service, mock_zerodb_client):
        """Should raise 404 when prize not found"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        mock_zerodb_client.tables.query_rows.return_value = []

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await prize_service.update_prize(
                hackathon_id=hackathon_id,
                prize_id=prize_id,
                update_data={"title": "Updated"},
            )

        assert exc_info.value.status_code == 404


class TestDeletePrize:
    """Test delete_prize service method"""

    @pytest.mark.asyncio
    async def test_delete_prize_success(self, prize_service, mock_zerodb_client):
        """Should delete prize successfully"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_zerodb_client.tables.query_rows.return_value = [
            {"prize_id": prize_id, "hackathon_id": hackathon_id}
        ]
        mock_zerodb_client.tables.delete_rows.return_value = None

        # Act
        result = await prize_service.delete_prize(hackathon_id, prize_id)

        # Assert
        assert result["success"] is True
        assert result["prize_id"] == prize_id

    @pytest.mark.asyncio
    async def test_delete_prize_not_found(self, prize_service, mock_zerodb_client):
        """Should raise 404 when prize not found"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        mock_zerodb_client.tables.query_rows.return_value = []

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await prize_service.delete_prize(hackathon_id, prize_id)

        assert exc_info.value.status_code == 404


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_create_prize_with_display_order(
        self, prize_service, mock_zerodb_client
    ):
        """Should create prize with custom display order"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        async def mock_query(table, filter):
            if table == "hackathons":
                return [{"hackathon_id": hackathon_id, "is_deleted": False}]
            return []

        mock_zerodb_client.tables.query_rows.side_effect = mock_query
        mock_zerodb_client.tables.insert_rows.return_value = None

        # Act
        result = await prize_service.create_prize(
            hackathon_id=hackathon_id,
            title="Special Prize",
            rank=3,
            display_order=1,
        )

        # Assert
        assert result["display_order"] == 1
        assert result["rank"] == 3

    @pytest.mark.asyncio
    async def test_create_prize_track_not_found(
        self, prize_service, mock_zerodb_client
    ):
        """Should raise 404 when track not found"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        track_id = str(uuid.uuid4())

        async def mock_query(table, filter):
            if table == "hackathons":
                return [{"hackathon_id": hackathon_id, "is_deleted": False}]
            elif table == "tracks":
                return []  # Track not found
            return []

        mock_zerodb_client.tables.query_rows.side_effect = mock_query

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await prize_service.create_prize(
                hackathon_id=hackathon_id,
                title="Track Prize",
                rank=1,
                track_id=track_id,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_list_prizes_filter_by_track(
        self, prize_service, mock_zerodb_client
    ):
        """Should filter prizes by track_id"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        track_id = str(uuid.uuid4())

        async def mock_query(table, filter):
            if table == "hackathons":
                return [{"hackathon_id": hackathon_id, "is_deleted": False}]
            elif table == "prizes" and filter.get("track_id") == track_id:
                return [
                    {
                        "prize_id": str(uuid.uuid4()),
                        "hackathon_id": hackathon_id,
                        "title": "Track Prize",
                        "track_id": track_id,
                        "amount": "3000.00",
                        "currency": "USD",
                        "rank": 1,
                        "display_order": 1,
                        "created_at": "2024-01-01T00:00:00",
                        "updated_at": "2024-01-01T00:00:00",
                    }
                ]
            return []

        mock_zerodb_client.tables.query_rows.side_effect = mock_query

        # Act
        result = await prize_service.list_prizes(hackathon_id, track_id=track_id)

        # Assert
        assert result["total"] == 1
        assert result["prizes"][0]["track_id"] == track_id

    @pytest.mark.asyncio
    async def test_list_prizes_filter_by_rank(
        self, prize_service, mock_zerodb_client
    ):
        """Should filter prizes by rank"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        async def mock_query(table, filter):
            if table == "hackathons":
                return [{"hackathon_id": hackathon_id, "is_deleted": False}]
            elif table == "prizes" and filter.get("rank") == 1:
                return [
                    {
                        "prize_id": str(uuid.uuid4()),
                        "hackathon_id": hackathon_id,
                        "title": "First Place",
                        "rank": 1,
                        "amount": "10000.00",
                        "currency": "USD",
                        "display_order": 1,
                        "created_at": "2024-01-01T00:00:00",
                        "updated_at": "2024-01-01T00:00:00",
                    }
                ]
            return []

        mock_zerodb_client.tables.query_rows.side_effect = mock_query

        # Act
        result = await prize_service.list_prizes(hackathon_id, rank=1)

        # Assert
        assert result["total"] == 1
        assert result["prizes"][0]["rank"] == 1

    @pytest.mark.asyncio
    async def test_update_prize_with_track_change(
        self, prize_service, mock_zerodb_client
    ):
        """Should update prize with track change"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        new_track_id = str(uuid.uuid4())

        async def mock_query(table, filter):
            if "prize_id" in filter and table == "prizes":
                if len([k for k in filter.keys() if k != "prize_id"]) == 1:
                    # Initial query for existing prize
                    return [
                        {
                            "prize_id": prize_id,
                            "hackathon_id": hackathon_id,
                            "rank": 1,
                            "track_id": None,
                        }
                    ]
                else:
                    # Updated prize query
                    return [
                        {
                            "prize_id": prize_id,
                            "hackathon_id": hackathon_id,
                            "title": "Updated Prize",
                            "rank": 1,
                            "track_id": new_track_id,
                            "amount": "10000.00",
                            "currency": "USD",
                            "display_order": 1,
                            "created_at": "2024-01-01T00:00:00",
                            "updated_at": "2024-01-02T00:00:00",
                        }
                    ]
            elif table == "tracks":
                return [
                    {"track_id": new_track_id, "hackathon_id": hackathon_id}
                ]  # Track exists
            elif table == "prizes" and filter.get("track_id") == new_track_id:
                return []  # No rank conflicts
            return []

        mock_zerodb_client.tables.query_rows.side_effect = mock_query
        mock_zerodb_client.tables.update_rows.return_value = None

        # Act
        result = await prize_service.update_prize(
            hackathon_id=hackathon_id,
            prize_id=prize_id,
            update_data={"track_id": new_track_id},
        )

        # Assert
        assert result["track_id"] == new_track_id

    @pytest.mark.asyncio
    async def test_update_prize_rank_conflict(
        self, prize_service, mock_zerodb_client
    ):
        """Should raise 409 when updating to conflicting rank"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        other_prize_id = str(uuid.uuid4())

        async def mock_query(table, filter):
            if "prize_id" in filter and len(filter) == 2:
                # Initial prize query
                return [
                    {
                        "prize_id": prize_id,
                        "hackathon_id": hackathon_id,
                        "rank": 2,
                    }
                ]
            elif "rank" in filter and filter.get("rank") == 1:
                # Check for rank conflict
                return [
                    {"prize_id": other_prize_id, "rank": 1}
                ]  # Different prize has rank 1
            return []

        mock_zerodb_client.tables.query_rows.side_effect = mock_query

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await prize_service.update_prize(
                hackathon_id=hackathon_id,
                prize_id=prize_id,
                update_data={"rank": 1},
            )

        assert exc_info.value.status_code == 409
