"""
Tests for Search Service

Comprehensive tests for semantic search functionality including:
- Universal search (search_all)
- Hackathon-scoped search (search_hackathon)
- Filtering (entity_type, status, track)
- Pagination
- Performance (< 200ms target)
- Error handling
- Edge cases
"""

from time import time
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest
from fastapi import HTTPException
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)
from api.schemas.search import SearchResult, SearchResultMetadata, SearchResponse, HackathonSearchResponse
from services.search_service import SearchService


class TestSearchResult:
    """Test SearchResult Pydantic model"""

    def test_search_result_creation(self):
        """Should create SearchResult with all fields"""
        # Arrange & Act
        result = SearchResult(
            id="sub-123",
            score=0.92,
            metadata=SearchResultMetadata(
                entity_type="submission",
                hackathon_id="hack-456",
                track_id="ai-ml",
                status="SUBMITTED",
                title="AI Assistant",
                description="An intelligent coding assistant",
            ),
        )

        # Assert
        assert result.id == "sub-123"
        assert result.score == 0.92
        assert result.metadata.entity_type == "submission"
        assert result.metadata.hackathon_id == "hack-456"
        assert result.metadata.title == "AI Assistant"
        assert result.metadata.description == "An intelligent coding assistant"
        assert result.metadata.track_id == "ai-ml"
        assert result.metadata.status == "SUBMITTED"

    def test_search_result_to_dict(self):
        """Should convert SearchResult to dictionary via model_dump"""
        # Arrange
        result = SearchResult(
            id="sub-123",
            score=0.85,
            metadata=SearchResultMetadata(
                entity_type="submission",
                hackathon_id="hack-456",
                track_id="ai-ml",
                title="AI Assistant",
                description="A helpful tool",
            ),
        )

        # Act
        result_dict = result.model_dump()

        # Assert
        assert result_dict["id"] == "sub-123"
        assert result_dict["score"] == 0.85
        assert result_dict["metadata"]["hackathon_id"] == "hack-456"
        assert result_dict["metadata"]["title"] == "AI Assistant"


class TestSearchServiceInitialization:
    """Test SearchService initialization"""

    def test_service_initialization(self):
        """Should initialize with zerodb client"""
        # Arrange
        mock_client = AsyncMock()

        # Act
        service = SearchService(mock_client)

        # Assert
        assert service.zerodb == mock_client

    def test_service_initialization_stores_client(self):
        """Should store zerodb_client as self.zerodb"""
        # Arrange
        mock_client = AsyncMock()

        # Act
        service = SearchService(mock_client)

        # Assert
        assert service.zerodb is mock_client


