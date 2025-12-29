"""
Tests for Analytics Service and API Endpoints

Comprehensive test suite for analytics statistics calculation and data export
with authentication, authorization, validation, and error handling.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from main import app
from services import analytics_service

# Test client
client = TestClient(app)


class TestAnalyticsService:
    """Test analytics_service.py functions"""

    @pytest.mark.asyncio
    async def test_get_hackathon_stats_success(self):
        """Should calculate statistics correctly"""
        # Arrange
        mock_client = Mock()
        hackathon_id = str(uuid.uuid4())

        # Mock hackathon query
        mock_client.tables.query_rows = AsyncMock(
            side_effect=[
                # Hackathon exists
                [
                    {
                        "hackathon_id": hackathon_id,
                        "name": "Test Hack",
                        "is_deleted": False,
                    }
                ],
                # Participants (3 builders, 2 judges, 1 organizer)
                [
                    {"participant_id": "p1", "role": "builder"},
                    {"participant_id": "p2", "role": "builder"},
                    {"participant_id": "p3", "role": "builder"},
                    {"participant_id": "p4", "role": "judge"},
                    {"participant_id": "p5", "role": "judge"},
                    {"participant_id": "p6", "role": "organizer"},
                ],
                # Teams (2 teams)
                [
                    {"team_id": "t1", "name": "Team 1"},
                    {"team_id": "t2", "name": "Team 2"},
                ],
                # Submissions (2 SUBMITTED, 1 DRAFT)
                [
                    {
                        "submission_id": "s1",
                        "status": "SUBMITTED",
                        "track": "general",
                    },
                    {
                        "submission_id": "s2",
                        "status": "SUBMITTED",
                        "track": "general",
                    },
                    {"submission_id": "s3", "status": "DRAFT", "track": "ai"},
                ],
                # Scores for s1
                [{"score_id": "sc1", "submission_id": "s1", "total_score": 90.0}],
                # Scores for s2
                [{"score_id": "sc2", "submission_id": "s2", "total_score": 80.0}],
                # Scores for s3 (empty)
                [],
            ]
        )

        # Act
        result = await analytics_service.get_hackathon_stats(
            zerodb_client=mock_client,
            hackathon_id=hackathon_id,
        )

        # Assert
        assert result["hackathon_id"] == hackathon_id
        assert result["total_participants"] == 6
        assert result["participants_by_role"]["builder"] == 3
        assert result["participants_by_role"]["judge"] == 2
        assert result["participants_by_role"]["organizer"] == 1
        assert result["total_teams"] == 2
        assert result["total_submissions"] == 3
        assert result["submissions_by_status"]["SUBMITTED"] == 2
        assert result["submissions_by_status"]["DRAFT"] == 1
        assert "general" in result["average_scores"]
        assert result["average_scores"]["general"] == 85.0  # (90 + 80) / 2
        assert "calculated_at" in result

    @pytest.mark.asyncio
    async def test_get_hackathon_stats_hackathon_not_found(self):
        """Should raise 404 if hackathon doesn't exist"""
        # Arrange
        mock_client = Mock()
        hackathon_id = str(uuid.uuid4())

        # Mock empty hackathon query
        mock_client.tables.query_rows = AsyncMock(return_value=[])

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await analytics_service.get_hackathon_stats(
                zerodb_client=mock_client,
                hackathon_id=hackathon_id,
            )

        assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_hackathon_stats_no_data(self):
        """Should handle hackathon with no participants/teams/submissions"""
        # Arrange
        mock_client = Mock()
        hackathon_id = str(uuid.uuid4())

        # Mock queries - hackathon exists but no data
        mock_client.tables.query_rows = AsyncMock(
            side_effect=[
                # Hackathon exists
                [
                    {
                        "hackathon_id": hackathon_id,
                        "name": "Empty Hack",
                        "is_deleted": False,
                    }
                ],
                # No participants
                [],
                # No teams
                [],
                # No submissions
                [],
            ]
        )

        # Act
        result = await analytics_service.get_hackathon_stats(
            zerodb_client=mock_client,
            hackathon_id=hackathon_id,
        )

        # Assert
        assert result["total_participants"] == 0
        assert result["participants_by_role"] == {}
        assert result["total_teams"] == 0
        assert result["total_submissions"] == 0
        assert result["submissions_by_status"] == {}
        assert result["average_scores"] == {}

    @pytest.mark.asyncio
    async def test_export_hackathon_data_json_success(self):
        """Should export data in JSON format correctly"""
        # Arrange
        mock_client = Mock()
        hackathon_id = str(uuid.uuid4())

        hackathon = {
            "hackathon_id": hackathon_id,
            "name": "Test Hack",
            "is_deleted": False,
        }

        participants = [
            {"participant_id": "p1", "user_id": "u1", "role": "builder"},
            {"participant_id": "p2", "user_id": "u2", "role": "judge"},
        ]

        teams = [{"team_id": "t1", "name": "Team 1"}]

        submissions = [
            {
                "submission_id": "s1",
                "project_name": "Cool Project",
                "status": "SUBMITTED",
            }
        ]

        scores = [
            {"score_id": "sc1", "submission_id": "s1", "total_score": 95.0}
        ]

        # Mock queries
        mock_client.tables.query_rows = AsyncMock(
            side_effect=[
                [hackathon],  # Hackathon
                participants,  # Participants
                teams,  # Teams
                submissions,  # Submissions
                scores,  # Scores for s1
            ]
        )

        # Act
        result = await analytics_service.export_hackathon_data(
            zerodb_client=mock_client,
            hackathon_id=hackathon_id,
            format="json",
        )

        # Assert
        assert result["format"] == "json"
        assert "data" in result
        assert result["data"]["hackathon"] == hackathon
        assert result["data"]["participants"] == participants
        assert result["data"]["teams"] == teams
        assert result["data"]["submissions"] == submissions
        assert result["data"]["scores"] == scores
        assert "export_metadata" in result["data"]
        assert result["data"]["export_metadata"]["format"] == "json"
        assert result["data"]["export_metadata"]["record_counts"]["participants"] == 2
        assert result["data"]["export_metadata"]["record_counts"]["teams"] == 1
        assert result["data"]["export_metadata"]["record_counts"]["submissions"] == 1
        assert result["data"]["export_metadata"]["record_counts"]["scores"] == 1

    @pytest.mark.asyncio
    async def test_export_hackathon_data_csv_success(self):
        """Should export data in CSV format correctly"""
        # Arrange
        mock_client = Mock()
        hackathon_id = str(uuid.uuid4())

        hackathon = {
            "hackathon_id": hackathon_id,
            "name": "Test Hack",
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "is_deleted": False,
        }

        participants = [
            {
                "participant_id": "p1",
                "hackathon_id": hackathon_id,
                "user_id": "u1",
                "role": "builder",
                "status": "approved",
                "joined_at": "2025-01-01T00:00:00Z",
            }
        ]

        teams = [
            {
                "team_id": "t1",
                "hackathon_id": hackathon_id,
                "name": "Team 1",
                "created_at": "2025-01-01T00:00:00Z",
            }
        ]

        submissions = [
            {
                "submission_id": "s1",
                "hackathon_id": hackathon_id,
                "team_id": "t1",
                "project_name": "Cool Project",
                "status": "SUBMITTED",
                "created_at": "2025-01-01T00:00:00Z",
            }
        ]

        scores = [
            {
                "score_id": "sc1",
                "submission_id": "s1",
                "judge_participant_id": "p2",
                "total_score": 95.0,
                "submitted_at": "2025-01-01T00:00:00Z",
            }
        ]

        # Mock queries
        mock_client.tables.query_rows = AsyncMock(
            side_effect=[
                [hackathon],  # Hackathon
                participants,  # Participants
                teams,  # Teams
                submissions,  # Submissions
                scores,  # Scores
            ]
        )

        # Act
        result = await analytics_service.export_hackathon_data(
            zerodb_client=mock_client,
            hackathon_id=hackathon_id,
            format="csv",
        )

        # Assert
        assert result["format"] == "csv"
        assert "data" in result
        csv_data = result["data"]
        assert isinstance(csv_data, str)
        assert "record_type" in csv_data  # CSV header
        assert "hackathon" in csv_data  # Hackathon record
        assert "participant" in csv_data  # Participant record
        assert "team" in csv_data  # Team record
        assert "submission" in csv_data  # Submission record
        assert "score" in csv_data  # Score record
        assert "Test Hack" in csv_data  # Hackathon name
        assert "builder" in csv_data  # Role
        assert "Team 1" in csv_data  # Team name
        assert "Cool Project" in csv_data  # Project name

    @pytest.mark.asyncio
    async def test_export_hackathon_data_invalid_format(self):
        """Should raise 400 for invalid format"""
        # Arrange
        mock_client = Mock()
        hackathon_id = str(uuid.uuid4())

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await analytics_service.export_hackathon_data(
                zerodb_client=mock_client,
                hackathon_id=hackathon_id,
                format="xml",  # Invalid format
            )

        assert "400" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_export_hackathon_data_hackathon_not_found(self):
        """Should raise 404 if hackathon doesn't exist"""
        # Arrange
        mock_client = Mock()
        hackathon_id = str(uuid.uuid4())

        # Mock empty hackathon query
        mock_client.tables.query_rows = AsyncMock(return_value=[])

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await analytics_service.export_hackathon_data(
                zerodb_client=mock_client,
                hackathon_id=hackathon_id,
                format="json",
            )

        assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()


