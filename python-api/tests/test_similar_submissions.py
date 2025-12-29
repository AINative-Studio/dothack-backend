"""
Tests for Similar Submissions Functionality

Tests the find_similar_submissions service method and API endpoint.
"""

from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBTimeoutError
from services.submission_service import find_similar_submissions


class TestFindSimilarSubmissions:
    """Test find_similar_submissions service method"""

    @pytest.mark.asyncio
    async def test_find_similar_submissions_success(self):
        """Should return similar submissions with scores"""
        # Arrange
        mock_client = AsyncMock()

        # Mock the query submission
        mock_client.tables.query_rows.side_effect = [
            [
                {
                    "submission_id": "sub-123",
                    "hackathon_id": "hack-456",
                    "project_name": "AI Healthcare App",
                    "description": "Machine learning for disease detection",
                }
            ],  # Query submission
            [
                {
                    "submission_id": "sub-789",
                    "team_id": "team-001",
                    "hackathon_id": "hack-456",
                    "project_name": "ML Medical Diagnosis",
                    "description": "Deep learning for medical imaging",
                    "status": "SUBMITTED",
                    "created_at": "2024-01-01T00:00:00Z",
                }
            ],  # First similar submission
            [
                {
                    "submission_id": "sub-999",
                    "team_id": "team-002",
                    "hackathon_id": "hack-456",
                    "project_name": "Healthcare AI Platform",
                    "description": "AI-powered patient diagnosis system",
                    "status": "SUBMITTED",
                    "created_at": "2024-01-02T00:00:00Z",
                }
            ],  # Second similar submission
        ]

        # Mock embeddings search
        mock_client.embeddings.search.return_value = [
            {
                "id": "sub-123",
                "score": 1.0,
                "metadata": {},
            },  # Self (will be filtered out)
            {
                "id": "sub-789",
                "score": 0.92,
                "metadata": {},
            },
            {
                "id": "sub-999",
                "score": 0.87,
                "metadata": {},
            },
        ]

        # Act
        result = await find_similar_submissions(
            zerodb_client=mock_client,
            submission_id="sub-123",
            top_k=10,
            similarity_threshold=0.5,
        )

        # Assert
        assert result["submission_id"] == "sub-123"
        assert len(result["similar_submissions"]) == 2
        assert result["total_found"] == 2

        # Verify first result
        first = result["similar_submissions"][0]
        assert first["submission_id"] == "sub-789"
        assert first["similarity_score"] == 0.92
        assert first["project_name"] == "ML Medical Diagnosis"

        # Verify second result
        second = result["similar_submissions"][1]
        assert second["submission_id"] == "sub-999"
        assert second["similarity_score"] == 0.87

        # Verify embeddings search was called correctly
        mock_client.embeddings.search.assert_called_once()
        call_args = mock_client.embeddings.search.call_args
        assert "AI Healthcare App" in call_args[1]["query"]
        assert "Machine learning for disease detection" in call_args[1]["query"]

    @pytest.mark.asyncio
    async def test_find_similar_submissions_not_found(self):
        """Should raise 404 when submission not found"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []  # Submission not found

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await find_similar_submissions(
                zerodb_client=mock_client,
                submission_id="nonexistent",
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_find_similar_submissions_same_hackathon_only(self):
        """Should filter to same hackathon when same_hackathon_only=True"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {
                "submission_id": "sub-123",
                "hackathon_id": "hack-456",
                "project_name": "Test Project",
                "description": "Test description",
            }
        ]
        mock_client.embeddings.search.return_value = []

        # Act
        await find_similar_submissions(
            zerodb_client=mock_client,
            submission_id="sub-123",
            same_hackathon_only=True,
        )

        # Assert
        call_args = mock_client.embeddings.search.call_args
        assert call_args[1]["namespace"] == "hackathons/hack-456/submissions"
        assert call_args[1]["filter"] == {"hackathon_id": "hack-456"}

    @pytest.mark.asyncio
    async def test_find_similar_submissions_global_search(self):
        """Should search globally when same_hackathon_only=False"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {
                "submission_id": "sub-123",
                "hackathon_id": "hack-456",
                "project_name": "Test Project",
                "description": "Test description",
            }
        ]
        mock_client.embeddings.search.return_value = []

        # Act
        await find_similar_submissions(
            zerodb_client=mock_client,
            submission_id="sub-123",
            same_hackathon_only=False,
        )

        # Assert
        call_args = mock_client.embeddings.search.call_args
        assert call_args[1]["namespace"] == "global/submissions"
        assert call_args[1]["filter"] == {}

    @pytest.mark.asyncio
    async def test_find_similar_submissions_excludes_self(self):
        """Should exclude the query submission from results"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = [
            [
                {
                    "submission_id": "sub-123",
                    "hackathon_id": "hack-456",
                    "project_name": "Test",
                    "description": "Test",
                }
            ],
            [
                {
                    "submission_id": "sub-456",
                    "team_id": "team-001",
                    "hackathon_id": "hack-456",
                    "project_name": "Similar",
                    "description": "Similar project",
                    "status": "SUBMITTED",
                    "created_at": "2024-01-01T00:00:00Z",
                }
            ],
        ]

        mock_client.embeddings.search.return_value = [
            {"id": "sub-123", "score": 1.0, "metadata": {}},  # Self
            {"id": "sub-456", "score": 0.9, "metadata": {}},  # Similar
        ]

        # Act
        result = await find_similar_submissions(
            zerodb_client=mock_client,
            submission_id="sub-123",
        )

        # Assert
        assert len(result["similar_submissions"]) == 1
        assert result["similar_submissions"][0]["submission_id"] == "sub-456"

    @pytest.mark.asyncio
    async def test_find_similar_submissions_respects_top_k(self):
        """Should return at most top_k results"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = [
            [
                {
                    "submission_id": "sub-123",
                    "hackathon_id": "hack-456",
                    "project_name": "Test",
                    "description": "Test",
                }
            ],
            [
                {
                    "submission_id": "sub-1",
                    "team_id": "team-001",
                    "hackathon_id": "hack-456",
                    "project_name": "Similar 1",
                    "description": "Similar",
                    "status": "SUBMITTED",
                    "created_at": "2024-01-01T00:00:00Z",
                }
            ],
            [
                {
                    "submission_id": "sub-2",
                    "team_id": "team-002",
                    "hackathon_id": "hack-456",
                    "project_name": "Similar 2",
                    "description": "Similar",
                    "status": "SUBMITTED",
                    "created_at": "2024-01-02T00:00:00Z",
                }
            ],
        ]

        # Return 3 results but request top_k=2
        mock_client.embeddings.search.return_value = [
            {"id": "sub-1", "score": 0.9, "metadata": {}},
            {"id": "sub-2", "score": 0.8, "metadata": {}},
            {"id": "sub-3", "score": 0.7, "metadata": {}},  # Should be cut off
        ]

        # Act
        result = await find_similar_submissions(
            zerodb_client=mock_client,
            submission_id="sub-123",
            top_k=2,
        )

        # Assert
        assert len(result["similar_submissions"]) == 2

    @pytest.mark.asyncio
    async def test_find_similar_submissions_timeout_error(self):
        """Should raise 504 when search times out"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {
                "submission_id": "sub-123",
                "hackathon_id": "hack-456",
                "project_name": "Test",
                "description": "Test",
            }
        ]
        mock_client.embeddings.search.side_effect = ZeroDBTimeoutError("Timeout")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await find_similar_submissions(
                zerodb_client=mock_client,
                submission_id="sub-123",
            )

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_find_similar_submissions_database_error(self):
        """Should raise 500 when database error occurs"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = ZeroDBError("Database error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await find_similar_submissions(
                zerodb_client=mock_client,
                submission_id="sub-123",
            )

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_find_similar_submissions_applies_threshold(self):
        """Should respect similarity threshold parameter"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {
                "submission_id": "sub-123",
                "hackathon_id": "hack-456",
                "project_name": "Test",
                "description": "Test",
            }
        ]
        mock_client.embeddings.search.return_value = []

        # Act
        await find_similar_submissions(
            zerodb_client=mock_client,
            submission_id="sub-123",
            similarity_threshold=0.75,
        )

        # Assert
        call_args = mock_client.embeddings.search.call_args
        assert call_args[1]["similarity_threshold"] == 0.75

    @pytest.mark.asyncio
    async def test_find_similar_submissions_includes_execution_time(self):
        """Should include execution time in results"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {
                "submission_id": "sub-123",
                "hackathon_id": "hack-456",
                "project_name": "Test",
                "description": "Test",
            }
        ]
        mock_client.embeddings.search.return_value = []

        # Act
        result = await find_similar_submissions(
            zerodb_client=mock_client,
            submission_id="sub-123",
        )

        # Assert
        assert "execution_time_ms" in result
        assert isinstance(result["execution_time_ms"], (int, float))
        assert result["execution_time_ms"] >= 0


class TestSimilarSubmissionsEndpoint:
    """Test similar submissions API endpoint"""

    @pytest.mark.asyncio
    async def test_similar_submissions_endpoint_integration(self):
        """Should handle GET /submissions/{id}/similar requests"""
        # Integration test placeholder
        # Would require full FastAPI test client setup
        pass

    @pytest.mark.asyncio
    async def test_similar_submissions_query_params_validation(self):
        """Should validate query parameters"""
        # Test that top_k is bounded (1-50)
        # Test that similarity_threshold is bounded (0.0-1.0)
        # Test that same_hackathon_only is boolean
        pass
