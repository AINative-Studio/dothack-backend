"""
Tests for Judging API Endpoints

Tests all judging routes with comprehensive coverage:
- POST /judging/scores - Score submission
- GET /judging/hackathons/{id}/results - Hackathon results
- GET /judging/assignments - Judge assignments

Following TDD methodology with mocked dependencies.
"""

import uuid
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from api.routes.judging import get_zerodb_client, router
from api.schemas.judging import ScoreSubmitRequest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBTimeoutError


# Test Client Setup
@pytest.fixture
def test_app():
    """Create test FastAPI app with judging routes"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def test_client(test_app):
    """Create test client"""
    return TestClient(test_app)


@pytest.fixture
def mock_zerodb_client():
    """Create mock ZeroDB client"""
    mock_client = AsyncMock()
    mock_client.tables = AsyncMock()
    mock_client.tables.query_rows = AsyncMock()
    mock_client.tables.insert_rows = AsyncMock()
    return mock_client


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    return {
        "id": "user-123-456",
        "email": "judge@example.com",
        "name": "Test Judge",
        "email_verified": True,
    }


@pytest.fixture
def sample_score_request():
    """Sample score submission request"""
    return {
        "judge_id": "user-123-456",
        "criteria": "innovation",
        "score": 85.0,
        "comment": "Excellent innovative approach",
    }


# Test POST /judging/scores
class TestSubmitScoreEndpoint:
    """Test score submission endpoint"""

    @pytest.mark.asyncio
    async def test_submit_score_success(
        self, test_client, mock_zerodb_client, mock_user, sample_score_request
    ):
        """Should successfully submit a score"""
        # Arrange
        submission_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        rubric_id = str(uuid.uuid4())

        # Mock successful submission
        with patch("api.routes.judging.get_current_user", return_value=mock_user):
            with patch("api.routes.judging.get_zerodb_client", return_value=mock_zerodb_client):
                with patch("api.routes.judging.submit_score") as mock_submit:
                    mock_submit.return_value = {
                        "success": True,
                        "score_id": str(uuid.uuid4()),
                        "row_ids": ["score-123"],
                    }

                    # Act
                    response = test_client.post(
                        f"/judging/scores?submission_id={submission_id}&hackathon_id={hackathon_id}&rubric_id={rubric_id}",
                        json=sample_score_request,
                    )

                    # Assert
                    assert response.status_code == status.HTTP_201_CREATED
                    data = response.json()
                    assert data["success"] is True
                    assert "score_id" in data
                    mock_submit.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_score_judge_id_mismatch(
        self, test_client, mock_zerodb_client, mock_user, sample_score_request
    ):
        """Should reject when judge_id doesn't match authenticated user"""
        # Arrange
        submission_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        rubric_id = str(uuid.uuid4())

        # Different judge_id in request
        different_request = sample_score_request.copy()
        different_request["judge_id"] = "different-user-789"

        with patch("api.routes.judging.get_current_user", return_value=mock_user):
            with patch("api.routes.judging.get_zerodb_client", return_value=mock_zerodb_client):
                # Act
                response = test_client.post(
                    f"/judging/scores?submission_id={submission_id}&hackathon_id={hackathon_id}&rubric_id={rubric_id}",
                    json=different_request,
                )

                # Assert
                assert response.status_code == status.HTTP_403_FORBIDDEN
                assert "must match authenticated user" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_submit_score_invalid_score_value(
        self, test_client, mock_zerodb_client, mock_user, sample_score_request
    ):
        """Should reject invalid score values"""
        # Arrange
        submission_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        rubric_id = str(uuid.uuid4())

        # Invalid score (> 100)
        invalid_request = sample_score_request.copy()
        invalid_request["score"] = 150.0

        with patch("api.routes.judging.get_current_user", return_value=mock_user):
            with patch("api.routes.judging.get_zerodb_client", return_value=mock_zerodb_client):
                # Act
                response = test_client.post(
                    f"/judging/scores?submission_id={submission_id}&hackathon_id={hackathon_id}&rubric_id={rubric_id}",
                    json=invalid_request,
                )

                # Assert
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_submit_score_not_judge(
        self, test_client, mock_zerodb_client, mock_user, sample_score_request
    ):
        """Should reject when user is not a judge"""
        # Arrange
        submission_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        rubric_id = str(uuid.uuid4())

        with patch("api.routes.judging.get_current_user", return_value=mock_user):
            with patch("api.routes.judging.get_zerodb_client", return_value=mock_zerodb_client):
                with patch("api.routes.judging.submit_score") as mock_submit:
                    # Mock authorization failure
                    mock_submit.side_effect = HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="User is not a judge for this hackathon",
                    )

                    # Act
                    response = test_client.post(
                        f"/judging/scores?submission_id={submission_id}&hackathon_id={hackathon_id}&rubric_id={rubric_id}",
                        json=sample_score_request,
                    )

                    # Assert
                    assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_submit_score_duplicate(
        self, test_client, mock_zerodb_client, mock_user, sample_score_request
    ):
        """Should reject duplicate scores"""
        # Arrange
        submission_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        rubric_id = str(uuid.uuid4())

        with patch("api.routes.judging.get_current_user", return_value=mock_user):
            with patch("api.routes.judging.get_zerodb_client", return_value=mock_zerodb_client):
                with patch("api.routes.judging.submit_score") as mock_submit:
                    # Mock duplicate error
                    mock_submit.side_effect = HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Judge has already submitted a score for this submission",
                    )

                    # Act
                    response = test_client.post(
                        f"/judging/scores?submission_id={submission_id}&hackathon_id={hackathon_id}&rubric_id={rubric_id}",
                        json=sample_score_request,
                    )

                    # Assert
                    assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_submit_score_database_timeout(
        self, test_client, mock_zerodb_client, mock_user, sample_score_request
    ):
        """Should handle database timeout"""
        # Arrange
        submission_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        rubric_id = str(uuid.uuid4())

        with patch("api.routes.judging.get_current_user", return_value=mock_user):
            with patch("api.routes.judging.get_zerodb_client", return_value=mock_zerodb_client):
                with patch("api.routes.judging.submit_score") as mock_submit:
                    # Mock timeout error
                    mock_submit.side_effect = HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail="Score submission timed out. Please try again.",
                    )

                    # Act
                    response = test_client.post(
                        f"/judging/scores?submission_id={submission_id}&hackathon_id={hackathon_id}&rubric_id={rubric_id}",
                        json=sample_score_request,
                    )

                    # Assert
                    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT


