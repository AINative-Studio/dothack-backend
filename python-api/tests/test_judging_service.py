"""
Tests for Judging Service

Following TDD methodology - tests written before implementation.
Tests judging and scoring operations for hackathon submissions.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)
from services.judging_service import (
    calculate_rankings,
    get_leaderboard,
    get_scores,
    submit_score,
)


class TestSubmitScore:
    """Test submit_score() function"""

    @pytest.mark.asyncio
    async def test_submit_score_success(self):
        """Should successfully submit a score"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())
        judge_id = str(uuid.uuid4())
        rubric_id = str(uuid.uuid4())

        # Mock authorization check and duplicate check
        mock_client.tables.query_rows.side_effect = [
            [{"user_id": judge_id, "hackathon_id": "hack-123", "role": "judge"}],
            [],  # No existing scores
        ]

        # Mock successful score insertion
        mock_client.tables.insert_rows.return_value = {
            "row_ids": ["score-abc-123"],
            "success": True,
        }

        # Act
        result = await submit_score(
            zerodb_client=mock_client,
            submission_id=submission_id,
            judge_participant_id=judge_id,
            hackathon_id="hack-123",
            rubric_id=rubric_id,
            scores_breakdown={
                "innovation": 8,
                "technical_quality": 9,
                "presentation": 7,
            },
            total_score=24.0,
            feedback="Excellent project with innovative approach",
        )

        # Assert
        assert result is not None
        assert result.get("success") is True
        mock_client.tables.insert_rows.assert_called_once()
        call_args = mock_client.tables.insert_rows.call_args
        assert call_args[0][0] == "scores"
        assert len(call_args[1]["rows"]) == 1
        score_row = call_args[1]["rows"][0]
        assert score_row["submission_id"] == submission_id
        assert score_row["judge_participant_id"] == judge_id
        assert score_row["total_score"] == 24.0

    @pytest.mark.asyncio
    async def test_submit_score_forbidden_not_judge(self):
        """Should raise 403 when user is not a judge"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())
        judge_id = str(uuid.uuid4())

        # Mock authorization check - user is builder, not judge
        mock_client.tables.query_rows.return_value = [
            {
                "user_id": judge_id,
                "hackathon_id": "hack-123",
                "role": "builder",
            }
        ]

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await submit_score(
                zerodb_client=mock_client,
                submission_id=submission_id,
                judge_participant_id=judge_id,
                hackathon_id="hack-123",
                rubric_id=str(uuid.uuid4()),
                scores_breakdown={"innovation": 8},
                total_score=8.0,
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_submit_score_duplicate_prevention(self):
        """Should check for duplicate scores from same judge"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())
        judge_id = str(uuid.uuid4())

        # Mock authorization check
        mock_client.tables.query_rows.side_effect = [
            [{"user_id": judge_id, "hackathon_id": "hack-123", "role": "judge"}],
            [{"score_id": "existing-score", "judge_participant_id": judge_id}],  # Existing score
        ]

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await submit_score(
                zerodb_client=mock_client,
                submission_id=submission_id,
                judge_participant_id=judge_id,
                hackathon_id="hack-123",
                rubric_id=str(uuid.uuid4()),
                scores_breakdown={"innovation": 8},
                total_score=8.0,
            )

        assert exc_info.value.status_code == 409
        assert "already submitted" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_submit_score_validates_total_score(self):
        """Should validate that total_score matches scores_breakdown sum"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())
        judge_id = str(uuid.uuid4())

        # Mock authorization check
        mock_client.tables.query_rows.return_value = [
            {
                "user_id": judge_id,
                "hackathon_id": "hack-123",
                "role": "judge",
            }
        ]

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await submit_score(
                zerodb_client=mock_client,
                submission_id=submission_id,
                judge_participant_id=judge_id,
                hackathon_id="hack-123",
                rubric_id=str(uuid.uuid4()),
                scores_breakdown={
                    "innovation": 8,
                    "technical_quality": 9,
                },
                total_score=20.0,  # Should be 17.0
            )

        assert exc_info.value.status_code == 400
        assert "total_score" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_submit_score_handles_zerodb_error(self):
        """Should handle ZeroDB errors gracefully"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())
        judge_id = str(uuid.uuid4())

        # Mock authorization check and duplicate check
        mock_client.tables.query_rows.side_effect = [
            [{"user_id": judge_id, "hackathon_id": "hack-123", "role": "judge"}],
            [],  # No existing scores
        ]

        # Mock database error
        mock_client.tables.insert_rows.side_effect = ZeroDBError("Database error", status_code=500)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await submit_score(
                zerodb_client=mock_client,
                submission_id=submission_id,
                judge_participant_id=judge_id,
                hackathon_id="hack-123",
                rubric_id=str(uuid.uuid4()),
                scores_breakdown={"innovation": 8},
                total_score=8.0,
            )

        assert exc_info.value.status_code == 500


