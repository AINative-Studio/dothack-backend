"""
Comprehensive API Integration Tests

Tests complete end-to-end flows across all API endpoints:
- Hackathon CRUD lifecycle
- Team creation and member management
- Submission creation and file upload
- Judging and scoring workflows
- Participant join/leave flows
- Authentication and authorization
- Error handling and validation

Coverage target: >= 80%

NOTE: The `client` fixture from conftest.py already has get_current_user
overridden via app.dependency_overrides. Tests that need a specific user
(organizer, judge, builder) should set up the override in the test or
use the appropriate fixture. The `@patch("api.routes.X.get_current_user")`
pattern does NOT work with FastAPI's Depends() system.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
from api.dependencies import get_current_user
from fastapi import status
from fastapi.testclient import TestClient
from main import app


def _set_auth_user(user: Dict[str, Any]):
    """Helper to set the authenticated user via dependency override."""
    async def override():
        return user
    app.dependency_overrides[get_current_user] = override


# ============================================================================
# Hackathon Endpoint Tests - Complete CRUD Flow
# ============================================================================


class TestHackathonEndpoints:
    """Test hackathon CRUD operations end-to-end."""

    @patch("services.hackathon_service.create_hackathon")
    def test_hackathon_crud_flow_complete(
        self,
        mock_create_service,
        client: TestClient,
        test_organizer: Dict[str, Any],
        hackathon_factory,
    ):
        """
        Test complete hackathon lifecycle: create -> read -> update -> delete.
        """
        # Setup auth for organizer
        _set_auth_user(test_organizer)

        organizer_id = test_organizer["id"]
        hackathon_data = hackathon_factory(organizer_id=organizer_id)
        hackathon_id = str(uuid.uuid4())

        # Step 1: CREATE hackathon
        mock_create_service.return_value = {
            "hackathon_id": hackathon_id,
            **hackathon_data,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        create_response = client.post(
            "/api/v1/hackathons",
            json=hackathon_data,
            headers={"Authorization": "Bearer test-token"},
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        created_data = create_response.json()
        assert created_data["hackathon_id"] == hackathon_id
        assert created_data["name"] == hackathon_data["name"]
        assert created_data["status"] == "draft"

        # Step 2: READ hackathon
        with patch("services.hackathon_service.get_hackathon") as mock_get:
            mock_get.return_value = created_data

            read_response = client.get(
                f"/api/v1/hackathons/{hackathon_id}",
                headers={"Authorization": "Bearer test-token"},
            )

            assert read_response.status_code == status.HTTP_200_OK
            read_data = read_response.json()
            assert read_data["hackathon_id"] == hackathon_id
            assert read_data["name"] == hackathon_data["name"]

        # Step 3: UPDATE hackathon
        with patch("services.hackathon_service.update_hackathon") as mock_update:
            updated_data = {**created_data, "status": "upcoming", "max_participants": 150}
            mock_update.return_value = updated_data

            update_response = client.patch(
                f"/api/v1/hackathons/{hackathon_id}",
                json={"status": "upcoming", "max_participants": 150},
                headers={"Authorization": "Bearer test-token"},
            )

            assert update_response.status_code == status.HTTP_200_OK
            update_result = update_response.json()
            assert update_result["status"] == "upcoming"
            assert update_result["max_participants"] == 150

        # Step 4: DELETE hackathon (soft delete)
        with patch("services.hackathon_service.delete_hackathon") as mock_delete:
            mock_delete.return_value = {
                "success": True,
                "hackathon_id": hackathon_id,
                "message": "Hackathon successfully deleted",
            }

            delete_response = client.delete(
                f"/api/v1/hackathons/{hackathon_id}",
                headers={"Authorization": "Bearer test-token"},
            )

            assert delete_response.status_code == status.HTTP_200_OK
            delete_data = delete_response.json()
            assert delete_data["success"] is True
            assert delete_data["hackathon_id"] == hackathon_id

    @patch("services.hackathon_service.list_hackathons")
    def test_list_hackathons_with_pagination(
        self, mock_list_service, client: TestClient, test_user: Dict[str, Any]
    ):
        """
        Test hackathon listing with pagination and filtering.
        """
        _set_auth_user(test_user)

        # Mock service response
        mock_hackathons = [
            {
                "hackathon_id": str(uuid.uuid4()),
                "name": f"Hackathon {i}",
                "status": "active" if i % 2 == 0 else "upcoming",
                "start_date": datetime.utcnow().isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            }
            for i in range(5)
        ]

        mock_list_service.return_value = {
            "hackathons": mock_hackathons,
            "total": 25,
            "skip": 0,
            "limit": 100,
        }

        # Test default pagination
        response = client.get("/api/v1/hackathons", headers={"Authorization": "Bearer test-token"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "hackathons" in data
        assert "total" in data
        assert data["total"] == 25
        assert len(data["hackathons"]) == 5

        # Test custom pagination
        mock_list_service.return_value = {
            "hackathons": mock_hackathons[:2],
            "total": 25,
            "skip": 10,
            "limit": 2,
        }

        response = client.get(
            "/api/v1/hackathons?skip=10&limit=2",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["skip"] == 10
        assert data["limit"] == 2
        assert len(data["hackathons"]) == 2

    def test_create_hackathon_validation_errors(
        self, client: TestClient, test_organizer: Dict[str, Any], hackathon_factory
    ):
        """
        Test hackathon creation validation errors.
        """
        _set_auth_user(test_organizer)

        # Test: Missing required field (name)
        invalid_data = hackathon_factory(organizer_id=test_organizer["id"])
        del invalid_data["name"]

        response = client.post(
            "/api/v1/hackathons",
            json=invalid_data,
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test: End date before start date
        invalid_data = hackathon_factory(
            organizer_id=test_organizer["id"],
            start_date=(datetime.utcnow() + timedelta(days=30)).isoformat(),
            end_date=(datetime.utcnow() + timedelta(days=25)).isoformat(),
        )

        response = client.post(
            "/api/v1/hackathons",
            json=invalid_data,
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test: Name too short
        invalid_data = hackathon_factory(organizer_id=test_organizer["id"], name="AI")

        response = client.post(
            "/api/v1/hackathons",
            json=invalid_data,
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_hackathon_authorization_errors(
        self, client: TestClient, test_user: Dict[str, Any], hackathon_factory
    ):
        """
        Test hackathon authorization errors.
        """
        _set_auth_user(test_user)
        different_organizer_id = str(uuid.uuid4())

        # Test: Create with different organizer_id
        hackathon_data = hackathon_factory(organizer_id=different_organizer_id)

        response = client.post(
            "/api/v1/hackathons",
            json=hackathon_data,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "organizer_id must match" in response.json()["detail"]


# ============================================================================
# Team Endpoint Tests - CRUD and Member Management
# ============================================================================


class TestTeamEndpoints:
    """Test team CRUD operations and member management."""

    @patch("services.team_service.create_team")
    @patch("services.team_service.add_team_member")
    @patch("services.team_service.remove_team_member")
    def test_team_lifecycle_with_members(
        self,
        mock_remove_member,
        mock_add_member,
        mock_create_team,
        client: TestClient,
        test_user: Dict[str, Any],
        team_factory,
    ):
        """
        Test complete team lifecycle with member management.
        """
        _set_auth_user(test_user)
        team_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        team_data = team_factory(hackathon_id=hackathon_id, lead_id=test_user["id"])

        # Step 1: CREATE team
        mock_create_team.return_value = {
            "team_id": team_id,
            **team_data,
            "members": [{"user_id": test_user["id"], "role": "LEAD"}],
            "created_at": datetime.utcnow().isoformat(),
        }

        create_response = client.post(
            "/teams",
            json=team_data,
            headers={"Authorization": "Bearer test-token"},
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        team = create_response.json()
        assert team["team_id"] == team_id
        assert len(team["members"]) == 1
        assert team["members"][0]["role"] == "LEAD"

        # Step 2: ADD team member
        new_member_id = str(uuid.uuid4())
        mock_add_member.return_value = {
            "success": True,
            "team_id": team_id,
            "member": {
                "user_id": new_member_id,
                "role": "MEMBER",
                "joined_at": datetime.utcnow().isoformat(),
            },
        }

        add_response = client.post(
            f"/teams/{team_id}/members",
            json={"user_id": new_member_id, "role": "MEMBER"},
            headers={"Authorization": "Bearer test-token"},
        )

        assert add_response.status_code == status.HTTP_200_OK
        add_data = add_response.json()
        assert add_data["success"] is True
        assert add_data["member"]["user_id"] == new_member_id

        # Step 3: REMOVE team member
        mock_remove_member.return_value = {
            "success": True,
            "team_id": team_id,
            "message": f"Member {new_member_id} removed from team",
        }

        remove_response = client.delete(
            f"/teams/{team_id}/members/{new_member_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        assert remove_response.status_code == status.HTTP_200_OK
        remove_data = remove_response.json()
        assert remove_data["success"] is True

    @patch("services.team_service.list_teams")
    def test_list_teams_by_hackathon(
        self, mock_list_teams, client: TestClient, test_user: Dict[str, Any]
    ):
        """
        Test listing teams for a specific hackathon.
        """
        _set_auth_user(test_user)
        hackathon_id = str(uuid.uuid4())

        mock_teams = [
            {
                "team_id": str(uuid.uuid4()),
                "name": f"Team {i}",
                "hackathon_id": hackathon_id,
                "member_count": i + 2,
            }
            for i in range(3)
        ]

        mock_list_teams.return_value = {"teams": mock_teams, "total": 3}

        response = client.get(
            f"/teams?hackathon_id={hackathon_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["teams"]) == 3
        assert all(team["hackathon_id"] == hackathon_id for team in data["teams"])


# ============================================================================
# Submission Endpoint Tests - File Upload and Status Flow
# ============================================================================


class TestSubmissionEndpoints:
    """Test submission CRUD operations and file uploads."""

    @patch("services.submission_service.create_submission")
    @patch("services.submission_service.upload_file_to_submission")
    def test_submission_with_file_upload(
        self,
        mock_upload_file,
        mock_create_submission,
        client: TestClient,
        test_user: Dict[str, Any],
        submission_factory,
    ):
        """
        Test submission creation with file upload.
        """
        _set_auth_user(test_user)
        submission_id = str(uuid.uuid4())
        submission_data = submission_factory()

        # Step 1: CREATE submission
        mock_create_submission.return_value = {
            "submission_id": submission_id,
            **submission_data,
            "files": [],
            "created_at": datetime.utcnow().isoformat(),
        }

        create_response = client.post(
            "/v1/submissions",
            json=submission_data,
            headers={"Authorization": "Bearer test-token"},
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        submission = create_response.json()
        assert submission["submission_id"] == submission_id
        assert submission["status"] == "DRAFT"
        assert len(submission["files"]) == 0

        # Step 2: UPLOAD file
        file_id = str(uuid.uuid4())
        mock_upload_file.return_value = {
            "success": True,
            "file": {
                "file_id": file_id,
                "filename": "demo-video.mp4",
                "file_type": "video/mp4",
                "size_bytes": 5242880,
                "uploaded_at": datetime.utcnow().isoformat(),
            },
        }

        upload_response = client.post(
            f"/v1/submissions/{submission_id}/files",
            json={
                "filename": "demo-video.mp4",
                "file_type": "video/mp4",
                "file_content": "base64-encoded-content",
            },
            headers={"Authorization": "Bearer test-token"},
        )

        assert upload_response.status_code == status.HTTP_200_OK
        upload_data = upload_response.json()
        assert upload_data["success"] is True
        assert upload_data["file"]["filename"] == "demo-video.mp4"

    @patch("services.submission_service.update_submission")
    def test_submission_status_workflow(
        self, mock_update, client: TestClient, test_user: Dict[str, Any]
    ):
        """
        Test submission status transitions.
        """
        _set_auth_user(test_user)
        submission_id = str(uuid.uuid4())

        # DRAFT -> SUBMITTED
        mock_update.return_value = {
            "submission_id": submission_id,
            "status": "SUBMITTED",
            "submitted_at": datetime.utcnow().isoformat(),
        }

        response = client.patch(
            f"/v1/submissions/{submission_id}",
            json={"status": "SUBMITTED"},
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "SUBMITTED"
        assert "submitted_at" in data


# ============================================================================
# Judging Endpoint Tests - Scoring and Results
# ============================================================================


class TestJudgingEndpoints:
    """Test judging operations and scoring."""

    @patch("services.judging_service.submit_score")
    def test_judge_score_submission(
        self, mock_submit_score, client: TestClient, test_judge: Dict[str, Any]
    ):
        """
        Test judge scoring a submission.
        """
        _set_auth_user(test_judge)
        submission_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        rubric_id = str(uuid.uuid4())

        score_data = {
            "scores": {
                "innovation": 8.5,
                "technical": 9.0,
                "design": 7.5,
                "presentation": 8.0,
            },
            "feedback": "Excellent technical implementation",
        }

        mock_submit_score.return_value = {
            "score_id": str(uuid.uuid4()),
            "submission_id": submission_id,
            "judge_id": test_judge["id"],
            "total_score": 8.25,
            **score_data,
            "created_at": datetime.utcnow().isoformat(),
        }

        response = client.post(
            f"/judging/scores?submission_id={submission_id}&hackathon_id={hackathon_id}&rubric_id={rubric_id}",
            json=score_data,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        result = response.json()
        assert result["judge_id"] == test_judge["id"]
        assert result["total_score"] == 8.25
        assert "feedback" in result

    @patch("services.judging_service.get_leaderboard")
    def test_get_hackathon_leaderboard(
        self, mock_leaderboard, client: TestClient, test_user: Dict[str, Any]
    ):
        """
        Test retrieving hackathon leaderboard.
        """
        _set_auth_user(test_user)
        hackathon_id = str(uuid.uuid4())

        mock_leaderboard.return_value = {
            "hackathon_id": hackathon_id,
            "rankings": [
                {
                    "rank": i + 1,
                    "submission_id": str(uuid.uuid4()),
                    "team_name": f"Team {i + 1}",
                    "average_score": 9.0 - (i * 0.5),
                    "judge_count": 3,
                }
                for i in range(10)
            ],
        }

        response = client.get(
            f"/judging/leaderboard/{hackathon_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["rankings"]) == 10
        assert data["rankings"][0]["rank"] == 1
        assert data["rankings"][0]["average_score"] > data["rankings"][1]["average_score"]

    def test_judge_score_validation_errors(
        self, client: TestClient, test_judge: Dict[str, Any]
    ):
        """
        Test score validation errors.
        """
        _set_auth_user(test_judge)
        submission_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        rubric_id = str(uuid.uuid4())

        # Test: Score out of range
        invalid_score = {
            "scores": {
                "innovation": 11.0,  # Invalid: > 10
                "technical": 9.0,
                "design": 7.5,
                "presentation": 8.0,
            },
            "feedback": "Good work",
        }

        response = client.post(
            f"/judging/scores?submission_id={submission_id}&hackathon_id={hackathon_id}&rubric_id={rubric_id}",
            json=invalid_score,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
        ]


# ============================================================================
# Participant Endpoint Tests - Join/Leave/Invite
# ============================================================================


class TestParticipantEndpoints:
    """Test participant management operations."""

    @patch("services.participants_service.ParticipantsService.join_hackathon")
    def test_join_hackathon_as_builder(
        self, mock_join, client: TestClient, test_builder: Dict[str, Any]
    ):
        """
        Test user joining hackathon as BUILDER.
        """
        _set_auth_user(test_builder)
        hackathon_id = str(uuid.uuid4())

        mock_join.return_value = {
            "participant_id": str(uuid.uuid4()),
            "hackathon_id": hackathon_id,
            "user_id": test_builder["id"],
            "role": "BUILDER",
            "joined_at": datetime.utcnow().isoformat(),
        }

        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/join",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["participant"]["role"] == "BUILDER"
        assert data["participant"]["hackathon_id"] == hackathon_id

    @patch("services.participants_service.ParticipantsService.leave_hackathon")
    def test_leave_hackathon(
        self, mock_leave, client: TestClient, test_user: Dict[str, Any]
    ):
        """
        Test user leaving hackathon.
        """
        _set_auth_user(test_user)
        hackathon_id = str(uuid.uuid4())

        mock_leave.return_value = {
            "success": True,
            "hackathon_id": hackathon_id,
            "message": "Successfully left hackathon",
        }

        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/leave",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    @patch("services.authorization.check_organizer")
    @patch("services.participants_service.ParticipantsService.invite_judges")
    def test_invite_judges_as_organizer(
        self,
        mock_invite_judges,
        mock_check_organizer,
        client: TestClient,
        test_organizer: Dict[str, Any],
    ):
        """
        Test organizer inviting judges.
        """
        _set_auth_user(test_organizer)
        mock_check_organizer.return_value = True
        hackathon_id = str(uuid.uuid4())

        judge_emails = ["judge1@example.com", "judge2@example.com", "judge3@example.com"]

        mock_invite_judges.return_value = {
            "success": True,
            "invited_count": 3,
            "invited_emails": judge_emails,
        }

        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/invite-judges",
            json={"emails": judge_emails, "message": "Join us as a judge!"},
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["invited_count"] == 3


# ============================================================================
# Authentication Tests
# ============================================================================


class TestAuthentication:
    """Test authentication flows and token validation."""

    def test_missing_auth_token_returns_401(self, client: TestClient):
        """
        Test requests without authentication return 401.
        """
        # Clear overrides for this test
        app.dependency_overrides.pop(get_current_user, None)

        # No auth header
        response = client.get("/api/v1/hackathons")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Invalid token format
        response = client.get("/api/v1/hackathons", headers={"Authorization": "InvalidFormat"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("api.dependencies.auth_client.verify_token")
    def test_expired_token_returns_401(self, mock_verify, client: TestClient):
        """
        Test expired JWT token returns 401.
        """
        # Clear overrides so real auth runs
        app.dependency_overrides.pop(get_current_user, None)

        from integrations.ainative.exceptions import TokenExpiredError

        mock_verify.side_effect = TokenExpiredError()

        response = client.get("/api/v1/hackathons", headers={"Authorization": "Bearer expired-token"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("api.dependencies.auth_client.verify_api_key")
    def test_api_key_authentication(self, mock_verify_key, client: TestClient, test_user: Dict[str, Any]):
        """
        Test API key authentication.
        """
        # Clear overrides so real auth runs
        app.dependency_overrides.pop(get_current_user, None)

        mock_verify_key.return_value = test_user

        with patch("services.hackathon_service.list_hackathons") as mock_list:
            mock_list.return_value = {"hackathons": [], "total": 0, "skip": 0, "limit": 100}

            response = client.get("/api/v1/hackathons", headers={"X-API-Key": "test-api-key-123"})

            assert response.status_code == status.HTTP_200_OK
            mock_verify_key.assert_called_once_with("test-api-key-123")


# ============================================================================
# Authorization Tests - Role-Based Access Control
# ============================================================================


class TestAuthorization:
    """Test role-based access control and permissions."""

    @patch("services.hackathon_service.get_hackathon")
    def test_non_organizer_cannot_update_hackathon(
        self, mock_get_hackathon, client: TestClient, test_builder: Dict[str, Any]
    ):
        """
        Test non-organizer cannot update hackathon.
        """
        _set_auth_user(test_builder)
        hackathon_id = str(uuid.uuid4())

        # Mock hackathon owned by different user
        mock_get_hackathon.return_value = {
            "hackathon_id": hackathon_id,
            "organizer_id": str(uuid.uuid4()),  # Different from test_builder
        }

        with patch("services.hackathon_service.update_hackathon") as mock_update:
            from fastapi import HTTPException

            mock_update.side_effect = HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have ORGANIZER role for this hackathon",
            )

            response = client.patch(
                f"/api/v1/hackathons/{hackathon_id}",
                json={"status": "active"},
                headers={"Authorization": "Bearer test-token"},
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_builder_cannot_submit_scores(
        self, client: TestClient, test_builder: Dict[str, Any]
    ):
        """
        Test builder cannot submit judge scores.
        """
        _set_auth_user(test_builder)

        score_data = {
            "scores": {"innovation": 8.0, "technical": 7.5},
            "feedback": "Great work",
        }

        submission_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        rubric_id = str(uuid.uuid4())

        with patch("services.judging_service.submit_score") as mock_submit:
            from fastapi import HTTPException

            mock_submit.side_effect = HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have JUDGE role",
            )

            response = client.post(
                f"/judging/scores?submission_id={submission_id}&hackathon_id={hackathon_id}&rubric_id={rubric_id}",
                json=score_data,
                headers={"Authorization": "Bearer test-token"},
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling and edge cases."""

    @patch("services.hackathon_service.get_hackathon")
    def test_hackathon_not_found_returns_404(
        self, mock_get, client: TestClient, test_user: Dict[str, Any]
    ):
        """
        Test 404 for non-existent hackathon.
        """
        _set_auth_user(test_user)

        from fastapi import HTTPException

        mock_get.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hackathon not found"
        )

        response = client.get(
            f"/api/v1/hackathons/{uuid.uuid4()}",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_zerodb_timeout_returns_504(
        self, client: TestClient, test_user: Dict[str, Any]
    ):
        """
        Test ZeroDB timeout returns 504.
        """
        _set_auth_user(test_user)

        with patch("services.team_service.list_teams") as mock_list:
            from fastapi import HTTPException

            mock_list.side_effect = HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Request timeout"
            )

            response = client.get("/teams", headers={"Authorization": "Bearer test-token"})

            assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    def test_validation_error_returns_422(
        self, client: TestClient, test_user: Dict[str, Any]
    ):
        """
        Test validation errors return 422.
        """
        _set_auth_user(test_user)

        # Invalid JSON structure
        response = client.post(
            "/v1/submissions",
            json={"invalid_field": "value"},  # Missing required fields
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_data = response.json()
        assert "error" in error_data or "detail" in error_data

    def test_server_error_returns_500(self, client: TestClient):
        """
        Test unexpected server errors return 500.
        """
        # For this test, we need the real auth to fail with an unexpected error
        # Clear overrides and patch the dependency itself to raise
        app.dependency_overrides.pop(get_current_user, None)

        with patch("api.dependencies.auth_client.verify_token") as mock_verify:
            mock_verify.side_effect = Exception("Unexpected error")

            response = client.get("/api/v1/hackathons", headers={"Authorization": "Bearer test-token"})

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ============================================================================
# Health and Utility Endpoints
# ============================================================================


class TestHealthEndpoints:
    """Test health check and utility endpoints."""

    def test_health_check_no_auth_required(self, client: TestClient):
        """
        Test health check endpoint works without auth.
        """
        response = client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_openapi_docs_accessible(self, client: TestClient):
        """
        Test OpenAPI documentation endpoints.
        """
        response = client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK

        openapi_schema = response.json()
        assert "openapi" in openapi_schema
        assert "info" in openapi_schema
        assert "paths" in openapi_schema


# ============================================================================
# Integration Test - Complete Hackathon Flow
# ============================================================================


class TestCompleteHackathonFlow:
    """
    End-to-end integration test for complete hackathon workflow.

    This test simulates a full hackathon lifecycle from creation to results.
    """

    def test_complete_hackathon_workflow(
        self,
        client: TestClient,
        test_organizer: Dict[str, Any],
        test_builder: Dict[str, Any],
        test_judge: Dict[str, Any],
        hackathon_factory,
        team_factory,
        submission_factory,
    ):
        """
        Complete hackathon flow integration test.

        Flow:
        1. Organizer creates hackathon
        2. Builder joins hackathon
        3. Builder creates team
        4. Team creates submission
        5. Judge scores submission
        6. Retrieve leaderboard with results
        """
        hackathon_id = str(uuid.uuid4())
        team_id = str(uuid.uuid4())
        submission_id = str(uuid.uuid4())

        # Step 1: Organizer creates hackathon
        _set_auth_user(test_organizer)
        hackathon_data = hackathon_factory(organizer_id=test_organizer["id"])

        with patch("services.hackathon_service.create_hackathon") as mock_create:
            mock_create.return_value = {
                "hackathon_id": hackathon_id,
                **hackathon_data,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = client.post(
                "/api/v1/hackathons",
                json=hackathon_data,
                headers={"Authorization": "Bearer organizer-token"},
            )
            assert response.status_code == status.HTTP_201_CREATED

        # Step 2: Builder joins hackathon
        _set_auth_user(test_builder)

        with patch("services.participants_service.ParticipantsService.join_hackathon") as mock_join:
            mock_join.return_value = {
                "participant_id": str(uuid.uuid4()),
                "hackathon_id": hackathon_id,
                "user_id": test_builder["id"],
                "role": "BUILDER",
            }

            response = client.post(
                f"/api/v1/hackathons/{hackathon_id}/join",
                headers={"Authorization": "Bearer builder-token"},
            )
            assert response.status_code == status.HTTP_201_CREATED

        # Step 3: Builder creates team
        team_data = team_factory(hackathon_id=hackathon_id, lead_id=test_builder["id"])

        with patch("services.team_service.create_team") as mock_create_team:
            mock_create_team.return_value = {
                "team_id": team_id,
                **team_data,
                "created_at": datetime.utcnow().isoformat(),
            }

            response = client.post(
                "/teams",
                json=team_data,
                headers={"Authorization": "Bearer builder-token"},
            )
            assert response.status_code == status.HTTP_201_CREATED

        # Step 4: Team creates submission
        submission_data = submission_factory(hackathon_id=hackathon_id, team_id=team_id)

        with patch("services.submission_service.create_submission") as mock_create_sub:
            mock_create_sub.return_value = {
                "submission_id": submission_id,
                **submission_data,
                "created_at": datetime.utcnow().isoformat(),
            }

            response = client.post(
                "/v1/submissions",
                json=submission_data,
                headers={"Authorization": "Bearer builder-token"},
            )
            assert response.status_code == status.HTTP_201_CREATED

        # Step 5: Judge scores submission
        _set_auth_user(test_judge)

        with patch("services.judging_service.submit_score") as mock_score:
            mock_score.return_value = {
                "score_id": str(uuid.uuid4()),
                "submission_id": submission_id,
                "total_score": 8.5,
            }

            response = client.post(
                f"/judging/scores?submission_id={submission_id}&hackathon_id={hackathon_id}&rubric_id={uuid.uuid4()}",
                json={"scores": {"innovation": 8.5}, "feedback": "Great!"},
                headers={"Authorization": "Bearer judge-token"},
            )
            assert response.status_code == status.HTTP_201_CREATED

        # Step 6: Retrieve leaderboard
        with patch("services.judging_service.get_leaderboard") as mock_leaderboard:
            mock_leaderboard.return_value = {
                "hackathon_id": hackathon_id,
                "rankings": [
                    {
                        "rank": 1,
                        "submission_id": submission_id,
                        "team_name": team_data["name"],
                        "average_score": 8.5,
                    }
                ],
            }

            response = client.get(
                f"/judging/leaderboard/{hackathon_id}",
                headers={"Authorization": "Bearer builder-token"},
            )
            assert response.status_code == status.HTTP_200_OK
            leaderboard = response.json()
            assert len(leaderboard["rankings"]) > 0
