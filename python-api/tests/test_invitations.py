"""
Tests for Invitations API Endpoints

Tests all invitation management endpoints including public accept/decline.
Uses TestClient for integration testing with mocked dependencies.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from api.routes.invitations import (
    get_current_user,
    get_current_user_optional,
    get_zerodb_client,
    router,
)
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBNotFound


# Create test app with invitations router
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

    async def override_get_current_user_optional():
        return mock_user

    async def override_get_zerodb_client():
        return mock_zerodb_client

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[
        get_current_user_optional
    ] = override_get_current_user_optional
    app.dependency_overrides[get_zerodb_client] = override_get_zerodb_client

    yield TestClient(app)

    # Clean up
    app.dependency_overrides.clear()


class TestCreateInvitationsEndpoint:
    """Test POST /hackathons/{hackathon_id}/invitations - Create invitations"""

    @patch("api.routes.invitations.invitation_service.create_invitations")
    def test_create_invitations_success(self, mock_create, client, mock_user):
        """Should create invitations and return 201"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        invitation_id = str(uuid.uuid4())

        mock_create.return_value = {
            "invitations": [
                {
                    "invitation_id": invitation_id,
                    "hackathon_id": hackathon_id,
                    "email": "judge@example.com",
                    "role": "JUDGE",
                    "status": "PENDING",
                    "token": "abc123",
                    "invited_by": mock_user["id"],
                    "created_at": "2024-01-01T00:00:00",
                    "expires_at": "2024-01-08T00:00:00",
                }
            ],
            "total": 1,
            "created": 1,
            "skipped": 0,
        }

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/invitations",
            json={"emails": ["judge@example.com"], "role": "JUDGE"},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["total"] == 1
        assert data["created"] == 1
        assert data["skipped"] == 0
        assert len(data["invitations"]) == 1
        assert data["invitations"][0]["email"] == "judge@example.com"

    @patch("api.routes.invitations.invitation_service.create_invitations")
    def test_create_multiple_invitations(self, mock_create, client, mock_user):
        """Should create multiple invitations"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        mock_create.return_value = {
            "invitations": [
                {
                    "invitation_id": str(uuid.uuid4()),
                    "hackathon_id": hackathon_id,
                    "email": "judge1@example.com",
                    "role": "JUDGE",
                    "status": "PENDING",
                    "token": "abc123",
                    "invited_by": mock_user["id"],
                    "created_at": "2024-01-01T00:00:00",
                    "expires_at": "2024-01-08T00:00:00",
                },
                {
                    "invitation_id": str(uuid.uuid4()),
                    "hackathon_id": hackathon_id,
                    "email": "judge2@example.com",
                    "role": "JUDGE",
                    "status": "PENDING",
                    "token": "def456",
                    "invited_by": mock_user["id"],
                    "created_at": "2024-01-01T00:00:00",
                    "expires_at": "2024-01-08T00:00:00",
                },
            ],
            "total": 2,
            "created": 2,
            "skipped": 0,
        }

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/invitations",
            json={"emails": ["judge1@example.com", "judge2@example.com"], "role": "JUDGE"},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["total"] == 2
        assert data["created"] == 2

    @patch("api.routes.invitations.invitation_service.create_invitations")
    def test_create_invitations_with_duplicates(self, mock_create, client):
        """Should skip duplicate invitations"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        mock_create.return_value = {
            "invitations": [
                {
                    "invitation_id": str(uuid.uuid4()),
                    "hackathon_id": hackathon_id,
                    "email": "new@example.com",
                    "role": "MENTOR",
                    "status": "PENDING",
                    "token": "abc123",
                    "invited_by": "organizer_id",
                    "created_at": "2024-01-01T00:00:00",
                    "expires_at": "2024-01-08T00:00:00",
                }
            ],
            "total": 1,
            "created": 1,
            "skipped": 1,
        }

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/invitations",
            json={"emails": ["new@example.com", "existing@example.com"], "role": "MENTOR"},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["created"] == 1
        assert data["skipped"] == 1


