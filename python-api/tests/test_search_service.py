"""
Tests for Search Service

Comprehensive tests for semantic search functionality including:
- Natural language search
- Similar submissions search
- Filtering (hackathon, track, status)
- Ranking by similarity
- Performance (< 200ms target)
- Error handling
- Edge cases
"""

import uuid
from datetime import datetime
from time import time
from unittest.mock import AsyncMock, patch

import pytest
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)
from services.search_service import (
    SearchResult,
    SearchService,
    quick_search,
)


class TestSearchResult:
    """Test SearchResult dataclass"""

    def test_search_result_creation(self):
        """Should create SearchResult with all fields"""
        # Arrange & Act
        result = SearchResult(
            submission_id="sub-123",
            hackathon_id="hack-456",
            title="AI Assistant",
            description="An intelligent coding assistant",
            similarity_score=0.92,
            metadata={"track_id": "ai-ml", "status": "SUBMITTED"}
        )

        # Assert
        assert result.submission_id == "sub-123"
        assert result.hackathon_id == "hack-456"
        assert result.title == "AI Assistant"
        assert result.description == "An intelligent coding assistant"
        assert result.similarity_score == 0.92
        assert result.metadata["track_id"] == "ai-ml"

    def test_search_result_to_dict(self):
        """Should convert SearchResult to dictionary"""
        # Arrange
        result = SearchResult(
            submission_id="sub-123",
            hackathon_id="hack-456",
            title="AI Assistant",
            description="A helpful tool",
            similarity_score=0.85,
            metadata={"track_id": "ai-ml"}
        )

        # Act
        result_dict = result.to_dict()

        # Assert
        assert result_dict["submission_id"] == "sub-123"
        assert result_dict["hackathon_id"] == "hack-456"
        assert result_dict["title"] == "AI Assistant"
        assert result_dict["similarity_score"] == 0.85


class TestSearchServiceInitialization:
    """Test SearchService initialization"""

    def test_service_initialization_default_model(self):
        """Should initialize with default embedding model"""
        # Arrange
        mock_client = AsyncMock()

        # Act
        service = SearchService(mock_client)

        # Assert
        assert service.client == mock_client
        assert service.model == "BAAI/bge-small-en-v1.5"

    def test_service_initialization_custom_model(self):
        """Should initialize with custom embedding model"""
        # Arrange
        mock_client = AsyncMock()
        custom_model = "custom-model-v1"

        # Act
        service = SearchService(mock_client, model=custom_model)

        # Assert
        assert service.model == custom_model