class TestGetScores:
    """Test get_scores() function"""

    @pytest.mark.asyncio
    async def test_get_scores_success(self):
        """Should retrieve all scores for a submission"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())

        mock_scores = [
            {
                "score_id": "score-1",
                "submission_id": submission_id,
                "judge_participant_id": "judge-1",
                "total_score": 24.0,
                "scores_breakdown": {"innovation": 8, "technical_quality": 9, "presentation": 7},
                "feedback": "Great project",
                "created_at": datetime.now().isoformat(),
            },
            {
                "score_id": "score-2",
                "submission_id": submission_id,
                "judge_participant_id": "judge-2",
                "total_score": 22.0,
                "scores_breakdown": {"innovation": 7, "technical_quality": 8, "presentation": 7},
                "feedback": "Good work",
                "created_at": datetime.now().isoformat(),
            },
        ]

        mock_client.tables.query_rows.return_value = mock_scores

        # Act
        result = await get_scores(
            zerodb_client=mock_client,
            submission_id=submission_id,
        )

        # Assert
        assert len(result) == 2
        assert result[0]["total_score"] == 24.0
        assert result[1]["total_score"] == 22.0
        mock_client.tables.query_rows.assert_called_once_with(
            "scores",
            filter={"submission_id": submission_id},
        )

    @pytest.mark.asyncio
    async def test_get_scores_empty_result(self):
        """Should return empty list when no scores found"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())
        mock_client.tables.query_rows.return_value = []

        # Act
        result = await get_scores(
            zerodb_client=mock_client,
            submission_id=submission_id,
        )

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_scores_includes_average(self):
        """Should calculate and include average score"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())

        mock_scores = [
            {
                "score_id": "score-1",
                "submission_id": submission_id,
                "total_score": 24.0,
            },
            {
                "score_id": "score-2",
                "submission_id": submission_id,
                "total_score": 22.0,
            },
        ]

        mock_client.tables.query_rows.return_value = mock_scores

        # Act
        result = await get_scores(
            zerodb_client=mock_client,
            submission_id=submission_id,
            include_average=True,
        )

        # Assert
        assert "average_score" in result
        assert result["average_score"] == 23.0
        assert "scores" in result
        assert len(result["scores"]) == 2


class TestCalculateRankings:
    """Test calculate_rankings() function"""

    @pytest.mark.asyncio
    async def test_calculate_rankings_success(self):
        """Should calculate rankings based on average scores"""
        # Arrange
        mock_client = AsyncMock()
        hackathon_id = "hack-123"

        # Mock projects and submissions
        mock_projects = [
            {"project_id": "proj-1", "hackathon_id": hackathon_id},
            {"project_id": "proj-2", "hackathon_id": hackathon_id},
            {"project_id": "proj-3", "hackathon_id": hackathon_id},
        ]

        mock_submissions_proj1 = [{"submission_id": "sub-1", "project_id": "proj-1"}]
        mock_submissions_proj2 = [{"submission_id": "sub-2", "project_id": "proj-2"}]
        mock_submissions_proj3 = [{"submission_id": "sub-3", "project_id": "proj-3"}]

        # Mock scores for each submission
        mock_client.tables.query_rows.side_effect = [
            mock_projects,  # First call gets projects
            mock_submissions_proj1,  # Submissions for proj-1
            mock_submissions_proj2,  # Submissions for proj-2
            mock_submissions_proj3,  # Submissions for proj-3
            [{"total_score": 24.0}, {"total_score": 26.0}],  # sub-1 scores (avg: 25.0)
            [{"total_score": 28.0}, {"total_score": 30.0}],  # sub-2 scores (avg: 29.0)
            [{"total_score": 20.0}, {"total_score": 22.0}],  # sub-3 scores (avg: 21.0)
        ]

        # Act
        result = await calculate_rankings(
            zerodb_client=mock_client,
            hackathon_id=hackathon_id,
        )

        # Assert
        assert len(result) == 3
        # Rankings should be sorted by average score (descending)
        assert result[0]["submission_id"] == "sub-2"  # avg: 29.0
        assert result[0]["rank"] == 1
        assert result[0]["average_score"] == 29.0

        assert result[1]["submission_id"] == "sub-1"  # avg: 25.0
        assert result[1]["rank"] == 2

        assert result[2]["submission_id"] == "sub-3"  # avg: 21.0
        assert result[2]["rank"] == 3

    @pytest.mark.asyncio
    async def test_calculate_rankings_handles_ties(self):
        """Should handle tied scores appropriately"""
        # Arrange
        mock_client = AsyncMock()
        hackathon_id = "hack-123"

        mock_projects = [
            {"project_id": "proj-1", "hackathon_id": hackathon_id},
            {"project_id": "proj-2", "hackathon_id": hackathon_id},
        ]

        # Both submissions have same average score
        mock_client.tables.query_rows.side_effect = [
            mock_projects,
            [{"submission_id": "sub-1", "project_id": "proj-1"}],  # proj-1 submissions
            [{"submission_id": "sub-2", "project_id": "proj-2"}],  # proj-2 submissions
            [{"total_score": 25.0}],  # sub-1 scores
            [{"total_score": 25.0}],  # sub-2 scores
        ]

        # Act
        result = await calculate_rankings(
            zerodb_client=mock_client,
            hackathon_id=hackathon_id,
        )

        # Assert
        assert len(result) == 2
        # Both should have same average score
        assert result[0]["average_score"] == result[1]["average_score"]

    @pytest.mark.asyncio
    async def test_calculate_rankings_excludes_unscored(self):
        """Should exclude submissions with no scores"""
        # Arrange
        mock_client = AsyncMock()
        hackathon_id = "hack-123"

        mock_projects = [
            {"project_id": "proj-1", "hackathon_id": hackathon_id},
            {"project_id": "proj-2", "hackathon_id": hackathon_id},
        ]

        mock_client.tables.query_rows.side_effect = [
            mock_projects,
            [{"submission_id": "sub-1", "project_id": "proj-1"}],  # proj-1 submissions
            [{"submission_id": "sub-2", "project_id": "proj-2"}],  # proj-2 submissions
            [{"total_score": 25.0}],  # sub-1 has score
            [],  # sub-2 has no scores
        ]

        # Act
        result = await calculate_rankings(
            zerodb_client=mock_client,
            hackathon_id=hackathon_id,
        )

        # Assert
        assert len(result) == 1
        assert result[0]["submission_id"] == "sub-1"

    @pytest.mark.asyncio
    async def test_calculate_rankings_by_track(self):
        """Should filter rankings by track"""
        # Arrange
        mock_client = AsyncMock()
        hackathon_id = "hack-123"
        track_id = "track-ai"

        # Mock projects filtered by track
        mock_projects = [
            {"project_id": "proj-1", "track_id": track_id, "hackathon_id": hackathon_id},
            {"project_id": "proj-2", "track_id": track_id, "hackathon_id": hackathon_id},
        ]

        mock_client.tables.query_rows.side_effect = [
            mock_projects,  # First call gets projects by track
            [{"submission_id": "sub-1", "project_id": "proj-1"}],  # proj-1 submissions
            [{"submission_id": "sub-2", "project_id": "proj-2"}],  # proj-2 submissions
            [{"total_score": 25.0}],  # sub-1 scores
            [{"total_score": 28.0}],  # sub-2 scores
        ]

        # Act
        result = await calculate_rankings(
            zerodb_client=mock_client,
            hackathon_id=hackathon_id,
            track_id=track_id,
        )

        # Assert
        assert len(result) == 2


class TestGetLeaderboard:
    """Test get_leaderboard() function"""

    @pytest.mark.asyncio
    async def test_get_leaderboard_success(self):
        """Should return formatted leaderboard with team/project details"""
        # Arrange
        mock_client = AsyncMock()
        hackathon_id = "hack-123"

        # Mock rankings
        mock_rankings = [
            {
                "rank": 1,
                "submission_id": "sub-1",
                "project_id": "proj-1",
                "average_score": 29.0,
                "score_count": 3,
            },
            {
                "rank": 2,
                "submission_id": "sub-2",
                "project_id": "proj-2",
                "average_score": 25.0,
                "score_count": 3,
            },
        ]

        # Mock project details
        mock_projects = [
            {
                "project_id": "proj-1",
                "team_id": "team-1",
                "name": "AI Assistant",
                "track_id": "track-ai",
            },
            {
                "project_id": "proj-2",
                "team_id": "team-2",
                "name": "Blockchain App",
                "track_id": "track-web3",
            },
        ]

        # Mock team details
        mock_teams = [
            {
                "team_id": "team-1",
                "name": "Team Alpha",
            },
            {
                "team_id": "team-2",
                "name": "Team Beta",
            },
        ]

        with patch("services.judging_service.calculate_rankings", return_value=mock_rankings):
            mock_client.tables.query_rows.side_effect = [
                [mock_projects[0]],  # proj-1
                [mock_teams[0]],  # team-1
                [mock_projects[1]],  # proj-2
                [mock_teams[1]],  # team-2
            ]

            # Act
            result = await get_leaderboard(
                zerodb_client=mock_client,
                hackathon_id=hackathon_id,
            )

            # Assert
            assert len(result) == 2
            assert result[0]["rank"] == 1
            assert result[0]["team_name"] == "Team Alpha"
            assert result[0]["project_name"] == "AI Assistant"
            assert result[0]["average_score"] == 29.0

    @pytest.mark.asyncio
    async def test_get_leaderboard_with_limit(self):
        """Should limit results when top_n specified"""
        # Arrange
        mock_client = AsyncMock()
        hackathon_id = "hack-123"

        mock_rankings = [
            {"rank": i, "submission_id": f"sub-{i}", "project_id": f"proj-{i}", "average_score": 30 - i, "score_count": 3}
            for i in range(1, 11)
        ]

        with patch("services.judging_service.calculate_rankings", return_value=mock_rankings):
            # Mock project and team queries
            mock_client.tables.query_rows.side_effect = [
                [{"project_id": f"proj-{i}", "team_id": f"team-{i}", "name": f"Project {i}"}]
                for i in range(1, 6)
            ] + [
                [{"team_id": f"team-{i}", "name": f"Team {i}"}]
                for i in range(1, 6)
            ]

            # Act
            result = await get_leaderboard(
                zerodb_client=mock_client,
                hackathon_id=hackathon_id,
                top_n=5,
            )

            # Assert
            assert len(result) <= 5

    @pytest.mark.asyncio
    async def test_get_leaderboard_handles_missing_team_data(self):
        """Should handle cases where team data is missing"""
        # Arrange
        mock_client = AsyncMock()
        hackathon_id = "hack-123"

        mock_rankings = [
            {
                "rank": 1,
                "submission_id": "sub-1",
                "project_id": "proj-1",
                "average_score": 29.0,
                "score_count": 3,
            }
        ]

        with patch("services.judging_service.calculate_rankings", return_value=mock_rankings):
            # Mock project without team
            mock_client.tables.query_rows.side_effect = [
                [{"project_id": "proj-1", "name": "Solo Project", "team_id": "team-1"}],
                [],  # No team found
            ]

            # Act
            result = await get_leaderboard(
                zerodb_client=mock_client,
                hackathon_id=hackathon_id,
            )

            # Assert
            assert len(result) == 1
            assert result[0]["team_name"] is None or result[0]["team_name"] == "N/A"


class TestPerformanceRequirements:
    """Test performance requirements"""

    @pytest.mark.asyncio
    async def test_calculate_rankings_performance(self):
        """Should complete rankings calculation in reasonable time"""
        import time

        # Arrange
        mock_client = AsyncMock()
        hackathon_id = "hack-123"

        # Simulate 50 projects and submissions
        mock_projects = [
            {"submission_id": f"sub-{i}", "project_id": f"proj-{i}", "hackathon_id": hackathon_id}
            for i in range(50)
        ]

        # Mock scores for all submissions - projects, then submissions for each, then scores
        scores_side_effects = [mock_projects]  # Get projects
        for i in range(50):
            scores_side_effects.append([{"submission_id": f"sub-{i}", "project_id": f"proj-{i}"}])  # Submissions
        for _ in range(50):
            scores_side_effects.append([{"total_score": 25.0}])  # Scores

        mock_client.tables.query_rows.side_effect = scores_side_effects

        # Act
        start_time = time.time()
        await calculate_rankings(
            zerodb_client=mock_client,
            hackathon_id=hackathon_id,
        )
        elapsed_time = (time.time() - start_time) * 1000

        # Assert - Should complete within 5 seconds even with 50 submissions
        assert elapsed_time < 5000, f"Rankings took {elapsed_time}ms (expected < 5000ms)"


class TestEdgeCases:
    """Test edge cases and error scenarios"""

    @pytest.mark.asyncio
    async def test_submit_score_with_empty_scores_breakdown(self):
        """Should reject empty scores_breakdown"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())
        judge_id = str(uuid.uuid4())

        mock_client.tables.query_rows.return_value = [
            {"user_id": judge_id, "hackathon_id": "hack-123", "role": "judge"}
        ]

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await submit_score(
                zerodb_client=mock_client,
                submission_id=submission_id,
                judge_participant_id=judge_id,
                hackathon_id="hack-123",
                rubric_id=str(uuid.uuid4()),
                scores_breakdown={},
                total_score=0.0,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_submit_score_with_negative_scores(self):
        """Should reject negative scores"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())
        judge_id = str(uuid.uuid4())

        mock_client.tables.query_rows.return_value = [
            {"user_id": judge_id, "hackathon_id": "hack-123", "role": "judge"}
        ]

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await submit_score(
                zerodb_client=mock_client,
                submission_id=submission_id,
                judge_participant_id=judge_id,
                hackathon_id="hack-123",
                rubric_id=str(uuid.uuid4()),
                scores_breakdown={"innovation": -5},
                total_score=-5.0,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_leaderboard_empty_hackathon(self):
        """Should handle hackathon with no submissions"""
        # Arrange
        mock_client = AsyncMock()
        hackathon_id = "hack-empty"

        with patch("services.judging_service.calculate_rankings", return_value=[]):
            # Act
            result = await get_leaderboard(
                zerodb_client=mock_client,
                hackathon_id=hackathon_id,
            )

            # Assert
            assert result == []