class TestAnalyticsEndpoints:
    """Test /api/v1/hackathons/{id}/stats and /api/v1/hackathons/{id}/export endpoints"""

    @patch("api.routes.analytics.get_current_user")
    @patch("api.routes.analytics.get_zerodb_client")
    @patch("services.authorization.check_organizer")
    @patch("services.analytics_service.get_hackathon_stats")
    def test_get_stats_success(
        self, mock_get_stats, mock_check_org, mock_zerodb, mock_auth
    ):
        """Should return statistics for authorized organizer"""
        # Arrange
        user_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_auth.return_value = {"id": user_id}
        mock_check_org.return_value = True

        mock_stats = {
            "hackathon_id": hackathon_id,
            "total_participants": 42,
            "participants_by_role": {
                "organizer": 2,
                "judge": 5,
                "builder": 35,
            },
            "total_teams": 8,
            "total_submissions": 8,
            "submissions_by_status": {
                "DRAFT": 2,
                "SUBMITTED": 3,
                "SCORED": 3,
            },
            "average_scores": {"general": 85.5},
            "calculated_at": "2025-12-28T10:30:00Z",
        }
        mock_get_stats.return_value = mock_stats

        # Act
        response = client.get(
            f"/api/v1/hackathons/{hackathon_id}/stats",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["hackathon_id"] == hackathon_id
        assert data["total_participants"] == 42
        assert data["participants_by_role"]["builder"] == 35
        assert data["total_teams"] == 8
        assert data["total_submissions"] == 8
        assert data["average_scores"]["general"] == 85.5

        mock_check_org.assert_called_once()
        mock_get_stats.assert_called_once()

    @patch("api.routes.analytics.get_current_user")
    def test_get_stats_unauthorized(self, mock_auth):
        """Should return 401 without authentication"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        # Act
        response = client.get(f"/api/v1/hackathons/{hackathon_id}/stats")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("api.routes.analytics.get_current_user")
    @patch("api.routes.analytics.get_zerodb_client")
    @patch("services.authorization.check_organizer")
    def test_get_stats_forbidden_not_organizer(
        self, mock_check_org, mock_zerodb, mock_auth
    ):
        """Should return 403 if user is not an organizer"""
        # Arrange
        user_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_auth.return_value = {"id": user_id}

        # Mock authorization failure
        from fastapi import HTTPException

        mock_check_org.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required role: organizer",
        )

        # Act
        response = client.get(
            f"/api/v1/hackathons/{hackathon_id}/stats",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "organizer" in response.json()["detail"].lower()

    @patch("api.routes.analytics.get_current_user")
    @patch("api.routes.analytics.get_zerodb_client")
    @patch("services.authorization.check_organizer")
    @patch("services.analytics_service.get_hackathon_stats")
    def test_get_stats_hackathon_not_found(
        self, mock_get_stats, mock_check_org, mock_zerodb, mock_auth
    ):
        """Should return 404 if hackathon doesn't exist"""
        # Arrange
        user_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_auth.return_value = {"id": user_id}
        mock_check_org.return_value = True

        from fastapi import HTTPException

        mock_get_stats.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hackathon {hackathon_id} not found",
        )

        # Act
        response = client.get(
            f"/api/v1/hackathons/{hackathon_id}/stats",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    @patch("api.routes.analytics.get_current_user")
    @patch("api.routes.analytics.get_zerodb_client")
    @patch("services.authorization.check_organizer")
    @patch("services.analytics_service.export_hackathon_data")
    def test_export_json_success(
        self, mock_export, mock_check_org, mock_zerodb, mock_auth
    ):
        """Should export data in JSON format"""
        # Arrange
        user_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_auth.return_value = {"id": user_id}
        mock_check_org.return_value = True

        mock_export_data = {
            "format": "json",
            "data": {
                "hackathon": {"hackathon_id": hackathon_id, "name": "Test Hack"},
                "participants": [{"participant_id": "p1"}],
                "teams": [{"team_id": "t1"}],
                "submissions": [{"submission_id": "s1"}],
                "scores": [{"score_id": "sc1"}],
                "export_metadata": {
                    "exported_at": "2025-12-28T10:30:00Z",
                    "format": "json",
                    "record_counts": {
                        "participants": 1,
                        "teams": 1,
                        "submissions": 1,
                        "scores": 1,
                    },
                },
            },
        }
        mock_export.return_value = mock_export_data

        # Act
        response = client.get(
            f"/api/v1/hackathons/{hackathon_id}/export?format=json",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["format"] == "json"
        assert "data" in data
        assert data["data"]["hackathon"]["hackathon_id"] == hackathon_id
        assert len(data["data"]["participants"]) == 1

        mock_check_org.assert_called_once()
        mock_export.assert_called_once_with(
            zerodb_client=mock_zerodb.return_value,
            hackathon_id=hackathon_id,
            format="json",
        )

    @patch("api.routes.analytics.get_current_user")
    @patch("api.routes.analytics.get_zerodb_client")
    @patch("services.authorization.check_organizer")
    @patch("services.analytics_service.export_hackathon_data")
    def test_export_csv_success(
        self, mock_export, mock_check_org, mock_zerodb, mock_auth
    ):
        """Should export data in CSV format"""
        # Arrange
        user_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_auth.return_value = {"id": user_id}
        mock_check_org.return_value = True

        csv_content = (
            "record_type,record_id,hackathon_id\n"
            "hackathon,hack-123,hack-123\n"
            "participant,p1,hack-123\n"
        )

        mock_export_data = {
            "format": "csv",
            "data": csv_content,
        }
        mock_export.return_value = mock_export_data

        # Act
        response = client.get(
            f"/api/v1/hackathons/{hackathon_id}/export?format=csv",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert hackathon_id in response.headers["content-disposition"]
        assert "record_type" in response.text
        assert "hackathon" in response.text

        mock_check_org.assert_called_once()
        mock_export.assert_called_once_with(
            zerodb_client=mock_zerodb.return_value,
            hackathon_id=hackathon_id,
            format="csv",
        )

    @patch("api.routes.analytics.get_current_user")
    def test_export_unauthorized(self, mock_auth):
        """Should return 401 without authentication"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        # Act
        response = client.get(f"/api/v1/hackathons/{hackathon_id}/export")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("api.routes.analytics.get_current_user")
    @patch("api.routes.analytics.get_zerodb_client")
    @patch("services.authorization.check_organizer")
    def test_export_forbidden_not_organizer(
        self, mock_check_org, mock_zerodb, mock_auth
    ):
        """Should return 403 if user is not an organizer"""
        # Arrange
        user_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_auth.return_value = {"id": user_id}

        from fastapi import HTTPException

        mock_check_org.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required role: organizer",
        )

        # Act
        response = client.get(
            f"/api/v1/hackathons/{hackathon_id}/export?format=json",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "organizer" in response.json()["detail"].lower()

    @patch("api.routes.analytics.get_current_user")
    @patch("api.routes.analytics.get_zerodb_client")
    @patch("services.authorization.check_organizer")
    @patch("services.analytics_service.export_hackathon_data")
    def test_export_hackathon_not_found(
        self, mock_export, mock_check_org, mock_zerodb, mock_auth
    ):
        """Should return 404 if hackathon doesn't exist"""
        # Arrange
        user_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_auth.return_value = {"id": user_id}
        mock_check_org.return_value = True

        from fastapi import HTTPException

        mock_export.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hackathon {hackathon_id} not found",
        )

        # Act
        response = client.get(
            f"/api/v1/hackathons/{hackathon_id}/export?format=json",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    @patch("api.routes.analytics.get_current_user")
    @patch("api.routes.analytics.get_zerodb_client")
    @patch("services.authorization.check_organizer")
    @patch("services.analytics_service.export_hackathon_data")
    def test_export_default_format_is_json(
        self, mock_export, mock_check_org, mock_zerodb, mock_auth
    ):
        """Should default to JSON format when no format parameter provided"""
        # Arrange
        user_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_auth.return_value = {"id": user_id}
        mock_check_org.return_value = True

        mock_export_data = {
            "format": "json",
            "data": {
                "hackathon": {"hackathon_id": hackathon_id},
                "participants": [],
                "teams": [],
                "submissions": [],
                "scores": [],
                "export_metadata": {
                    "exported_at": "2025-12-28T10:30:00Z",
                    "format": "json",
                    "record_counts": {
                        "participants": 0,
                        "teams": 0,
                        "submissions": 0,
                        "scores": 0,
                    },
                },
            },
        }
        mock_export.return_value = mock_export_data

        # Act
        response = client.get(
            f"/api/v1/hackathons/{hackathon_id}/export",  # No format parameter
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["format"] == "json"

        # Verify service was called with default "json" format
        mock_export.assert_called_once_with(
            zerodb_client=mock_zerodb.return_value,
            hackathon_id=hackathon_id,
            format="json",  # Default value
        )