class TestSearchByQuery:
    """Test search_by_query() function"""

    @pytest.mark.asyncio
    async def test_search_by_query_success(self):
        """Should return search results for valid query"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        # Mock embedding generation
        mock_client.embeddings.generate.return_value = {
            "embedding": [0.1] * 384,  # 384-dimensional embedding
            "model": "BAAI/bge-small-en-v1.5"
        }

        # Mock vector search results
        mock_client.vectors.search.return_value = [
            {
                "vector_id": "sub-123",
                "similarity": 0.92,
                "metadata": {
                    "submission_id": "sub-123",
                    "hackathon_id": "hack-456",
                    "project_name": "AI Healthcare",
                    "description": "AI-powered healthcare solution",
                    "track_id": "ai-ml",
                    "status": "SUBMITTED"
                }
            },
            {
                "vector_id": "sub-456",
                "similarity": 0.85,
                "metadata": {
                    "submission_id": "sub-456",
                    "hackathon_id": "hack-456",
                    "project_name": "Medical AI",
                    "description": "AI for medical diagnosis",
                    "track_id": "ai-ml",
                    "status": "SUBMITTED"
                }
            }
        ]

        # Act
        results = await service.search_by_query(
            query="AI healthcare solutions",
            hackathon_id="hack-456",
            top_k=10
        )

        # Assert
        assert len(results) == 2
        assert results[0].submission_id == "sub-123"
        assert results[0].similarity_score == 0.92
        assert results[0].title == "AI Healthcare"
        assert results[1].submission_id == "sub-456"
        assert results[1].similarity_score == 0.85

        # Verify embedding was generated
        mock_client.embeddings.generate.assert_called_once_with(
            text="AI healthcare solutions",
            model="BAAI/bge-small-en-v1.5"
        )

        # Verify vector search was called
        mock_client.vectors.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_by_query_with_filters(self):
        """Should apply filters to search"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.generate.return_value = {
            "embedding": [0.1] * 384
        }
        mock_client.vectors.search.return_value = []

        filters = {"track_id": "ai-ml", "status": "SUBMITTED"}

        # Act
        await service.search_by_query(
            query="test query",
            hackathon_id="hack-123",
            top_k=10,
            filters=filters
        )

        # Assert
        call_args = mock_client.vectors.search.call_args
        assert call_args.kwargs["filter"]["track_id"] == "ai-ml"
        assert call_args.kwargs["filter"]["status"] == "SUBMITTED"
        assert call_args.kwargs["filter"]["hackathon_id"] == "hack-123"

    @pytest.mark.asyncio
    async def test_search_by_query_with_min_similarity(self):
        """Should respect minimum similarity threshold"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.generate.return_value = {
            "embedding": [0.1] * 384
        }
        mock_client.vectors.search.return_value = []

        # Act
        await service.search_by_query(
            query="test",
            hackathon_id="hack-123",
            min_similarity=0.7
        )

        # Assert
        call_args = mock_client.vectors.search.call_args
        assert call_args.kwargs["similarity_threshold"] == 0.7

    @pytest.mark.asyncio
    async def test_search_by_query_empty_query_raises_error(self):
        """Should raise ValueError for empty query"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await service.search_by_query(
                query="",
                hackathon_id="hack-123"
            )
        assert "query cannot be empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_search_by_query_invalid_top_k_raises_error(self):
        """Should raise ValueError for invalid top_k"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        # Act & Assert - top_k too small
        with pytest.raises(ValueError) as exc_info:
            await service.search_by_query(
                query="test",
                hackathon_id="hack-123",
                top_k=0
            )
        assert "top_k" in str(exc_info.value).lower()

        # Act & Assert - top_k too large
        with pytest.raises(ValueError) as exc_info:
            await service.search_by_query(
                query="test",
                hackathon_id="hack-123",
                top_k=100
            )
        assert "top_k" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_search_by_query_invalid_similarity_raises_error(self):
        """Should raise ValueError for invalid min_similarity"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        # Act & Assert - negative similarity
        with pytest.raises(ValueError) as exc_info:
            await service.search_by_query(
                query="test",
                hackathon_id="hack-123",
                min_similarity=-0.1
            )
        assert "similarity" in str(exc_info.value).lower()

        # Act & Assert - similarity > 1.0
        with pytest.raises(ValueError) as exc_info:
            await service.search_by_query(
                query="test",
                hackathon_id="hack-123",
                min_similarity=1.5
            )
        assert "similarity" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_search_by_query_handles_timeout(self):
        """Should handle timeout errors gracefully"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.generate.side_effect = ZeroDBTimeoutError(
            "Request timed out"
        )

        # Act & Assert
        with pytest.raises(ZeroDBError) as exc_info:
            await service.search_by_query(
                query="test",
                hackathon_id="hack-123"
            )
        assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_search_by_query_handles_zerodb_error(self):
        """Should propagate ZeroDB errors"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.generate.side_effect = ZeroDBError(
            "API error"
        )

        # Act & Assert
        with pytest.raises(ZeroDBError):
            await service.search_by_query(
                query="test",
                hackathon_id="hack-123"
            )

    @pytest.mark.asyncio
    async def test_search_by_query_performance(self):
        """Should complete search in under 200ms (target)"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        # Simulate fast responses
        mock_client.embeddings.generate.return_value = {
            "embedding": [0.1] * 384
        }
        mock_client.vectors.search.return_value = [
            {
                "vector_id": "sub-1",
                "similarity": 0.9,
                "metadata": {
                    "submission_id": "sub-1",
                    "hackathon_id": "hack-1",
                    "project_name": "Test",
                    "description": "Test project"
                }
            }
        ]

        # Act
        start = time()
        await service.search_by_query(
            query="test query",
            hackathon_id="hack-123"
        )
        elapsed = (time() - start) * 1000  # Convert to ms

        # Assert (allow for some overhead in mock calls)
        assert elapsed < 200, f"Search took {elapsed}ms (target: <200ms)"


class TestFindSimilarSubmissions:
    """Test find_similar_submissions() function"""

    @pytest.mark.asyncio
    async def test_find_similar_success(self):
        """Should find similar submissions successfully"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        # Mock vector.get for reference submission
        mock_client.vectors.get.return_value = {
            "vector_id": "sub-123",
            "embedding": [0.5] * 384,
            "metadata": {
                "submission_id": "sub-123",
                "project_name": "Original Project"
            }
        }

        # Mock vector search results (includes self + similar)
        mock_client.vectors.search.return_value = [
            {
                "vector_id": "sub-123",
                "similarity": 1.0,  # Perfect match (self)
                "metadata": {
                    "submission_id": "sub-123",
                    "hackathon_id": "hack-456",
                    "project_name": "Original Project",
                    "description": "Original"
                }
            },
            {
                "vector_id": "sub-456",
                "similarity": 0.88,
                "metadata": {
                    "submission_id": "sub-456",
                    "hackathon_id": "hack-456",
                    "project_name": "Similar Project 1",
                    "description": "Very similar"
                }
            },
            {
                "vector_id": "sub-789",
                "similarity": 0.75,
                "metadata": {
                    "submission_id": "sub-789",
                    "hackathon_id": "hack-456",
                    "project_name": "Similar Project 2",
                    "description": "Somewhat similar"
                }
            }
        ]

        # Act
        results = await service.find_similar_submissions(
            submission_id="sub-123",
            hackathon_id="hack-456",
            top_k=10
        )

        # Assert - should exclude the reference submission
        assert len(results) == 2
        assert results[0].submission_id == "sub-456"
        assert results[0].similarity_score == 0.88
        assert results[1].submission_id == "sub-789"
        assert results[1].similarity_score == 0.75

        # Verify get was called
        mock_client.vectors.get.assert_called_once_with(
            vector_id="sub-123",
            namespace="hackathons/hack-456/submissions"
        )

    @pytest.mark.asyncio
    async def test_find_similar_with_filters(self):
        """Should apply filters when finding similar submissions"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.vectors.get.return_value = {
            "embedding": [0.5] * 384
        }
        mock_client.vectors.search.return_value = []

        filters = {"track_id": "blockchain", "status": "SUBMITTED"}

        # Act
        await service.find_similar_submissions(
            submission_id="sub-123",
            hackathon_id="hack-456",
            filters=filters
        )

        # Assert
        call_args = mock_client.vectors.search.call_args
        assert call_args.kwargs["filter"]["track_id"] == "blockchain"
        assert call_args.kwargs["filter"]["status"] == "SUBMITTED"

    @pytest.mark.asyncio
    async def test_find_similar_empty_submission_id_raises_error(self):
        """Should raise ValueError for empty submission_id"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await service.find_similar_submissions(
                submission_id="",
                hackathon_id="hack-123"
            )
        assert "submission_id" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_find_similar_submission_not_found(self):
        """Should raise ZeroDBNotFound if reference submission not found"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.vectors.get.side_effect = ZeroDBNotFound(
            "Vector not found"
        )

        # Act & Assert
        with pytest.raises(ZeroDBNotFound):
            await service.find_similar_submissions(
                submission_id="nonexistent",
                hackathon_id="hack-123"
            )

    @pytest.mark.asyncio
    async def test_find_similar_no_embedding_raises_error(self):
        """Should raise error if embedding is missing"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        # Return response without embedding
        mock_client.vectors.get.return_value = {
            "vector_id": "sub-123",
            "metadata": {}
        }

        # Act & Assert
        with pytest.raises(ZeroDBNotFound) as exc_info:
            await service.find_similar_submissions(
                submission_id="sub-123",
                hackathon_id="hack-456"
            )
        assert "embedding not found" in str(exc_info.value).lower()