class TestSearchAll:
    """Test search_all() method"""

    @pytest.mark.asyncio
    async def test_search_all_success(self):
        """Should return search results for valid query"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        # Mock embeddings.search results
        mock_client.embeddings.search.return_value = [
            {
                "id": "sub-123",
                "score": 0.92,
                "metadata": {
                    "entity_type": "submission",
                    "hackathon_id": "hack-456",
                    "title": "AI Healthcare",
                    "description": "AI-powered healthcare solution",
                    "track_id": "ai-ml",
                    "status": "SUBMITTED",
                },
            },
            {
                "id": "sub-456",
                "score": 0.85,
                "metadata": {
                    "entity_type": "submission",
                    "hackathon_id": "hack-456",
                    "title": "Medical AI",
                    "description": "AI for medical diagnosis",
                    "track_id": "ai-ml",
                    "status": "SUBMITTED",
                },
            },
        ]

        # Act
        result = await service.search_all(
            query="AI healthcare solutions",
            limit=10,
        )

        # Assert
        assert len(result["results"]) == 2
        assert result["results"][0]["id"] == "sub-123"
        assert result["results"][0]["score"] == 0.92
        assert result["results"][1]["id"] == "sub-456"
        assert result["results"][1]["score"] == 0.85
        assert result["total_results"] == 2
        assert "execution_time_ms" in result

        # Verify embeddings.search was called
        mock_client.embeddings.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_all_with_entity_type_filter(self):
        """Should apply entity_type filter to search"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.embeddings.search.return_value = []

        # Act
        await service.search_all(
            query="test query",
            entity_type="submission",
            limit=10,
        )

        # Assert
        call_args = mock_client.embeddings.search.call_args
        assert call_args.kwargs["filter"]["entity_type"] == "submission"

    @pytest.mark.asyncio
    async def test_search_all_with_status_filter(self):
        """Should apply status filter to search"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.embeddings.search.return_value = []

        # Act
        await service.search_all(
            query="test query",
            status="SUBMITTED",
            limit=10,
        )

        # Assert
        call_args = mock_client.embeddings.search.call_args
        assert call_args.kwargs["filter"]["status"] == "SUBMITTED"

    @pytest.mark.asyncio
    async def test_search_all_with_similarity_threshold(self):
        """Should pass similarity_threshold to search"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.embeddings.search.return_value = []

        # Act
        await service.search_all(
            query="test",
            similarity_threshold=0.7,
        )

        # Assert
        call_args = mock_client.embeddings.search.call_args
        assert call_args.kwargs["similarity_threshold"] == 0.7

    @pytest.mark.asyncio
    async def test_search_all_no_filters(self):
        """Should pass None filter when no entity_type or status"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.embeddings.search.return_value = []

        # Act
        await service.search_all(query="test")

        # Assert
        call_args = mock_client.embeddings.search.call_args
        assert call_args.kwargs["filter"] is None

    @pytest.mark.asyncio
    async def test_search_all_handles_timeout(self):
        """Should raise HTTPException 504 on timeout"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.search.side_effect = ZeroDBTimeoutError(
            "Request timed out"
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.search_all(query="test")
        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_search_all_handles_zerodb_error(self):
        """Should raise HTTPException 500 on ZeroDBError"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.search.side_effect = ZeroDBError("API error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.search_all(query="test")
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_search_all_performance(self):
        """Should complete search in under 200ms (target)"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.search.return_value = [
            {
                "id": "sub-1",
                "score": 0.9,
                "metadata": {
                    "entity_type": "submission",
                    "hackathon_id": "hack-1",
                    "title": "Test",
                    "description": "Test project",
                },
            }
        ]

        # Act
        start = time()
        await service.search_all(query="test query")
        elapsed = (time() - start) * 1000

        # Assert (allow for some overhead in mock calls)
        assert elapsed < 200, f"Search took {elapsed}ms (target: <200ms)"

    @pytest.mark.asyncio
    async def test_search_all_returns_dicts(self):
        """Should return dict with results list"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.embeddings.search.return_value = [
            {
                "id": "sub-123",
                "score": 0.9,
                "metadata": {
                    "entity_type": "submission",
                    "hackathon_id": "hack-456",
                    "title": "Test Project",
                    "description": "A test",
                },
            }
        ]
        service = SearchService(mock_client)

        # Act
        result = await service.search_all(query="test", limit=10)

        # Assert
        assert len(result["results"]) == 1
        assert isinstance(result["results"][0], dict)
        assert result["results"][0]["id"] == "sub-123"
        assert result["results"][0]["score"] == 0.9


class TestSearchHackathon:
    """Test search_hackathon() method"""

    @pytest.mark.asyncio
    async def test_search_hackathon_success(self):
        """Should return search results scoped to a hackathon"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        # Mock hackathon existence check
        mock_client.tables.query_rows.return_value = [
            {"hackathon_id": "hack-456", "name": "Test Hackathon"}
        ]

        # Mock embeddings.search results
        mock_client.embeddings.search.return_value = [
            {
                "id": "sub-123",
                "score": 0.92,
                "metadata": {
                    "entity_type": "submission",
                    "hackathon_id": "hack-456",
                    "title": "AI Healthcare",
                    "description": "AI-powered healthcare solution",
                },
            },
            {
                "id": "sub-456",
                "score": 0.85,
                "metadata": {
                    "entity_type": "submission",
                    "hackathon_id": "hack-456",
                    "title": "Medical AI",
                    "description": "AI for medical diagnosis",
                },
            },
        ]

        # Act
        result = await service.search_hackathon(
            hackathon_id="hack-456",
            query="AI healthcare solutions",
            limit=10,
        )

        # Assert
        assert len(result["results"]) == 2
        assert result["results"][0]["id"] == "sub-123"
        assert result["results"][0]["score"] == 0.92
        assert result["results"][1]["id"] == "sub-456"
        assert result["results"][1]["score"] == 0.85
        assert result["hackathon_id"] == "hack-456"
        assert result["total_results"] == 2
        assert "execution_time_ms" in result

    @pytest.mark.asyncio
    async def test_search_hackathon_with_entity_type_filter(self):
        """Should apply entity_type filter"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.tables.query_rows.return_value = [{"hackathon_id": "hack-123"}]
        mock_client.embeddings.search.return_value = []

        # Act
        await service.search_hackathon(
            hackathon_id="hack-123",
            query="test",
            entity_type="submission",
        )

        # Assert
        call_args = mock_client.embeddings.search.call_args
        assert call_args.kwargs["filter"]["entity_type"] == "submission"
        assert call_args.kwargs["filter"]["hackathon_id"] == "hack-123"

    @pytest.mark.asyncio
    async def test_search_hackathon_with_track_filter(self):
        """Should apply track_id filter"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.tables.query_rows.return_value = [{"hackathon_id": "hack-123"}]
        mock_client.embeddings.search.return_value = []

        # Act
        await service.search_hackathon(
            hackathon_id="hack-123",
            query="test",
            track_id="ai-ml",
        )

        # Assert
        call_args = mock_client.embeddings.search.call_args
        assert call_args.kwargs["filter"]["track_id"] == "ai-ml"

    @pytest.mark.asyncio
    async def test_search_hackathon_with_status_filter(self):
        """Should apply status filter"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.tables.query_rows.return_value = [{"hackathon_id": "hack-123"}]
        mock_client.embeddings.search.return_value = []

        # Act
        await service.search_hackathon(
            hackathon_id="hack-123",
            query="test",
            status="SUBMITTED",
        )

        # Assert
        call_args = mock_client.embeddings.search.call_args
        assert call_args.kwargs["filter"]["status"] == "SUBMITTED"

    @pytest.mark.asyncio
    async def test_search_hackathon_not_found(self):
        """Should raise HTTPException 404 if hackathon does not exist"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.tables.query_rows.return_value = []  # No hackathon found

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.search_hackathon(
                hackathon_id="nonexistent",
                query="test",
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_search_hackathon_handles_timeout(self):
        """Should raise HTTPException 504 on timeout"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.tables.query_rows.return_value = [{"hackathon_id": "hack-123"}]
        mock_client.embeddings.search.side_effect = ZeroDBTimeoutError(
            "Request timed out"
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.search_hackathon(
                hackathon_id="hack-123",
                query="test",
            )
        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_search_hackathon_handles_zerodb_error(self):
        """Should raise HTTPException 500 on ZeroDBError"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.tables.query_rows.return_value = [{"hackathon_id": "hack-123"}]
        mock_client.embeddings.search.side_effect = ZeroDBError("API error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.search_hackathon(
                hackathon_id="hack-123",
                query="test",
            )
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_search_hackathon_uses_scoped_namespace(self):
        """Should use hackathon-scoped namespace for search"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.tables.query_rows.return_value = [{"hackathon_id": "hack-456"}]
        mock_client.embeddings.search.return_value = []

        # Act
        await service.search_hackathon(
            hackathon_id="hack-456",
            query="test",
        )

        # Assert
        call_args = mock_client.embeddings.search.call_args
        assert call_args.kwargs["namespace"] == "hackathons/hack-456"

    @pytest.mark.asyncio
    async def test_search_hackathon_similarity_threshold(self):
        """Should pass similarity_threshold to search"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.tables.query_rows.return_value = [{"hackathon_id": "hack-123"}]
        mock_client.embeddings.search.return_value = []

        # Act
        await service.search_hackathon(
            hackathon_id="hack-123",
            query="test",
            similarity_threshold=0.8,
        )

        # Assert
        call_args = mock_client.embeddings.search.call_args
        assert call_args.kwargs["similarity_threshold"] == 0.8


class TestSearchAllPagination:
    """Test pagination in search_all()"""

    @pytest.mark.asyncio
    async def test_pagination_with_offset(self):
        """Should apply offset for pagination"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        # Mock 15 results
        mock_client.embeddings.search.return_value = [
            {
                "id": f"sub-{i}",
                "score": 0.9 - (i * 0.01),
                "metadata": {
                    "entity_type": "submission",
                    "hackathon_id": "hack-123",
                    "title": f"Project {i}",
                    "description": f"Description {i}",
                },
            }
            for i in range(15)
        ]

        # Act - get first page (offset=0, limit=10)
        result = await service.search_all(
            query="test",
            limit=10,
            offset=0,
        )

        # Assert
        assert len(result["results"]) == 10
        assert result["total_results"] == 15
        assert result["results"][0]["id"] == "sub-0"

    @pytest.mark.asyncio
    async def test_pagination_second_page(self):
        """Should return second page of results with offset"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        # Mock 15 results
        mock_client.embeddings.search.return_value = [
            {
                "id": f"sub-{i}",
                "score": 0.9 - (i * 0.01),
                "metadata": {
                    "entity_type": "submission",
                    "hackathon_id": "hack-123",
                    "title": f"Project {i}",
                    "description": f"Description {i}",
                },
            }
            for i in range(15)
        ]

        # Act - get second page (offset=10, limit=10)
        result = await service.search_all(
            query="test",
            limit=10,
            offset=10,
        )

        # Assert
        assert len(result["results"]) == 5  # Only 5 results on page 2
        assert result["results"][0]["id"] == "sub-10"


class TestSearchHackathonPagination:
    """Test pagination in search_hackathon()"""

    @pytest.mark.asyncio
    async def test_hackathon_search_pagination(self):
        """Should apply pagination to hackathon search results"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.tables.query_rows.return_value = [{"hackathon_id": "hack-123"}]

        # Mock 15 results
        mock_client.embeddings.search.return_value = [
            {
                "id": f"sub-{i}",
                "score": 0.9 - (i * 0.01),
                "metadata": {
                    "entity_type": "submission",
                    "hackathon_id": "hack-123",
                    "title": f"Project {i}",
                    "description": f"Description {i}",
                },
            }
            for i in range(15)
        ]

        # Act
        result = await service.search_hackathon(
            hackathon_id="hack-123",
            query="test",
            limit=10,
            offset=0,
        )

        # Assert
        assert len(result["results"]) == 10
        assert result["total_results"] == 15
        assert result["hackathon_id"] == "hack-123"


class TestSearchResultTransformation:
    """Test result transformation in search methods"""

    @pytest.mark.asyncio
    async def test_results_transformed_to_dicts(self):
        """Should transform raw ZeroDB results to dict format"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.search.return_value = [
            {
                "id": "sub-123",
                "score": 0.92,
                "metadata": {
                    "entity_type": "submission",
                    "hackathon_id": "hack-456",
                    "title": "AI Project",
                    "description": "An AI solution",
                    "track_id": "ai-ml",
                },
            }
        ]

        # Act
        result = await service.search_all(query="test")

        # Assert
        assert len(result["results"]) == 1
        assert isinstance(result["results"][0], dict)
        assert result["results"][0]["id"] == "sub-123"
        assert result["results"][0]["score"] == 0.92
        assert result["results"][0]["metadata"]["entity_type"] == "submission"

    @pytest.mark.asyncio
    async def test_results_handle_missing_metadata(self):
        """Should handle results with empty metadata"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.search.return_value = [
            {
                "id": "sub-123",
                "score": 0.85,
                # Missing metadata key
            }
        ]

        # Act
        result = await service.search_all(query="test")

        # Assert
        assert len(result["results"]) == 1
        assert result["results"][0]["metadata"] == {}

    @pytest.mark.asyncio
    async def test_results_handle_missing_score(self):
        """Should default score to 0.0 when missing"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.search.return_value = [
            {
                "id": "sub-123",
                # Missing score
                "metadata": {"entity_type": "submission"},
            }
        ]

        # Act
        result = await service.search_all(query="test")

        # Assert
        assert result["results"][0]["score"] == 0.0


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_search_with_no_results(self):
        """Should handle empty search results gracefully"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.embeddings.search.return_value = []

        # Act
        result = await service.search_all(query="nonexistent query")

        # Assert
        assert result["results"] == []
        assert result["total_results"] == 0

    @pytest.mark.asyncio
    async def test_search_with_special_characters_in_query(self):
        """Should handle special characters in query"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.embeddings.search.return_value = []

        # Act
        result = await service.search_all(
            query="C++ & Python projects with $ symbols!",
        )

        # Assert - should not raise error
        assert isinstance(result, dict)
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_search_hackathon_with_no_results(self):
        """Should handle empty hackathon search results gracefully"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.tables.query_rows.return_value = [{"hackathon_id": "hack-123"}]
        mock_client.embeddings.search.return_value = []

        # Act
        result = await service.search_hackathon(
            hackathon_id="hack-123",
            query="nonexistent",
        )

        # Assert
        assert result["results"] == []
        assert result["total_results"] == 0
        assert result["hackathon_id"] == "hack-123"

    @pytest.mark.asyncio
    async def test_search_all_uses_global_namespace(self):
        """Should use 'global' namespace for universal search"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.embeddings.search.return_value = []

        # Act
        await service.search_all(query="test")

        # Assert
        call_args = mock_client.embeddings.search.call_args
        assert call_args.kwargs["namespace"] == "global"

    @pytest.mark.asyncio
    async def test_search_all_includes_metadata_flag(self):
        """Should request include_metadata=True"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.embeddings.search.return_value = []

        # Act
        await service.search_all(query="test")

        # Assert
        call_args = mock_client.embeddings.search.call_args
        assert call_args.kwargs["include_metadata"] is True

    @pytest.mark.asyncio
    async def test_search_all_top_k_accounts_for_offset(self):
        """Should request top_k = limit + offset for pagination"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)
        mock_client.embeddings.search.return_value = []

        # Act
        await service.search_all(query="test", limit=10, offset=5)

        # Assert
        call_args = mock_client.embeddings.search.call_args
        assert call_args.kwargs["top_k"] == 15  # 10 + 5


