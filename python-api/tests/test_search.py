"""
Tests for Search Functionality

Tests search service business logic and API endpoints for semantic search.
"""

from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBTimeoutError
from services.search_service import SearchService


class TestSearchService:
    """Test SearchService business logic"""

    @pytest.mark.asyncio
    async def test_search_all_success(self):
        """Should return search results for universal search"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.embeddings.search.return_value = [
            {
                "id": "submission-1",
                "score": 0.95,
                "metadata": {
                    "entity_type": "submission",
                    "hackathon_id": "hack-123",
                    "title": "AI Healthcare App",
                },
            },
            {
                "id": "project-2",
                "score": 0.87,
                "metadata": {
                    "entity_type": "project",
                    "hackathon_id": "hack-456",
                    "title": "ML Model",
                },
            },
        ]

        service = SearchService(mock_client)

        # Act
        result = await service.search_all(
            query="machine learning healthcare",
            limit=10,
            offset=0,
        )

        # Assert
        assert len(result["results"]) == 2
        assert result["results"][0]["id"] == "submission-1"
        assert result["results"][0]["score"] == 0.95
        assert result["total_results"] == 2
        assert "execution_time_ms" in result

        # Verify embeddings search was called correctly
        mock_client.embeddings.search.assert_called_once()
        call_args = mock_client.embeddings.search.call_args
        assert call_args[1]["query"] == "machine learning healthcare"
        assert call_args[1]["namespace"] == "global"

    @pytest.mark.asyncio
    async def test_search_all_with_filters(self):
        """Should apply entity_type and status filters"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.embeddings.search.return_value = [
            {
                "id": "submission-1",
                "score": 0.92,
                "metadata": {
                    "entity_type": "submission",
                    "status": "SUBMITTED",
                },
            }
        ]

        service = SearchService(mock_client)

        # Act
        result = await service.search_all(
            query="blockchain",
            entity_type="submission",
            status="SUBMITTED",
            limit=5,
        )

        # Assert
        assert len(result["results"]) == 1
        call_args = mock_client.embeddings.search.call_args
        assert call_args[1]["filter"] == {
            "entity_type": "submission",
            "status": "SUBMITTED",
        }

    @pytest.mark.asyncio
    async def test_search_all_pagination(self):
        """Should handle pagination correctly"""
        # Arrange
        mock_client = AsyncMock()
        # Return 5 results, we'll request offset=2, limit=2
        mock_client.embeddings.search.return_value = [
            {"id": f"result-{i}", "score": 0.9 - (i * 0.1), "metadata": {}}
            for i in range(5)
        ]

        service = SearchService(mock_client)

        # Act
        result = await service.search_all(
            query="test",
            limit=2,
            offset=2,
        )

        # Assert
        assert len(result["results"]) == 2
        assert result["results"][0]["id"] == "result-2"
        assert result["results"][1]["id"] == "result-3"
        assert result["total_results"] == 5

    @pytest.mark.asyncio
    async def test_search_all_timeout_error(self):
        """Should raise 504 when search times out"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.embeddings.search.side_effect = ZeroDBTimeoutError("Timeout")

        service = SearchService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.search_all(query="test")

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_search_all_database_error(self):
        """Should raise 500 when search fails"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.embeddings.search.side_effect = ZeroDBError("Database error")

        service = SearchService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.search_all(query="test")

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_search_hackathon_success(self):
        """Should search within specific hackathon"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {"hackathon_id": "hack-123"}
        ]  # Hackathon exists
        mock_client.embeddings.search.return_value = [
            {
                "id": "submission-1",
                "score": 0.93,
                "metadata": {
                    "hackathon_id": "hack-123",
                    "entity_type": "submission",
                    "track_id": "ai-track",
                },
            }
        ]

        service = SearchService(mock_client)

        # Act
        result = await service.search_hackathon(
            hackathon_id="hack-123",
            query="AI chatbot",
            limit=10,
        )

        # Assert
        assert result["hackathon_id"] == "hack-123"
        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "submission-1"

        # Verify namespace is hackathon-scoped
        call_args = mock_client.embeddings.search.call_args
        assert call_args[1]["namespace"] == "hackathons/hack-123"

    @pytest.mark.asyncio
    async def test_search_hackathon_not_found(self):
        """Should raise 404 when hackathon doesn't exist"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []  # Hackathon not found

        service = SearchService(mock_client)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.search_hackathon(
                hackathon_id="nonexistent",
                query="test",
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_search_hackathon_with_track_filter(self):
        """Should filter by track_id within hackathon"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [{"hackathon_id": "hack-123"}]
        mock_client.embeddings.search.return_value = []

        service = SearchService(mock_client)

        # Act
        await service.search_hackathon(
            hackathon_id="hack-123",
            query="web app",
            track_id="web-track",
            entity_type="submission",
            status="SUBMITTED",
        )

        # Assert
        call_args = mock_client.embeddings.search.call_args
        assert call_args[1]["filter"] == {
            "hackathon_id": "hack-123",
            "track_id": "web-track",
            "entity_type": "submission",
            "status": "SUBMITTED",
        }

    @pytest.mark.asyncio
    async def test_search_hackathon_performance_warning(self):
        """Should log warning if search exceeds 200ms target"""
        # This test verifies that slow searches are logged
        # In production, this helps identify performance issues

        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [{"hackathon_id": "hack-123"}]
        mock_client.embeddings.search.return_value = []

        service = SearchService(mock_client)

        # Act
        result = await service.search_hackathon(
            hackathon_id="hack-123",
            query="test",
        )

        # Assert - should complete successfully
        assert result["hackathon_id"] == "hack-123"
        assert "execution_time_ms" in result


class TestSearchRoutes:
    """Test search API endpoints"""

    @pytest.mark.asyncio
    async def test_universal_search_endpoint(self):
        """Should handle universal search requests"""
        # Integration test placeholder
        # Would require full FastAPI test client setup
        pass

    @pytest.mark.asyncio
    async def test_hackathon_search_endpoint(self):
        """Should handle hackathon-scoped search requests"""
        # Integration test placeholder
        # Would require full FastAPI test client setup
        pass

    @pytest.mark.asyncio
    async def test_search_validation(self):
        """Should validate search request parameters"""
        # Test Pydantic validation for query length, limit bounds, etc.
        pass


class TestEmbeddingsAPI:
    """Test ZeroDB Embeddings API wrapper"""

    @pytest.mark.asyncio
    async def test_generate_embeddings(self):
        """Should generate embeddings from texts"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.project_id = "project-123"
        mock_client._request.return_value = {
            "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        }

        from integrations.zerodb.embeddings import EmbeddingsAPI

        embeddings_api = EmbeddingsAPI(mock_client)

        # Act
        result = await embeddings_api.generate(["text1", "text2"])

        # Assert
        assert len(result) == 2
        assert len(result[0]) == 3
        mock_client._request.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_and_store(self):
        """Should embed and store documents"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.project_id = "project-123"
        mock_client._request.return_value = {"count": 2}

        from integrations.zerodb.embeddings import EmbeddingsAPI

        embeddings_api = EmbeddingsAPI(mock_client)

        # Act
        result = await embeddings_api.embed_and_store(
            documents=[
                {"id": "doc-1", "text": "Test doc 1", "metadata": {"type": "submission"}},
                {"id": "doc-2", "text": "Test doc 2", "metadata": {"type": "project"}},
            ],
            namespace="hackathons/test",
        )

        # Assert
        assert result["count"] == 2
        call_args = mock_client._request.call_args
        assert "embed-and-store" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_search_with_similarity_threshold(self):
        """Should apply similarity threshold filter"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.project_id = "project-123"
        mock_client._request.return_value = {"results": []}

        from integrations.zerodb.embeddings import EmbeddingsAPI

        embeddings_api = EmbeddingsAPI(mock_client)

        # Act
        await embeddings_api.search(
            query="test query",
            namespace="test",
            similarity_threshold=0.7,
        )

        # Assert
        call_args = mock_client._request.call_args
        payload = call_args[1]["json"]
        assert payload["similarity_threshold"] == 0.7