class TestSearchWithPagination:
    """Test search_with_pagination() function"""

    @pytest.mark.asyncio
    async def test_pagination_first_page(self):
        """Should return first page of results"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.generate.return_value = {
            "embedding": [0.1] * 384
        }

        # Mock 15 results
        mock_client.vectors.search.return_value = [
            {
                "vector_id": f"sub-{i}",
                "similarity": 0.9 - (i * 0.01),
                "metadata": {
                    "submission_id": f"sub-{i}",
                    "hackathon_id": "hack-123",
                    "project_name": f"Project {i}",
                    "description": f"Description {i}"
                }
            }
            for i in range(15)
        ]

        # Act
        result = await service.search_with_pagination(
            query="test",
            hackathon_id="hack-123",
            page=1,
            page_size=10
        )

        # Assert
        assert len(result["results"]) == 10
        assert result["page"] == 1
        assert result["page_size"] == 10
        assert result["total"] == 15
        assert result["has_more"] is True
        assert result["results"][0].submission_id == "sub-0"

    @pytest.mark.asyncio
    async def test_pagination_second_page(self):
        """Should return second page of results"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.generate.return_value = {
            "embedding": [0.1] * 384
        }

        # Mock 15 results
        mock_client.vectors.search.return_value = [
            {
                "vector_id": f"sub-{i}",
                "similarity": 0.9 - (i * 0.01),
                "metadata": {
                    "submission_id": f"sub-{i}",
                    "hackathon_id": "hack-123",
                    "project_name": f"Project {i}",
                    "description": f"Description {i}"
                }
            }
            for i in range(15)
        ]

        # Act
        result = await service.search_with_pagination(
            query="test",
            hackathon_id="hack-123",
            page=2,
            page_size=10
        )

        # Assert
        assert len(result["results"]) == 5  # Only 5 results on page 2
        assert result["page"] == 2
        assert result["has_more"] is False
        assert result["results"][0].submission_id == "sub-10"

    @pytest.mark.asyncio
    async def test_pagination_invalid_page_raises_error(self):
        """Should raise ValueError for invalid page number"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await service.search_with_pagination(
                query="test",
                hackathon_id="hack-123",
                page=0  # Invalid
            )
        assert "page" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_pagination_invalid_page_size_raises_error(self):
        """Should raise ValueError for invalid page_size"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await service.search_with_pagination(
                query="test",
                hackathon_id="hack-123",
                page_size=100  # Too large
            )
        assert "page_size" in str(exc_info.value).lower()