class TestSearchResponseModels:
    """Test SearchResponse and HackathonSearchResponse models"""

    def test_search_response_creation(self):
        """Should create SearchResponse with all fields"""
        # Arrange & Act
        response = SearchResponse(
            query="test query",
            total_results=2,
            results=[
                SearchResult(
                    id="sub-1",
                    score=0.9,
                    metadata=SearchResultMetadata(entity_type="submission"),
                ),
                SearchResult(
                    id="sub-2",
                    score=0.8,
                    metadata=SearchResultMetadata(entity_type="submission"),
                ),
            ],
            limit=10,
            offset=0,
            has_more=False,
            execution_time_ms=45.2,
        )

        # Assert
        assert response.query == "test query"
        assert response.total_results == 2
        assert len(response.results) == 2
        assert response.limit == 10
        assert response.offset == 0
        assert response.has_more is False
        assert response.execution_time_ms == 45.2

    def test_hackathon_search_response_creation(self):
        """Should create HackathonSearchResponse with hackathon_id"""
        # Arrange & Act
        response = HackathonSearchResponse(
            query="test",
            total_results=1,
            results=[
                SearchResult(
                    id="sub-1",
                    score=0.95,
                    metadata=SearchResultMetadata(
                        entity_type="submission",
                        hackathon_id="hack-456",
                    ),
                ),
            ],
            limit=10,
            offset=0,
            has_more=False,
            hackathon_id="hack-456",
        )

        # Assert
        assert response.hackathon_id == "hack-456"
        assert response.results[0].metadata.hackathon_id == "hack-456"

    def test_search_result_metadata_optional_fields(self):
        """Should allow optional fields to be None"""
        # Arrange & Act
        metadata = SearchResultMetadata(entity_type="submission")

        # Assert
        assert metadata.entity_type == "submission"
        assert metadata.hackathon_id is None
        assert metadata.track_id is None
        assert metadata.team_id is None
        assert metadata.status is None
        assert metadata.title is None
        assert metadata.description is None
        assert metadata.tags is None
        assert metadata.submitted_at is None
        assert metadata.created_at is None
