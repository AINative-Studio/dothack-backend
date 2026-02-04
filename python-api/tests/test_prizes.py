"""
Tests for Prizes API Endpoints

Tests all prize CRUD endpoints for hackathon prize management.
Uses TestClient for integration testing with mocked dependencies.
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from api.routes.prizes import get_current_user, get_zerodb_client, router
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBNotFound


# Create test app with prizes router
app = FastAPI()
app.include_router(router)


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    return {
        "id": str(uuid.uuid4()),
        "email": "organizer@example.com",
        "name": "Test Organizer",
    }


@pytest.fixture
def mock_zerodb_client():
    """Mock ZeroDB client"""
    return AsyncMock()


@pytest.fixture
def client(mock_user, mock_zerodb_client):
    """Test client with dependency overrides"""

    async def override_get_current_user():
        return mock_user

    async def override_get_zerodb_client():
        return mock_zerodb_client

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_zerodb_client] = override_get_zerodb_client

    yield TestClient(app)

    # Clean up
    app.dependency_overrides.clear()


class TestCreatePrizeEndpoint:
    """Test POST /hackathons/{hackathon_id}/prizes - Create prize"""

    @patch("api.routes.prizes.PrizeService.create_prize")
    @patch("api.routes.prizes.check_organizer")
    def test_create_prize_success(
        self, mock_check_organizer, mock_create, client, mock_user
    ):
        """Should create prize and return 201"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_check_organizer.return_value = None
        mock_create.return_value = {
            "prize_id": prize_id,
            "hackathon_id": hackathon_id,
            "title": "Grand Prize",
            "description": "Overall winner",
            "amount": Decimal("10000.00"),
            "currency": "USD",
            "rank": 1,
            "track_id": None,
            "sponsor_name": "Tech Corp",
            "display_order": 1,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/prizes",
            json={
                "title": "Grand Prize",
                "description": "Overall winner",
                "amount": 10000.00,
                "currency": "USD",
                "rank": 1,
                "sponsor_name": "Tech Corp",
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["prize_id"] == prize_id
        assert data["title"] == "Grand Prize"
        assert data["rank"] == 1
        assert data["amount"] == "10000.00"
        assert data["currency"] == "USD"

    @patch("api.routes.prizes.PrizeService.create_prize")
    @patch("api.routes.prizes.check_organizer")
    def test_create_prize_track_specific(
        self, mock_check_organizer, mock_create, client
    ):
        """Should create track-specific prize"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        track_id = str(uuid.uuid4())

        mock_check_organizer.return_value = None
        mock_create.return_value = {
            "prize_id": prize_id,
            "hackathon_id": hackathon_id,
            "title": "Best AI Project",
            "description": "Most innovative AI implementation",
            "amount": Decimal("5000.00"),
            "currency": "USD",
            "rank": 1,
            "track_id": track_id,
            "sponsor_name": None,
            "display_order": 1,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/prizes",
            json={
                "title": "Best AI Project",
                "description": "Most innovative AI implementation",
                "amount": 5000.00,
                "currency": "USD",
                "rank": 1,
                "track_id": track_id,
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["track_id"] == track_id
        assert data["title"] == "Best AI Project"

    @patch("api.routes.prizes.PrizeService.create_prize")
    @patch("api.routes.prizes.check_organizer")
    def test_create_prize_minimal_fields(
        self, mock_check_organizer, mock_create, client
    ):
        """Should create prize with only required fields"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_check_organizer.return_value = None
        mock_create.return_value = {
            "prize_id": prize_id,
            "hackathon_id": hackathon_id,
            "title": "Runner Up",
            "description": None,
            "amount": None,
            "currency": "USD",
            "rank": 2,
            "track_id": None,
            "sponsor_name": None,
            "display_order": 2,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/prizes",
            json={"title": "Runner Up", "rank": 2},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Runner Up"
        assert data["rank"] == 2
        assert data["amount"] is None

    @patch("api.routes.prizes.check_organizer")
    def test_create_prize_invalid_title_too_short(self, mock_check_organizer, client):
        """Should reject prize with title too short"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_check_organizer.return_value = None

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/prizes",
            json={"title": "AI", "rank": 1},  # Less than 3 chars
        )

        # Assert
        assert response.status_code == 422

    @patch("api.routes.prizes.check_organizer")
    def test_create_prize_invalid_rank_zero(self, mock_check_organizer, client):
        """Should reject prize with invalid rank"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_check_organizer.return_value = None

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/prizes",
            json={"title": "Grand Prize", "rank": 0},  # Rank must be >= 1
        )

        # Assert
        assert response.status_code == 422

    @patch("api.routes.prizes.check_organizer")
    def test_create_prize_invalid_amount_negative(self, mock_check_organizer, client):
        """Should reject prize with negative amount"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_check_organizer.return_value = None

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/prizes",
            json={"title": "Grand Prize", "rank": 1, "amount": -1000},
        )

        # Assert
        assert response.status_code == 422


class TestListPrizesEndpoint:
    """Test GET /hackathons/{hackathon_id}/prizes - List prizes"""

    @patch("api.routes.prizes.PrizeService.list_prizes")
    def test_list_prizes_success(self, mock_list, client):
        """Should return list of prizes with prize pool"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        prize1_id = str(uuid.uuid4())
        prize2_id = str(uuid.uuid4())

        mock_list.return_value = {
            "prizes": [
                {
                    "prize_id": prize1_id,
                    "hackathon_id": hackathon_id,
                    "title": "Grand Prize",
                    "description": "Overall winner",
                    "amount": Decimal("10000.00"),
                    "currency": "USD",
                    "rank": 1,
                    "track_id": None,
                    "sponsor_name": "Tech Corp",
                    "display_order": 1,
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00",
                },
                {
                    "prize_id": prize2_id,
                    "hackathon_id": hackathon_id,
                    "title": "Runner Up",
                    "description": "Second place",
                    "amount": Decimal("5000.00"),
                    "currency": "USD",
                    "rank": 2,
                    "track_id": None,
                    "sponsor_name": None,
                    "display_order": 2,
                    "created_at": "2024-01-02T00:00:00",
                    "updated_at": "2024-01-02T00:00:00",
                },
            ],
            "total": 2,
            "hackathon_id": hackathon_id,
            "total_prize_pool": {"USD": 15000.00},
        }

        # Act
        response = client.get(f"/api/v1/hackathons/{hackathon_id}/prizes")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["prizes"]) == 2
        assert data["prizes"][0]["title"] == "Grand Prize"
        assert data["prizes"][1]["title"] == "Runner Up"
        assert data["total_prize_pool"]["USD"] == 15000.00

    @patch("api.routes.prizes.PrizeService.list_prizes")
    def test_list_prizes_empty(self, mock_list, client):
        """Should return empty list when no prizes"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_list.return_value = {
            "prizes": [],
            "total": 0,
            "hackathon_id": hackathon_id,
            "total_prize_pool": None,
        }

        # Act
        response = client.get(f"/api/v1/hackathons/{hackathon_id}/prizes")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["prizes"]) == 0
        assert data["total_prize_pool"] is None

    @patch("api.routes.prizes.PrizeService.list_prizes")
    def test_list_prizes_filter_by_track(self, mock_list, client):
        """Should filter prizes by track_id"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        track_id = str(uuid.uuid4())
        prize_id = str(uuid.uuid4())

        mock_list.return_value = {
            "prizes": [
                {
                    "prize_id": prize_id,
                    "hackathon_id": hackathon_id,
                    "title": "Best AI Project",
                    "description": "Track-specific prize",
                    "amount": Decimal("3000.00"),
                    "currency": "USD",
                    "rank": 1,
                    "track_id": track_id,
                    "sponsor_name": None,
                    "display_order": 1,
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00",
                }
            ],
            "total": 1,
            "hackathon_id": hackathon_id,
            "total_prize_pool": {"USD": 3000.00},
        }

        # Act
        response = client.get(
            f"/api/v1/hackathons/{hackathon_id}/prizes?track_id={track_id}"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["prizes"][0]["track_id"] == track_id

    @patch("api.routes.prizes.PrizeService.list_prizes")
    def test_list_prizes_filter_by_rank(self, mock_list, client):
        """Should filter prizes by rank"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        prize_id = str(uuid.uuid4())

        mock_list.return_value = {
            "prizes": [
                {
                    "prize_id": prize_id,
                    "hackathon_id": hackathon_id,
                    "title": "Grand Prize",
                    "description": "First place",
                    "amount": Decimal("10000.00"),
                    "currency": "USD",
                    "rank": 1,
                    "track_id": None,
                    "sponsor_name": None,
                    "display_order": 1,
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00",
                }
            ],
            "total": 1,
            "hackathon_id": hackathon_id,
            "total_prize_pool": {"USD": 10000.00},
        }

        # Act
        response = client.get(f"/api/v1/hackathons/{hackathon_id}/prizes?rank=1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["prizes"][0]["rank"] == 1


class TestGetPrizeEndpoint:
    """Test GET /hackathons/{hackathon_id}/prizes/{prize_id} - Get prize"""

    @patch("api.routes.prizes.PrizeService.get_prize")
    def test_get_prize_success(self, mock_get, client):
        """Should return single prize"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_get.return_value = {
            "prize_id": prize_id,
            "hackathon_id": hackathon_id,
            "title": "Grand Prize",
            "description": "Overall winner",
            "amount": Decimal("10000.00"),
            "currency": "USD",
            "rank": 1,
            "track_id": None,
            "sponsor_name": "Tech Corp",
            "display_order": 1,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.get(
            f"/api/v1/hackathons/{hackathon_id}/prizes/{prize_id}"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["prize_id"] == prize_id
        assert data["title"] == "Grand Prize"
        assert data["amount"] == "10000.00"

    @patch("api.routes.prizes.PrizeService.get_prize")
    def test_get_prize_not_found(self, mock_get, client):
        """Should return 404 when prize not found"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        from fastapi import HTTPException, status
        mock_get.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prize {prize_id} not found"
        )

        # Act
        response = client.get(
            f"/api/v1/hackathons/{hackathon_id}/prizes/{prize_id}"
        )

        # Assert
        assert response.status_code == 404


class TestUpdatePrizeEndpoint:
    """Test PUT /hackathons/{hackathon_id}/prizes/{prize_id} - Update prize"""

    @patch("api.routes.prizes.PrizeService.update_prize")
    @patch("api.routes.prizes.check_organizer")
    def test_update_prize_success(
        self, mock_check_organizer, mock_update, client, mock_user
    ):
        """Should update prize and return updated data"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_check_organizer.return_value = None
        mock_update.return_value = {
            "prize_id": prize_id,
            "hackathon_id": hackathon_id,
            "title": "Updated Grand Prize",
            "description": "Updated description",
            "amount": Decimal("15000.00"),
            "currency": "USD",
            "rank": 1,
            "track_id": None,
            "sponsor_name": "New Sponsor",
            "display_order": 1,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
        }

        # Act
        response = client.put(
            f"/api/v1/hackathons/{hackathon_id}/prizes/{prize_id}",
            json={
                "title": "Updated Grand Prize",
                "description": "Updated description",
                "amount": 15000.00,
                "sponsor_name": "New Sponsor",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Grand Prize"
        assert data["amount"] == "15000.00"
        assert data["sponsor_name"] == "New Sponsor"

    @patch("api.routes.prizes.PrizeService.get_prize")
    @patch("api.routes.prizes.check_organizer")
    def test_update_prize_no_changes(self, mock_check_organizer, mock_get, client):
        """Should return existing prize when no update data provided"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_check_organizer.return_value = None
        mock_get.return_value = {
            "prize_id": prize_id,
            "hackathon_id": hackathon_id,
            "title": "Grand Prize",
            "description": "Original description",
            "amount": Decimal("10000.00"),
            "currency": "USD",
            "rank": 1,
            "track_id": None,
            "sponsor_name": "Tech Corp",
            "display_order": 1,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.put(
            f"/api/v1/hackathons/{hackathon_id}/prizes/{prize_id}",
            json={},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Grand Prize"

    @patch("api.routes.prizes.PrizeService.update_prize")
    @patch("api.routes.prizes.check_organizer")
    def test_update_prize_change_rank(
        self, mock_check_organizer, mock_update, client
    ):
        """Should successfully update prize rank"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_check_organizer.return_value = None
        mock_update.return_value = {
            "prize_id": prize_id,
            "hackathon_id": hackathon_id,
            "title": "Grand Prize",
            "description": "Overall winner",
            "amount": Decimal("10000.00"),
            "currency": "USD",
            "rank": 2,  # Changed from 1 to 2
            "track_id": None,
            "sponsor_name": "Tech Corp",
            "display_order": 2,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
        }

        # Act
        response = client.put(
            f"/api/v1/hackathons/{hackathon_id}/prizes/{prize_id}",
            json={"rank": 2},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["rank"] == 2


class TestDeletePrizeEndpoint:
    """Test DELETE /hackathons/{hackathon_id}/prizes/{prize_id} - Delete prize"""

    @patch("api.routes.prizes.PrizeService.delete_prize")
    @patch("api.routes.prizes.check_organizer")
    def test_delete_prize_success(
        self, mock_check_organizer, mock_delete, client, mock_user
    ):
        """Should delete prize and return 204"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_check_organizer.return_value = None
        mock_delete.return_value = None

        # Act
        response = client.delete(
            f"/api/v1/hackathons/{hackathon_id}/prizes/{prize_id}"
        )

        # Assert
        assert response.status_code == 204

    @patch("api.routes.prizes.PrizeService.delete_prize")
    @patch("api.routes.prizes.check_organizer")
    def test_delete_prize_not_found(
        self, mock_check_organizer, mock_delete, client
    ):
        """Should return 404 when prize not found"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_check_organizer.return_value = None
        from fastapi import HTTPException, status
        mock_delete.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prize {prize_id} not found"
        )

        # Act
        response = client.delete(
            f"/api/v1/hackathons/{hackathon_id}/prizes/{prize_id}"
        )

        # Assert
        assert response.status_code == 404


class TestPrizeBusinessLogic:
    """Test prize business logic and validation"""

    @patch("api.routes.prizes.PrizeService.create_prize")
    @patch("api.routes.prizes.check_organizer")
    def test_prize_currency_uppercase_conversion(
        self, mock_check_organizer, mock_create, client
    ):
        """Should convert currency to uppercase"""
        # Arrange
        prize_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_check_organizer.return_value = None
        mock_create.return_value = {
            "prize_id": prize_id,
            "hackathon_id": hackathon_id,
            "title": "Grand Prize",
            "description": None,
            "amount": Decimal("10000.00"),
            "currency": "EUR",  # Stored as uppercase
            "rank": 1,
            "track_id": None,
            "sponsor_name": None,
            "display_order": 1,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/prizes",
            json={
                "title": "Grand Prize",
                "rank": 1,
                "amount": 10000.00,
                "currency": "eur",  # Lowercase input
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["currency"] == "EUR"

    @patch("api.routes.prizes.PrizeService.list_prizes")
    def test_prize_pool_multiple_currencies(self, mock_list, client):
        """Should calculate prize pool for multiple currencies"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        mock_list.return_value = {
            "prizes": [
                {
                    "prize_id": str(uuid.uuid4()),
                    "hackathon_id": hackathon_id,
                    "title": "USD Prize",
                    "description": None,
                    "amount": Decimal("10000.00"),
                    "currency": "USD",
                    "rank": 1,
                    "track_id": None,
                    "sponsor_name": None,
                    "display_order": 1,
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00",
                },
                {
                    "prize_id": str(uuid.uuid4()),
                    "hackathon_id": hackathon_id,
                    "title": "EUR Prize",
                    "description": None,
                    "amount": Decimal("5000.00"),
                    "currency": "EUR",
                    "rank": 2,
                    "track_id": None,
                    "sponsor_name": None,
                    "display_order": 2,
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00",
                },
            ],
            "total": 2,
            "hackathon_id": hackathon_id,
            "total_prize_pool": {"USD": 10000.00, "EUR": 5000.00},
        }

        # Act
        response = client.get(f"/api/v1/hackathons/{hackathon_id}/prizes")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_prize_pool"]["USD"] == 10000.00
        assert data["total_prize_pool"]["EUR"] == 5000.00
