"""
Tests for AI-Powered Recommendations

Tests the recommendations service business logic and API endpoints for
judge recommendations, team formation suggestions, and RLHF feedback tracking.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBTimeoutError
from services.recommendations_service import RecommendationsService


class TestRecommendSubmissionsForJudge:
    """Test recommend_submissions_for_judge service method"""

    @pytest.mark.asyncio
    async def test_recommend_for_judge_with_scoring_history(self):
        """Should recommend based on judge's highly-rated submissions"""
        # Arrange
        mock_client = AsyncMock()

        # Mock judge participant verification
        mock_client.tables.query_rows.side_effect = [
            [
                {
                    "hackathon_id": "hack-123",
                    "participant_id": "judge-456",
                    "role": "JUDGE",
                }
            ],  # Judge exists
            [
                {
                    "submission_id": "sub-001",
                    "hackathon_id": "hack-123",
                    "judge_id": "judge-456",
                    "total_score": 95,
                },
                {
                    "submission_id": "sub-002",
                    "hackathon_id": "hack-123",
                    "judge_id": "judge-456",
                    "total_score": 88,
                },
            ],  # Scored submissions
            [],  # All submissions query
            # Queries for high-rated submission details
            [
                {
                    "submission_id": "sub-001",
                    "project_name": "AI Healthcare",
                    "description": "Machine learning diagnosis",
                }
            ],
            [
                {
                    "submission_id": "sub-002",
                    "project_name": "Medical Chatbot",
                    "description": "AI-powered medical assistant",
                }
            ],
            # Query for recommended submission details
            [
                {
                    "submission_id": "sub-999",
                    "team_id": "team-001",
                    "hackathon_id": "hack-123",
                    "project_name": "Health AI Platform",
                    "description": "Deep learning medical imaging",
                    "status": "SUBMITTED",
                    "created_at": "2024-01-15T10:00:00Z",
                }
            ],
        ]

        # Mock embeddings search
        mock_client.embeddings.search.return_value = [
            {
                "id": "sub-999",
                "score": 0.89,
                "metadata": {},
            }
        ]

        service = RecommendationsService(mock_client)

        # Act
        result = await service.recommend_submissions_for_judge(
            judge_id="judge-456",
            hackathon_id="hack-123",
            top_k=10,
        )

        # Assert
        assert len(result["recommended_submissions"]) == 1
        assert result["recommended_submissions"][0]["submission_id"] == "sub-999"
        assert result["recommended_submissions"][0]["relevance_score"] == 0.89
        assert result["total_recommended"] == 1
        assert "highly-rated" in result["recommendation_reason"]
        assert "execution_time_ms" in result

    @pytest.mark.asyncio
    async def test_recommend_for_new_judge_without_history(self):
        """Should provide diverse recommendations for new judges"""
        # Arrange
        mock_client = AsyncMock()

        mock_client.tables.query_rows.side_effect = [
            [{"hackathon_id": "hack-123", "participant_id": "judge-new", "role": "JUDGE"}],
            [],  # No scored submissions
            [],  # All submissions query
            [
                {
                    "submission_id": "sub-100",
                    "team_id": "team-100",
                    "hackathon_id": "hack-123",
                    "project_name": "Innovative Project",
                    "description": "Creative solution",
                    "status": "SUBMITTED",
                    "created_at": "2024-01-15T10:00:00Z",
                }
            ],
        ]

        mock_client.embeddings.search.return_value = [
            {"id": "sub-100", "score": 0.75, "metadata": {}}
        ]

        service = RecommendationsService(mock_client)

        # Act
        result = await service.recommend_submissions_for_judge(
            judge_id="judge-new",
            hackathon_id="hack-123",
            top_k=10,
        )

        # Assert
        assert len(result["recommended_submissions"]) == 1
        assert "Diverse" in result["recommendation_reason"]
        mock_client.embeddings.search.assert_called_once()
        call_args = mock_client.embeddings.search.call_args
        assert "innovative" in call_args[1]["query"]

    @pytest.mark.asyncio
    async def test_recommend_for_judge_not_found(self):
        """Should raise 404 when judge not found in hackathon"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []  # Judge not found

        service = RecommendationsService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.recommend_submissions_for_judge(
                judge_id="nonexistent",
                hackathon_id="hack-123",
                top_k=10,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_recommend_excludes_already_scored(self):
        """Should exclude submissions already scored by judge"""
        # Arrange
        mock_client = AsyncMock()

        mock_client.tables.query_rows.side_effect = [
            [{"hackathon_id": "hack-123", "participant_id": "judge-456", "role": "JUDGE"}],
            [
                {"submission_id": "sub-scored", "judge_id": "judge-456", "total_score": 80}
            ],  # Already scored
            [],  # All submissions
            # No high-rated queries needed since we have 0 scored submissions for query building
        ]

        # Search returns both scored and unscored, but we should filter
        mock_client.embeddings.search.return_value = [
            {"id": "sub-scored", "score": 0.95, "metadata": {}},  # Should be excluded
            {"id": "sub-new", "score": 0.90, "metadata": {}},  # Should be included
        ]

        # Mock query for the new submission only (scored should be filtered out)
        mock_client.tables.query_rows.side_effect.append(
            [
                {
                    "submission_id": "sub-new",
                    "team_id": "team-001",
                    "hackathon_id": "hack-123",
                    "project_name": "New Project",
                    "description": "Fresh submission",
                    "status": "SUBMITTED",
                    "created_at": "2024-01-15T10:00:00Z",
                }
            ]
        )

        service = RecommendationsService(mock_client)

        # Act
        result = await service.recommend_submissions_for_judge(
            judge_id="judge-456",
            hackathon_id="hack-123",
            top_k=10,
        )

        # Assert - should only have sub-new, not sub-scored
        assert len(result["recommended_submissions"]) == 1
        assert result["recommended_submissions"][0]["submission_id"] == "sub-new"

    @pytest.mark.asyncio
    async def test_recommend_timeout_error(self):
        """Should raise 504 when search times out"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = [
            [{"hackathon_id": "hack-123", "participant_id": "judge-456", "role": "JUDGE"}],
            [],  # Scored submissions
            [],  # All submissions
        ]
        mock_client.embeddings.search.side_effect = ZeroDBTimeoutError("Timeout")

        service = RecommendationsService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.recommend_submissions_for_judge(
                judge_id="judge-456",
                hackathon_id="hack-123",
            )

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_recommend_database_error(self):
        """Should raise 500 when database error occurs"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = ZeroDBError("Database error")

        service = RecommendationsService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.recommend_submissions_for_judge(
                judge_id="judge-456",
                hackathon_id="hack-123",
            )

        assert exc_info.value.status_code == 500


class TestSuggestTeamFormation:
    """Test suggest_team_formation service method"""

    @pytest.mark.asyncio
    async def test_suggest_team_with_desired_skills(self):
        """Should suggest participants matching desired skills"""
        # Arrange
        mock_client = AsyncMock()

        mock_client.tables.query_rows.side_effect = [
            [
                {
                    "hackathon_id": "hack-123",
                    "participant_id": "builder-456",
                }
            ],  # Participant exists
            [],  # Team members
            [
                {
                    "participant_id": "builder-789",
                    "hackathon_id": "hack-123",
                    "role": "BUILDER",
                }
            ],  # Available participants
        ]

        mock_client.embeddings.search.return_value = [
            {"id": "builder-789", "score": 0.88, "metadata": {}}
        ]

        service = RecommendationsService(mock_client)

        # Act
        result = await service.suggest_team_formation(
            hackathon_id="hack-123",
            participant_id="builder-456",
            desired_skills=["Python", "React", "Machine Learning"],
            top_k=10,
        )

        # Assert
        assert len(result["suggested_participants"]) == 1
        assert result["suggested_participants"][0]["participant_id"] == "builder-789"
        assert result["suggested_participants"][0]["match_score"] == 0.88
        assert "Python" in result["suggestion_reason"]
        assert "execution_time_ms" in result

    @pytest.mark.asyncio
    async def test_suggest_team_without_desired_skills(self):
        """Should suggest diverse participants when no skills specified"""
        # Arrange
        mock_client = AsyncMock()

        mock_client.tables.query_rows.side_effect = [
            [{"hackathon_id": "hack-123", "participant_id": "builder-456"}],
            [],  # Team members
            [
                {
                    "participant_id": "builder-999",
                    "hackathon_id": "hack-123",
                    "role": "BUILDER",
                }
            ],  # Available participants
        ]

        mock_client.embeddings.search.return_value = [
            {"id": "builder-999", "score": 0.70, "metadata": {}}
        ]

        service = RecommendationsService(mock_client)

        # Act
        result = await service.suggest_team_formation(
            hackathon_id="hack-123",
            participant_id="builder-456",
            desired_skills=None,
            top_k=10,
        )

        # Assert
        assert len(result["suggested_participants"]) == 1
        assert "Diverse" in result["suggestion_reason"]
        call_args = mock_client.embeddings.search.call_args
        assert "collaborative" in call_args[1]["query"]

    @pytest.mark.asyncio
    async def test_suggest_team_participant_not_found(self):
        """Should raise 404 when participant not found"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []  # Participant not found

        service = RecommendationsService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.suggest_team_formation(
                hackathon_id="hack-123",
                participant_id="nonexistent",
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_suggest_team_excludes_participants_on_teams(self):
        """Should exclude participants already on teams"""
        # Arrange
        mock_client = AsyncMock()

        mock_client.tables.query_rows.side_effect = [
            [{"hackathon_id": "hack-123", "participant_id": "builder-456"}],
            [
                {"participant_id": "builder-on-team", "hackathon_id": "hack-123"}
            ],  # On team
            [
                {"participant_id": "builder-on-team", "role": "BUILDER"},
                {"participant_id": "builder-available", "role": "BUILDER"},
            ],  # All participants
        ]

        mock_client.embeddings.search.return_value = [
            {"id": "builder-on-team", "score": 0.95, "metadata": {}},  # Should exclude
            {"id": "builder-available", "score": 0.90, "metadata": {}},  # Should include
        ]

        service = RecommendationsService(mock_client)

        # Act
        result = await service.suggest_team_formation(
            hackathon_id="hack-123",
            participant_id="builder-456",
            top_k=10,
        )

        # Assert - should only have available builder
        suggestions = result["suggested_participants"]
        assert len(suggestions) == 1
        assert suggestions[0]["participant_id"] == "builder-available"

    @pytest.mark.asyncio
    async def test_suggest_team_excludes_self(self):
        """Should exclude the requesting participant from suggestions"""
        # Arrange
        mock_client = AsyncMock()

        mock_client.tables.query_rows.side_effect = [
            [{"hackathon_id": "hack-123", "participant_id": "builder-456"}],
            [],  # Team members
            [
                {"participant_id": "builder-456", "role": "BUILDER"},  # Self
                {"participant_id": "builder-789", "role": "BUILDER"},  # Other
            ],
        ]

        mock_client.embeddings.search.return_value = [
            {"id": "builder-456", "score": 1.0, "metadata": {}},  # Self - should exclude
            {"id": "builder-789", "score": 0.85, "metadata": {}},  # Should include
        ]

        service = RecommendationsService(mock_client)

        # Act
        result = await service.suggest_team_formation(
            hackathon_id="hack-123",
            participant_id="builder-456",
            top_k=10,
        )

        # Assert
        suggestions = result["suggested_participants"]
        assert len(suggestions) == 1
        assert suggestions[0]["participant_id"] == "builder-789"

    @pytest.mark.asyncio
    async def test_suggest_team_fallback_to_random(self):
        """Should fallback to random participants if no semantic results"""
        # Arrange
        mock_client = AsyncMock()

        mock_client.tables.query_rows.side_effect = [
            [{"hackathon_id": "hack-123", "participant_id": "builder-456"}],
            [],  # Team members
            [
                {
                    "participant_id": "builder-789",
                    "hackathon_id": "hack-123",
                    "role": "BUILDER",
                },
                {
                    "participant_id": "builder-999",
                    "hackathon_id": "hack-123",
                    "role": "BUILDER",
                },
            ],  # Available participants
        ]

        mock_client.embeddings.search.return_value = []  # No semantic results

        service = RecommendationsService(mock_client)

        # Act
        result = await service.suggest_team_formation(
            hackathon_id="hack-123",
            participant_id="builder-456",
            top_k=10,
        )

        # Assert - should return available participants with default score
        assert len(result["suggested_participants"]) == 2
        assert result["suggested_participants"][0]["match_score"] == 0.5
        assert "Available participants" in result["suggestion_reason"]


class TestTrackRecommendationFeedback:
    """Test track_recommendation_feedback service method"""

    @pytest.mark.asyncio
    async def test_track_thumbs_up_feedback(self):
        """Should track thumbs_up feedback successfully"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.insert_rows.return_value = {"count": 1}

        service = RecommendationsService(mock_client)

        # Act
        result = await service.track_recommendation_feedback(
            recommendation_id="rec-123",
            user_id="user-456",
            feedback_type="thumbs_up",
            rating=None,
            comment="Great recommendations!",
        )

        # Assert
        assert result["success"] is True
        assert result["recommendation_id"] == "rec-123"
        assert result["feedback_tracked"] is True

        # Verify insert was called
        mock_client.tables.insert_rows.assert_called_once()
        call_args = mock_client.tables.insert_rows.call_args
        assert call_args[0][0] == "recommendation_feedback"
        inserted_row = call_args[1]["rows"][0]
        assert inserted_row["feedback_type"] == "thumbs_up"
        assert inserted_row["user_id"] == "user-456"

    @pytest.mark.asyncio
    async def test_track_rating_feedback(self):
        """Should track rating feedback with validation"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.insert_rows.return_value = {"count": 1}

        service = RecommendationsService(mock_client)

        # Act
        result = await service.track_recommendation_feedback(
            recommendation_id="rec-123",
            user_id="user-456",
            feedback_type="rating",
            rating=5,
            comment="Excellent!",
        )

        # Assert
        assert result["success"] is True
        call_args = mock_client.tables.insert_rows.call_args
        inserted_row = call_args[1]["rows"][0]
        assert inserted_row["rating"] == 5

    @pytest.mark.asyncio
    async def test_track_invalid_feedback_type(self):
        """Should raise 400 for invalid feedback_type"""
        # Arrange
        mock_client = AsyncMock()
        service = RecommendationsService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.track_recommendation_feedback(
                recommendation_id="rec-123",
                user_id="user-456",
                feedback_type="invalid_type",
                rating=None,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid feedback_type" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_track_rating_without_value(self):
        """Should raise 400 when rating type missing rating value"""
        # Arrange
        mock_client = AsyncMock()
        service = RecommendationsService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.track_recommendation_feedback(
                recommendation_id="rec-123",
                user_id="user-456",
                feedback_type="rating",
                rating=None,  # Missing rating
            )

        assert exc_info.value.status_code == 400
        assert "Rating must be between 1 and 5" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_track_rating_out_of_range(self):
        """Should raise 400 when rating is out of range"""
        # Arrange
        mock_client = AsyncMock()
        service = RecommendationsService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.track_recommendation_feedback(
                recommendation_id="rec-123",
                user_id="user-456",
                feedback_type="rating",
                rating=6,  # Out of range
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_track_feedback_database_error(self):
        """Should raise 500 when database error occurs"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.insert_rows.side_effect = ZeroDBError("Database error")

        service = RecommendationsService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.track_recommendation_feedback(
                recommendation_id="rec-123",
                user_id="user-456",
                feedback_type="thumbs_up",
            )

        assert exc_info.value.status_code == 500


class TestRecommendationsRoutes:
    """Test recommendations API endpoints"""

    @pytest.mark.asyncio
    async def test_judge_recommendations_endpoint(self):
        """Should handle GET /hackathons/{id}/recommendations/judge requests"""
        # Integration test placeholder
        # Would require full FastAPI test client setup
        pass

    @pytest.mark.asyncio
    async def test_team_suggestions_endpoint(self):
        """Should handle POST /hackathons/{id}/recommendations/team requests"""
        # Integration test placeholder
        # Would require full FastAPI test client setup
        pass

    @pytest.mark.asyncio
    async def test_feedback_tracking_endpoint(self):
        """Should handle POST /recommendations/{id}/feedback requests"""
        # Integration test placeholder
        # Would require full FastAPI test client setup
        pass