class TestConvertToSearchResults:
    """Test _convert_to_search_results() helper function"""

    def test_convert_valid_results(self):
        """Should convert ZeroDB results to SearchResult objects"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        raw_results = [
            {
                "vector_id": "sub-123",
                "similarity": 0.92,
                "metadata": {
                    "submission_id": "sub-123",
                    "hackathon_id": "hack-456",
                    "project_name": "AI Project",
                    "description": "An AI solution",
                    "track_id": "ai-ml"
                }
            }
        ]

        # Act
        results = service._convert_to_search_results(raw_results)

        # Assert
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].submission_id == "sub-123"
        assert results[0].similarity_score == 0.92
        assert results[0].title == "AI Project"

    def test_convert_handles_missing_fields(self):
        """Should handle missing optional fields gracefully"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        raw_results = [
            {
                "vector_id": "sub-123",
                "similarity": 0.85,
                "metadata": {
                    "submission_id": "sub-123",
                    "hackathon_id": "hack-456"
                    # Missing project_name and description
                }
            }
        ]

        # Act
        results = service._convert_to_search_results(raw_results)

        # Assert
        assert len(results) == 1
        assert results[0].title == ""
        assert results[0].description == ""


class TestGenerateQueryEmbedding:
    """Test _generate_query_embedding() helper function"""

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self):
        """Should generate embedding for query"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.generate.return_value = {
            "embedding": [0.1, 0.2, 0.3],
            "model": "BAAI/bge-small-en-v1.5"
        }

        # Act
        embedding = await service._generate_query_embedding("test query")

        # Assert
        assert embedding == [0.1, 0.2, 0.3]
        mock_client.embeddings.generate.assert_called_once_with(
            text="test query",
            model="BAAI/bge-small-en-v1.5"
        )

    @pytest.mark.asyncio
    async def test_generate_embedding_missing_field_raises_error(self):
        """Should raise error if embedding field is missing"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.generate.return_value = {
            "model": "test-model"
            # Missing embedding field
        }

        # Act & Assert
        with pytest.raises(ZeroDBError) as exc_info:
            await service._generate_query_embedding("test")
        assert "missing 'embedding' field" in str(exc_info.value).lower()