# Test GET /judging/hackathons/{id}/results
class TestGetHackathonResults:
    """Test hackathon results endpoint"""

    @pytest.mark.asyncio
    async def test_get_results_success(self, test_client, mock_zerodb_client, mock_user):
        """Should successfully retrieve hackathon results"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        mock_leaderboard = [
            {
                "rank": 1,
                "submission_id": str(uuid.uuid4()),
                "project_id": str(uuid.uuid4()),
                "project_name": "AI Assistant",
                "team_id": str(uuid.uuid4()),
                "team_name": "Team Alpha",
                "average_score": 85.5,
                "score_count": 5,
            }
        ]

        mock_hackathon = {"hackathon_id": hackathon_id, "name": "Test Hackathon 2024"}

        with patch("api.routes.judging.get_current_user", return_value=mock_user):
            with patch("api.routes.judging.get_zerodb_client", return_value=mock_zerodb_client):
                with patch("api.routes.judging.get_leaderboard", return_value=mock_leaderboard):
                    mock_zerodb_client.tables.query_rows.return_value = [mock_hackathon]

                    # Act
                    response = test_client.get(f"/judging/hackathons/{hackathon_id}/results")

                    # Assert
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert data["hackathon_name"] == "Test Hackathon 2024"
                    assert len(data["entries"]) == 1
                    assert data["entries"][0]["rank"] == 1
                    assert data["total_entries"] == 1

    @pytest.mark.asyncio
    async def test_get_results_with_track_filter(
        self, test_client, mock_zerodb_client, mock_user
    ):
        """Should filter results by track"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        track_id = str(uuid.uuid4())

        mock_leaderboard = []
        mock_hackathon = {"hackathon_id": hackathon_id, "name": "Test Hackathon"}

        with patch("api.routes.judging.get_current_user", return_value=mock_user):
            with patch("api.routes.judging.get_zerodb_client", return_value=mock_zerodb_client):
                with patch("api.routes.judging.get_leaderboard", return_value=mock_leaderboard) as mock_get:
                    mock_zerodb_client.tables.query_rows.return_value = [mock_hackathon]

                    # Act
                    response = test_client.get(
                        f"/judging/hackathons/{hackathon_id}/results?track_id={track_id}"
                    )

                    # Assert
                    assert response.status_code == status.HTTP_200_OK
                    # Verify track_id was passed to service
                    mock_get.assert_called_once()
                    call_kwargs = mock_get.call_args.kwargs
                    assert call_kwargs["track_id"] == track_id

    @pytest.mark.asyncio
    async def test_get_results_with_top_n_limit(
        self, test_client, mock_zerodb_client, mock_user
    ):
        """Should limit results to top N"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        top_n = 10

        mock_leaderboard = []
        mock_hackathon = {"hackathon_id": hackathon_id, "name": "Test Hackathon"}

        with patch("api.routes.judging.get_current_user", return_value=mock_user):
            with patch("api.routes.judging.get_zerodb_client", return_value=mock_zerodb_client):
                with patch("api.routes.judging.get_leaderboard", return_value=mock_leaderboard) as mock_get:
                    mock_zerodb_client.tables.query_rows.return_value = [mock_hackathon]

                    # Act
                    response = test_client.get(
                        f"/judging/hackathons/{hackathon_id}/results?top_n={top_n}"
                    )

                    # Assert
                    assert response.status_code == status.HTTP_200_OK
                    # Verify top_n was passed to service
                    call_kwargs = mock_get.call_args.kwargs
                    assert call_kwargs["top_n"] == top_n

    @pytest.mark.asyncio
    async def test_get_results_hackathon_not_found(
        self, test_client, mock_zerodb_client, mock_user
    ):
        """Should return 404 when hackathon not found"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        with patch("api.routes.judging.get_current_user", return_value=mock_user):
            with patch("api.routes.judging.get_zerodb_client", return_value=mock_zerodb_client):
                with patch("api.routes.judging.get_leaderboard", return_value=[]):
                    # Mock hackathon not found
                    mock_zerodb_client.tables.query_rows.return_value = []

                    # Act
                    response = test_client.get(f"/judging/hackathons/{hackathon_id}/results")

                    # Assert
                    assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_results_database_timeout(
        self, test_client, mock_zerodb_client, mock_user
    ):
        """Should handle database timeout"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        with patch("api.routes.judging.get_current_user", return_value=mock_user):
            with patch("api.routes.judging.get_zerodb_client", return_value=mock_zerodb_client):
                with patch("api.routes.judging.get_leaderboard") as mock_get:
                    # Mock timeout
                    mock_get.side_effect = ZeroDBTimeoutError("Connection timeout")

                    # Act
                    response = test_client.get(f"/judging/hackathons/{hackathon_id}/results")

                    # Assert
                    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT


# Test GET /judging/assignments
class TestGetJudgeAssignments:
    """Test judge assignments endpoint"""

    @pytest.mark.asyncio
    async def test_get_assignments_success(self, test_client, mock_zerodb_client, mock_user):
        """Should successfully retrieve judge assignments"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        judge_id = mock_user["id"]

        # Mock participant (is judge)
        mock_participant = {
            "user_id": judge_id,
            "hackathon_id": hackathon_id,
            "role": "judge",
        }

        # Mock projects
        mock_projects = [
            {
                "project_id": str(uuid.uuid4()),
                "hackathon_id": hackathon_id,
                "name": "AI Project",
                "team_id": str(uuid.uuid4()),
            }
        ]

        # Mock submissions
        mock_submissions = [
            {
                "submission_id": str(uuid.uuid4()),
                "project_id": mock_projects[0]["project_id"],
                "url": "https://example.com/project",
                "created_at": "2024-01-01T00:00:00",
            }
        ]

        # Mock team
        mock_team = {"team_id": mock_projects[0]["team_id"], "name": "Team Alpha"}

        with patch("api.routes.judging.get_current_user", return_value=mock_user):
            with patch("api.routes.judging.get_zerodb_client", return_value=mock_zerodb_client):
                # Set up query_rows to return different results based on table
                async def mock_query_rows(table_name, **kwargs):
                    if table_name == "hackathon_participants":
                        return [mock_participant]
                    elif table_name == "projects":
                        return mock_projects
                    elif table_name == "submissions":
                        return mock_submissions
                    elif table_name == "scores":
                        return []  # No existing scores
                    elif table_name == "teams":
                        return [mock_team]
                    return []

                mock_zerodb_client.tables.query_rows.side_effect = mock_query_rows

                # Act
                response = test_client.get(f"/judging/assignments?hackathon_id={hackathon_id}")

                # Assert
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert isinstance(data, list)
                assert len(data) == 1
                assert data[0]["project_name"] == "AI Project"
                assert data[0]["already_scored"] is False

    @pytest.mark.asyncio
    async def test_get_assignments_not_participant(
        self, test_client, mock_zerodb_client, mock_user
    ):
        """Should reject when user is not a participant"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        with patch("api.routes.judging.get_current_user", return_value=mock_user):
            with patch("api.routes.judging.get_zerodb_client", return_value=mock_zerodb_client):
                # Mock no participant record
                mock_zerodb_client.tables.query_rows.return_value = []

                # Act
                response = test_client.get(f"/judging/assignments?hackathon_id={hackathon_id}")

                # Assert
                assert response.status_code == status.HTTP_403_FORBIDDEN
                assert "not a participant" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_assignments_not_judge(self, test_client, mock_zerodb_client, mock_user):
        """Should reject when user is not a judge"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        judge_id = mock_user["id"]

        # Mock participant but not judge
        mock_participant = {
            "user_id": judge_id,
            "hackathon_id": hackathon_id,
            "role": "builder",  # Not a judge
        }

        with patch("api.routes.judging.get_current_user", return_value=mock_user):
            with patch("api.routes.judging.get_zerodb_client", return_value=mock_zerodb_client):
                mock_zerodb_client.tables.query_rows.return_value = [mock_participant]

                # Act
                response = test_client.get(f"/judging/assignments?hackathon_id={hackathon_id}")

                # Assert
                assert response.status_code == status.HTTP_403_FORBIDDEN
                assert "not a judge" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_assignments_already_scored(
        self, test_client, mock_zerodb_client, mock_user
    ):
        """Should mark assignments as already scored"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        judge_id = mock_user["id"]

        mock_participant = {
            "user_id": judge_id,
            "hackathon_id": hackathon_id,
            "role": "judge",
        }

        mock_projects = [
            {
                "project_id": str(uuid.uuid4()),
                "hackathon_id": hackathon_id,
                "name": "AI Project",
                "team_id": None,
            }
        ]

        mock_submissions = [
            {
                "submission_id": str(uuid.uuid4()),
                "project_id": mock_projects[0]["project_id"],
                "url": "https://example.com/project",
                "created_at": "2024-01-01T00:00:00",
            }
        ]

        # Mock existing score
        mock_score = {
            "score_id": str(uuid.uuid4()),
            "submission_id": mock_submissions[0]["submission_id"],
            "judge_participant_id": judge_id,
        }

        with patch("api.routes.judging.get_current_user", return_value=mock_user):
            with patch("api.routes.judging.get_zerodb_client", return_value=mock_zerodb_client):

                async def mock_query_rows(table_name, **kwargs):
                    if table_name == "hackathon_participants":
                        return [mock_participant]
                    elif table_name == "projects":
                        return mock_projects
                    elif table_name == "submissions":
                        return mock_submissions
                    elif table_name == "scores":
                        return [mock_score]  # Has existing score
                    return []

                mock_zerodb_client.tables.query_rows.side_effect = mock_query_rows

                # Act
                response = test_client.get(f"/judging/assignments?hackathon_id={hackathon_id}")

                # Assert
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert len(data) == 1
                assert data[0]["already_scored"] is True

    @pytest.mark.asyncio
    async def test_get_assignments_database_error(
        self, test_client, mock_zerodb_client, mock_user
    ):
        """Should handle database errors"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        with patch("api.routes.judging.get_current_user", return_value=mock_user):
            with patch("api.routes.judging.get_zerodb_client", return_value=mock_zerodb_client):
                # Mock database error
                mock_zerodb_client.tables.query_rows.side_effect = ZeroDBError(
                    "Database connection failed"
                )

                # Act
                response = test_client.get(f"/judging/assignments?hackathon_id={hackathon_id}")

                # Assert
                assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# Test ZeroDB Client Dependency
class TestGetZeroDBClient:
    """Test ZeroDB client dependency"""

    def test_get_zerodb_client_success(self):
        """Should create ZeroDB client with settings"""
        # Arrange
        with patch("api.routes.judging.settings") as mock_settings:
            mock_settings.ZERODB_API_KEY = "test-key"
            mock_settings.ZERODB_PROJECT_ID = "test-project"
            mock_settings.ZERODB_BASE_URL = "https://api.example.com"

            with patch("api.routes.judging.ZeroDBClient") as MockClient:
                # Act
                client = get_zerodb_client()

                # Assert
                MockClient.assert_called_once_with(
                    api_key="test-key",
                    project_id="test-project",
                    base_url="https://api.example.com",
                )

    def test_get_zerodb_client_missing_credentials(self):
        """Should raise 500 when credentials missing"""
        # Arrange
        with patch("api.routes.judging.settings") as mock_settings:
            mock_settings.ZERODB_API_KEY = None
            mock_settings.ZERODB_PROJECT_ID = None

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                get_zerodb_client()

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Database configuration error" in exc_info.value.detail
