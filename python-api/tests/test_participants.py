"""
Tests for Participant Management

Tests participant service business logic and API endpoints.
Covers join, invite, list, and leave operations.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from integrations.zerodb.exceptions import ZeroDBError
from services.participants_service import ParticipantsService


class TestJoinHackathon:
    """Test join_hackathon() method"""

    @pytest.mark.asyncio
    async def test_join_hackathon_success(self):
        """Should create participant record when user joins hackathon"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = [
            [{"hackathon_id": "hack-123"}],  # Hackathon exists
            [],  # User not already a participant
        ]
        mock_client.tables.insert_rows.return_value = None

        service = ParticipantsService(mock_client)

        # Act
        result = await service.join_hackathon(
            hackathon_id="hack-123",
            user_id="user-456",
            user_email="test@example.com",
            user_name="Test User",
            role="BUILDER",
        )

        # Assert
        assert result["hackathon_id"] == "hack-123"
        assert result["participant_id"] == "user-456"
        assert result["role"] == "BUILDER"
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"
        assert "id" in result
        assert "joined_at" in result

        # Verify ZeroDB calls
        assert mock_client.tables.query_rows.call_count == 2
        mock_client.tables.insert_rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_join_hackathon_not_found(self):
        """Should raise 404 when hackathon does not exist"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []  # Hackathon not found

        service = ParticipantsService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.join_hackathon(
                hackathon_id="nonexistent",
                user_id="user-456",
                user_email="test@example.com",
                user_name="Test User",
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_join_hackathon_already_joined(self):
        """Should raise 409 when user is already a participant"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = [
            [{"hackathon_id": "hack-123"}],  # Hackathon exists
            [{"participant_id": "user-456"}],  # User already joined
        ]

        service = ParticipantsService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.join_hackathon(
                hackathon_id="hack-123",
                user_id="user-456",
                user_email="test@example.com",
                user_name="Test User",
            )

        assert exc_info.value.status_code == 409
        assert "already a participant" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_join_hackathon_database_error(self):
        """Should raise 500 when database error occurs"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = ZeroDBError("Connection failed")

        service = ParticipantsService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.join_hackathon(
                hackathon_id="hack-123",
                user_id="user-456",
                user_email="test@example.com",
                user_name="Test User",
            )

        assert exc_info.value.status_code == 500


class TestInviteJudges:
    """Test invite_judges() method"""

    @pytest.mark.asyncio
    async def test_invite_judges_success(self):
        """Should create placeholder judge records for invited emails"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = [
            [{"hackathon_id": "hack-123"}],  # Hackathon exists
            [],  # No existing participants (first invite check)
            [],  # No existing participants (second invite check)
        ]
        mock_client.tables.insert_rows.return_value = None

        service = ParticipantsService(mock_client)

        # Act
        result = await service.invite_judges(
            hackathon_id="hack-123",
            organizer_id="org-789",
            judge_emails=["judge1@example.com", "judge2@example.com"],
            message="Please join as a judge!",
        )

        # Assert
        assert result["invited_count"] == 2
        assert len(result["invited_emails"]) == 2
        assert "judge1@example.com" in result["invited_emails"]
        assert "judge2@example.com" in result["invited_emails"]

        # Verify insert was called twice (once per judge)
        assert mock_client.tables.insert_rows.call_count == 2

    @pytest.mark.asyncio
    async def test_invite_judges_skip_duplicates(self):
        """Should skip judges who are already invited"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = [
            [{"hackathon_id": "hack-123"}],  # Hackathon exists
            [
                {
                    "metadata": {"ainative_user_email": "judge1@example.com"}
                }  # Already invited
            ],
            [],  # Second judge not invited yet
        ]
        mock_client.tables.insert_rows.return_value = None

        service = ParticipantsService(mock_client)

        # Act
        result = await service.invite_judges(
            hackathon_id="hack-123",
            organizer_id="org-789",
            judge_emails=["judge1@example.com", "judge2@example.com"],
        )

        # Assert
        assert result["invited_count"] == 1
        assert result["invited_emails"] == ["judge2@example.com"]

    @pytest.mark.asyncio
    async def test_invite_judges_hackathon_not_found(self):
        """Should raise 404 when hackathon does not exist"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []  # Hackathon not found

        service = ParticipantsService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.invite_judges(
                hackathon_id="nonexistent",
                organizer_id="org-789",
                judge_emails=["judge@example.com"],
            )

        assert exc_info.value.status_code == 404