class TestQuickSearch:
    """Test quick_search() convenience function"""

    @pytest.mark.asyncio
    async def test_quick_search_returns_dicts(self):
        """Should return list of dictionaries"""
        # Arrange
        mock_client = AsyncMock()

        mock_client.embeddings.generate.return_value = {
            "embedding": [0.1] * 384
        }

        mock_client.vectors.search.return_value = [
            {
                "vector_id": "sub-123",
                "similarity": 0.9,
                "metadata": {
                    "submission_id": "sub-123",
                    "hackathon_id": "hack-456",
                    "project_name": "Test Project",
                    "description": "A test"
                }
            }
        ]

        # Act
        results = await quick_search(
            zerodb_client=mock_client,
            query="test",
            hackathon_id="hack-456"
        )

        # Assert
        assert len(results) == 1
        assert isinstance(results[0], dict)
        assert results[0]["submission_id"] == "sub-123"
        assert results[0]["similarity_score"] == 0.9


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_search_with_no_results(self):
        """Should handle empty search results gracefully"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.generate.return_value = {
            "embedding": [0.1] * 384
        }
        mock_client.vectors.search.return_value = []

        # Act
        results = await service.search_by_query(
            query="nonexistent query",
            hackathon_id="hack-123"
        )

        # Assert
        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_special_characters_in_query(self):
        """Should handle special characters in query"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.generate.return_value = {
            "embedding": [0.1] * 384
        }
        mock_client.vectors.search.return_value = []

        # Act
        results = await service.search_by_query(
            query="C++ & Python projects with $ symbols!",
            hackathon_id="hack-123"
        )

        # Assert - should not raise error
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_very_long_query(self):
        """Should handle very long queries"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.embeddings.generate.return_value = {
            "embedding": [0.1] * 384
        }
        mock_client.vectors.search.return_value = []

        long_query = "test " * 100  # 500 characters

        # Act
        results = await service.search_by_query(
            query=long_query,
            hackathon_id="hack-123"
        )

        # Assert - should not raise error
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_find_similar_with_only_self_in_results(self):
        """Should return empty list if only self is found"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.vectors.get.return_value = {
            "embedding": [0.5] * 384
        }

        # Only self in results
        mock_client.vectors.search.return_value = [
            {
                "vector_id": "sub-123",
                "similarity": 1.0,
                "metadata": {
                    "submission_id": "sub-123",
                    "hackathon_id": "hack-456",
                    "project_name": "Self",
                    "description": "Self"
                }
            }
        ]

        # Act
        results = await service.find_similar_submissions(
            submission_id="sub-123",
            hackathon_id="hack-456"
        )

        # Assert
        assert results == []


class TestCoverageCompletion:
    """Additional tests to reach 80%+ coverage"""

    @pytest.mark.asyncio
    async def test_search_by_query_catches_generic_exception(self):
        """Should catch and wrap generic exceptions"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        # Simulate unexpected error
        mock_client.embeddings.generate.side_effect = RuntimeError(
            "Unexpected error"
        )

        # Act & Assert
        with pytest.raises(ZeroDBError) as exc_info:
            await service.search_by_query(
                query="test",
                hackathon_id="hack-123"
            )
        assert "embedding generation failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_find_similar_catches_generic_exception(self):
        """Should catch and wrap generic exceptions in find_similar"""
        # Arrange
        mock_client = AsyncMock()
        service = SearchService(mock_client)

        mock_client.vectors.get.side_effect = RuntimeError(
            "Unexpected error"
        )

        # Act & Assert
        with pytest.raises(ZeroDBError) as exc_info:
            await service.find_similar_submissions(
                submission_id="sub-123",
                hackathon_id="hack-456"
            )
        assert "search failed" in str(exc_info.value).lower()

    def test_search_result_default_metadata(self):
        """Should use empty dict as default metadata"""
        # Arrange & Act
        result = SearchResult(
            submission_id="sub-123",
            hackathon_id="hack-456",
            title="Test",
            description="Test desc",
            similarity_score=0.8
            # metadata not provided
        )

        # Assert
        assert result.metadata == {}