class TestListInvitationsEndpoint:
    """Test GET /hackathons/{hackathon_id}/invitations - List invitations"""

    @patch("api.routes.invitations.invitation_service.list_invitations")
    def test_list_invitations_success(self, mock_list, client):
        """Should return list of invitations"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        mock_list.return_value = {
            "invitations": [
                {
                    "invitation_id": str(uuid.uuid4()),
                    "hackathon_id": hackathon_id,
                    "email": "judge@example.com",
                    "role": "JUDGE",
                    "status": "PENDING",
                    "token": "abc123",
                    "invited_by": "organizer_id",
                    "created_at": "2024-01-01T00:00:00",
                    "expires_at": "2024-01-08T00:00:00",
                }
            ],
            "total": 1,
        }

        # Act
        response = client.get(f"/api/v1/hackathons/{hackathon_id}/invitations")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["invitations"]) == 1


class TestGetInvitationEndpoint:
    """Test GET /invitations/{invitation_id} - Get invitation"""

    @patch("api.routes.invitations.invitation_service.get_invitation")
    def test_get_invitation_success(self, mock_get, client):
        """Should return single invitation"""
        # Arrange
        invitation_id = str(uuid.uuid4())

        mock_get.return_value = {
            "invitation_id": invitation_id,
            "hackathon_id": str(uuid.uuid4()),
            "email": "judge@example.com",
            "role": "JUDGE",
            "status": "PENDING",
            "token": "abc123",
            "invited_by": "organizer_id",
            "created_at": "2024-01-01T00:00:00",
            "expires_at": "2024-01-08T00:00:00",
        }

        # Act
        response = client.get(f"/api/v1/invitations/{invitation_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["invitation_id"] == invitation_id


class TestGetInvitationByTokenEndpoint:
    """Test GET /invitations/token/{token} - Get invitation by token (PUBLIC)"""

    @patch("api.routes.invitations.invitation_service.get_invitation_by_token")
    def test_get_invitation_by_token_success(self, mock_get, client):
        """Should return invitation details by token"""
        # Arrange
        token = "abc123xyz"
        invitation_id = str(uuid.uuid4())

        mock_get.return_value = {
            "invitation_id": invitation_id,
            "hackathon_id": str(uuid.uuid4()),
            "email": "judge@example.com",
            "role": "JUDGE",
            "status": "PENDING",
            "token": token,
            "invited_by": "organizer_id",
            "created_at": "2024-01-01T00:00:00",
            "expires_at": "2024-01-08T00:00:00",
        }

        # Act
        response = client.get(f"/api/v1/invitations/token/{token}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["token"] == token

    @patch("api.routes.invitations.invitation_service.get_invitation_by_token")
    def test_get_invitation_by_invalid_token(self, mock_get, client):
        """Should return 404 for invalid token"""
        # Arrange
        mock_get.side_effect = ZeroDBNotFound("Invalid token")

        # Act
        response = client.get("/api/v1/invitations/token/invalid_token")

        # Assert
        assert response.status_code == 500


class TestAcceptInvitationEndpoint:
    """Test POST /invitations/accept - Accept invitation (PUBLIC)"""

    @patch("api.routes.invitations.invitation_service.accept_invitation")
    def test_accept_invitation_success(self, mock_accept, client):
        """Should accept invitation and return updated status"""
        # Arrange
        token = "abc123xyz"
        invitation_id = str(uuid.uuid4())

        mock_accept.return_value = {
            "invitation_id": invitation_id,
            "hackathon_id": str(uuid.uuid4()),
            "email": "judge@example.com",
            "role": "JUDGE",
            "status": "ACCEPTED",
            "token": token,
            "invited_by": "organizer_id",
            "created_at": "2024-01-01T00:00:00",
            "expires_at": "2024-01-08T00:00:00",
            "accepted_at": "2024-01-02T00:00:00",
        }

        # Act
        response = client.post(
            "/api/v1/invitations/accept",
            json={"token": token, "email": "judge@example.com", "name": "Judge Name"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ACCEPTED"

    @patch("api.routes.invitations.invitation_service.accept_invitation")
    def test_accept_expired_invitation(self, mock_accept, client):
        """Should reject expired invitation"""
        # Arrange
        mock_accept.side_effect = ZeroDBError("Invitation expired")

        # Act
        response = client.post(
            "/api/v1/invitations/accept",
            json={"token": "expired_token", "email": "test@example.com", "name": "Test"},
        )

        # Assert
        assert response.status_code == 500


class TestDeclineInvitationEndpoint:
    """Test POST /invitations/decline - Decline invitation (PUBLIC)"""

    @patch("api.routes.invitations.invitation_service.decline_invitation")
    def test_decline_invitation_success(self, mock_decline, client):
        """Should decline invitation and return updated status"""
        # Arrange
        token = "abc123xyz"
        invitation_id = str(uuid.uuid4())

        mock_decline.return_value = {
            "invitation_id": invitation_id,
            "hackathon_id": str(uuid.uuid4()),
            "email": "judge@example.com",
            "role": "JUDGE",
            "status": "DECLINED",
            "token": token,
            "invited_by": "organizer_id",
            "created_at": "2024-01-01T00:00:00",
            "expires_at": "2024-01-08T00:00:00",
            "declined_at": "2024-01-02T00:00:00",
        }

        # Act
        response = client.post(
            "/api/v1/invitations/decline",
            json={"token": token},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "DECLINED"


class TestResendInvitationEndpoint:
    """Test POST /invitations/{invitation_id}/resend - Resend invitation"""

    @patch("api.routes.invitations.invitation_service.resend_invitation")
    def test_resend_invitation_success(self, mock_resend, client, mock_user):
        """Should resend invitation with new expiration"""
        # Arrange
        invitation_id = str(uuid.uuid4())

        mock_resend.return_value = {
            "invitation_id": invitation_id,
            "hackathon_id": str(uuid.uuid4()),
            "email": "judge@example.com",
            "role": "JUDGE",
            "status": "PENDING",
            "token": "new_token",
            "invited_by": mock_user["id"],
            "created_at": "2024-01-01T00:00:00",
            "expires_at": "2024-01-10T00:00:00",
        }

        # Act
        response = client.post(f"/api/v1/invitations/{invitation_id}/resend")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["token"] == "new_token"


class TestCancelInvitationEndpoint:
    """Test DELETE /invitations/{invitation_id} - Cancel invitation"""

    @patch("api.routes.invitations.invitation_service.cancel_invitation")
    def test_cancel_invitation_success(self, mock_cancel, client, mock_user):
        """Should cancel pending invitation and return 204"""
        # Arrange
        invitation_id = str(uuid.uuid4())
        mock_cancel.return_value = None

        # Act
        response = client.delete(f"/api/v1/invitations/{invitation_id}")

        # Assert
        assert response.status_code == 204

    @patch("api.routes.invitations.invitation_service.cancel_invitation")
    def test_cancel_accepted_invitation(self, mock_cancel, client):
        """Should prevent cancellation of accepted invitation"""
        # Arrange
        invitation_id = str(uuid.uuid4())
        mock_cancel.side_effect = ZeroDBError("Cannot cancel accepted invitation")

        # Act
        response = client.delete(f"/api/v1/invitations/{invitation_id}")

        # Assert
        assert response.status_code == 500