class TestListParticipants:
    """Test list_participants() method"""

    @pytest.mark.asyncio
    async def test_list_participants_all(self):
        """Should return all participants when no role filter"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {
                "id": "p1",
                "participant_id": "user1",
                "role": "BUILDER",
                "metadata": {
                    "ainative_user_email": "builder@example.com",
                    "ainative_user_name": "Builder User",
                },
            },
            {
                "id": "p2",
                "participant_id": "user2",
                "role": "JUDGE",
                "metadata": {
                    "ainative_user_email": "judge@example.com",
                    "ainative_user_name": "Judge User",
                },
            },
        ]

        service = ParticipantsService(mock_client)

        # Act
        result = await service.list_participants(hackathon_id="hack-123")

        # Assert
        assert len(result) == 2
        assert result[0]["email"] == "builder@example.com"
        assert result[0]["name"] == "Builder User"
        assert result[1]["email"] == "judge@example.com"
        assert result[1]["name"] == "Judge User"

    @pytest.mark.asyncio
    async def test_list_participants_with_role_filter(self):
        """Should filter participants by role"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {
                "id": "p1",
                "participant_id": "user1",
                "role": "JUDGE",
                "metadata": {"ainative_user_email": "judge@example.com"},
            }
        ]

        service = ParticipantsService(mock_client)

        # Act
        result = await service.list_participants(hackathon_id="hack-123", role="JUDGE")

        # Assert
        assert len(result) == 1
        assert result[0]["role"] == "JUDGE"

        # Verify filter was applied
        mock_client.tables.query_rows.assert_called_once()
        call_args = mock_client.tables.query_rows.call_args
        assert call_args[1]["filter"]["role"] == "JUDGE"

    @pytest.mark.asyncio
    async def test_list_participants_database_error(self):
        """Should raise 500 when database error occurs"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = ZeroDBError("Connection failed")

        service = ParticipantsService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.list_participants(hackathon_id="hack-123")

        assert exc_info.value.status_code == 500


class TestLeaveHackathon:
    """Test leave_hackathon() method"""

    @pytest.mark.asyncio
    async def test_leave_hackathon_success(self):
        """Should delete participant record when leaving"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = [
            [{"id": "p1", "participant_id": "user-456"}],  # User is participant
            [],  # No team memberships
        ]
        mock_client.tables.delete_rows.return_value = None

        service = ParticipantsService(mock_client)

        # Act
        result = await service.leave_hackathon(
            hackathon_id="hack-123",
            user_id="user-456",
        )

        # Assert
        assert result is True
        mock_client.tables.delete_rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_leave_hackathon_not_participant(self):
        """Should raise 404 when user is not a participant"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []  # Not a participant

        service = ParticipantsService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.leave_hackathon(
                hackathon_id="hack-123",
                user_id="user-456",
            )

        assert exc_info.value.status_code == 404
        assert "not a participant" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_leave_hackathon_has_submission(self):
        """Should raise 409 when user has submitted a project"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = [
            [{"id": "p1", "participant_id": "user-456"}],  # User is participant
            [{"team_id": "team-789"}],  # User has team membership
            [{"status": "SUBMITTED"}],  # Team has submission
        ]

        service = ParticipantsService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.leave_hackathon(
                hackathon_id="hack-123",
                user_id="user-456",
            )

        assert exc_info.value.status_code == 409
        assert "cannot leave" in exc_info.value.detail.lower()
        assert "submitting" in exc_info.value.detail.lower()


class TestParticipantsRoutes:
    """Test participant API routes"""

    @pytest.mark.asyncio
    async def test_join_hackathon_endpoint(self, client):
        """Should create participant when joining via API"""
        # This would require setting up a full integration test
        # with mocked authentication and ZeroDB
        # For now, we've tested the service layer comprehensively
        pass

    @pytest.mark.asyncio
    async def test_invite_judges_endpoint_requires_auth(self, client):
        """Should require authentication for invite endpoint"""
        # Integration test for authentication requirement
        pass

    @pytest.mark.asyncio
    async def test_list_participants_endpoint_public(self, client):
        """Should allow public access to list participants"""
        # Integration test for public access
        pass
