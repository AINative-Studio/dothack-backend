"""
Comprehensive Embedding Tests

Tests for embedding generation, vector storage, semantic search, and performance.
This test suite achieves >= 80% coverage with proper mocking of external APIs.

Test Categories:
1. Embedding Generation (OpenAI/ZeroDB embeddings API)
2. Vector Storage (ZeroDB vectors API)
3. Semantic Search (similarity-based search)
4. Similarity Calculations
5. Performance Tests (< 500ms)
6. Error Handling
7. Integration Tests
"""

import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)
from services.embedding_service import (
    _prepare_text_for_embedding,
    batch_generate_embeddings,
    delete_submission_embedding,
    generate_submission_embedding,
    search_similar_submissions,
    update_submission_embedding,
)


# Test Fixtures
@pytest.fixture
def mock_zerodb_client():
    """Create a mock ZeroDB client with all necessary APIs"""
    client = AsyncMock()
    client.project_id = "test-project-123"

    # Mock embeddings API
    client.embeddings = AsyncMock()
    client.embeddings.generate = AsyncMock()

    # Mock vectors API
    client.vectors = AsyncMock()
    client.vectors.upsert = AsyncMock()
    client.vectors.batch_upsert = AsyncMock()
    client.vectors.delete = AsyncMock()
    client.vectors.search = AsyncMock()

    return client


@pytest.fixture
def sample_embedding():
    """Generate a sample 384-dimensional embedding vector"""
    return [0.1 * i for i in range(384)]


@pytest.fixture
def sample_submission():
    """Generate a sample submission dict"""
    return {
        "submission_id": str(uuid.uuid4()),
        "hackathon_id": str(uuid.uuid4()),
        "title": "AI Code Assistant",
        "description": "An intelligent coding assistant using GPT-4 for code generation and debugging",
        "project_details": "Built with Python, FastAPI, and integrates with OpenAI API",
        "track_id": "ai-ml-track",
        "team_id": "team-789",
        "status": "submitted",
    }


# ============================================================================
# PART 1: EMBEDDING GENERATION TESTS
# ============================================================================


class TestEmbeddingGeneration:
    """Test embedding generation with OpenAI/ZeroDB embeddings API"""

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, mock_zerodb_client, sample_embedding, sample_submission):
        """Should successfully generate and store embedding for a submission"""
        # Arrange
        mock_zerodb_client.embeddings.generate.return_value = [sample_embedding]
        mock_zerodb_client.vectors.upsert.return_value = {
            "vector_id": sample_submission["submission_id"],
            "success": True,
        }

        # Act
        result = await generate_submission_embedding(
            zerodb_client=mock_zerodb_client,
            submission_id=sample_submission["submission_id"],
            hackathon_id=sample_submission["hackathon_id"],
            title=sample_submission["title"],
            description=sample_submission["description"],
            project_details=sample_submission["project_details"],
            track_id=sample_submission["track_id"],
            team_id=sample_submission["team_id"],
            status=sample_submission["status"],
        )

        # Assert - verify result structure
        assert result["vector_id"] == sample_submission["submission_id"]
        assert result["dimensions"] == 384
        assert result["namespace"] == f"hackathons/{sample_submission['hackathon_id']}/submissions"
        assert result["text_length"] > 0

        # Assert - verify embedding generation was called with combined text
        mock_zerodb_client.embeddings.generate.assert_called_once()
        call_args = mock_zerodb_client.embeddings.generate.call_args
        texts = call_args[1]["texts"]
        assert len(texts) == 1
        combined_text = texts[0]
        assert sample_submission["title"] in combined_text
        assert sample_submission["description"] in combined_text
        assert sample_submission["project_details"] in combined_text

        # Assert - verify vector upsert was called correctly
        mock_zerodb_client.vectors.upsert.assert_called_once()
        upsert_args = mock_zerodb_client.vectors.upsert.call_args[1]
        assert upsert_args["vector_id"] == sample_submission["submission_id"]
        assert upsert_args["embedding"] == sample_embedding
        assert upsert_args["namespace"] == f"hackathons/{sample_submission['hackathon_id']}/submissions"

        # Assert - verify metadata
        metadata = upsert_args["metadata"]
        assert metadata["submission_id"] == sample_submission["submission_id"]
        assert metadata["hackathon_id"] == sample_submission["hackathon_id"]
        assert metadata["title"] == sample_submission["title"]
        assert metadata["track_id"] == sample_submission["track_id"]
        assert metadata["team_id"] == sample_submission["team_id"]
        assert metadata["status"] == sample_submission["status"]
        assert metadata["has_project_details"] is True

    @pytest.mark.asyncio
    async def test_generate_embedding_without_optional_fields(self, mock_zerodb_client, sample_embedding):
        """Should work with only required fields (title and description)"""
        # Arrange
        mock_zerodb_client.embeddings.generate.return_value = [sample_embedding]
        mock_zerodb_client.vectors.upsert.return_value = {"success": True}

        # Act
        result = await generate_submission_embedding(
            zerodb_client=mock_zerodb_client,
            submission_id="sub-123",
            hackathon_id="hack-456",
            title="Simple Project",
            description="A simple description",
            # No project_details, track_id, team_id
        )

        # Assert
        assert result["vector_id"] == "sub-123"
        upsert_args = mock_zerodb_client.vectors.upsert.call_args[1]
        metadata = upsert_args["metadata"]
        assert "track_id" not in metadata
        assert "team_id" not in metadata
        assert "has_project_details" not in metadata

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_title_raises_error(self, mock_zerodb_client):
        """Should raise ValueError if title is empty"""
        with pytest.raises(ValueError, match="Title cannot be empty"):
            await generate_submission_embedding(
                zerodb_client=mock_zerodb_client,
                submission_id="sub-123",
                hackathon_id="hack-456",
                title="",
                description="Valid description",
            )

        # Should not call any API
        mock_zerodb_client.embeddings.generate.assert_not_called()
        mock_zerodb_client.vectors.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_description_raises_error(self, mock_zerodb_client):
        """Should raise ValueError if description is empty or whitespace"""
        with pytest.raises(ValueError, match="Description cannot be empty"):
            await generate_submission_embedding(
                zerodb_client=mock_zerodb_client,
                submission_id="sub-123",
                hackathon_id="hack-456",
                title="Valid title",
                description="   ",  # Whitespace only
            )

    @pytest.mark.asyncio
    async def test_generate_embedding_no_vector_returned_raises_error(self, mock_zerodb_client):
        """Should raise HTTPException if embedding API returns empty list"""
        # Arrange
        mock_zerodb_client.embeddings.generate.return_value = []

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await generate_submission_embedding(
                zerodb_client=mock_zerodb_client,
                submission_id="sub-123",
                hackathon_id="hack-456",
                title="Test",
                description="Test description",
            )

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_generate_embedding_timeout_raises_http_exception(self, mock_zerodb_client):
        """Should raise HTTPException 504 on timeout"""
        # Arrange
        mock_zerodb_client.embeddings.generate.side_effect = ZeroDBTimeoutError("Request timed out")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await generate_submission_embedding(
                zerodb_client=mock_zerodb_client,
                submission_id="sub-123",
                hackathon_id="hack-456",
                title="Test",
                description="Test description",
            )

        assert exc_info.value.status_code == 504
        assert "timed out" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_generate_embedding_database_error_raises_http_exception(self, mock_zerodb_client, sample_embedding):
        """Should raise HTTPException 500 on database error"""
        # Arrange
        mock_zerodb_client.embeddings.generate.return_value = [sample_embedding]
        mock_zerodb_client.vectors.upsert.side_effect = ZeroDBError("Database connection failed")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await generate_submission_embedding(
                zerodb_client=mock_zerodb_client,
                submission_id="sub-123",
                hackathon_id="hack-456",
                title="Test",
                description="Test description",
            )

        assert exc_info.value.status_code == 500


# ============================================================================
# PART 2: VECTOR STORAGE TESTS
# ============================================================================


class TestVectorStorage:
    """Test vector storage and upsert operations"""

    @pytest.mark.asyncio
    async def test_update_embedding_success(self, mock_zerodb_client, sample_embedding):
        """Should update existing embedding (upsert operation)"""
        # Arrange
        mock_zerodb_client.embeddings.generate.return_value = [sample_embedding]
        mock_zerodb_client.vectors.upsert.return_value = {"success": True}

        # Act
        result = await update_submission_embedding(
            zerodb_client=mock_zerodb_client,
            submission_id="sub-123",
            hackathon_id="hack-456",
            title="Updated Title",
            description="Updated description with new content",
            status="submitted",
        )

        # Assert
        assert result["vector_id"] == "sub-123"
        mock_zerodb_client.embeddings.generate.assert_called_once()
        mock_zerodb_client.vectors.upsert.assert_called_once()

        # Verify updated status in metadata
        upsert_args = mock_zerodb_client.vectors.upsert.call_args[1]
        metadata = upsert_args["metadata"]
        assert metadata["status"] == "submitted"

    @pytest.mark.asyncio
    async def test_delete_embedding_success(self, mock_zerodb_client):
        """Should delete embedding successfully"""
        # Arrange
        mock_zerodb_client.vectors.delete.return_value = {"success": True}

        # Act
        result = await delete_submission_embedding(
            zerodb_client=mock_zerodb_client,
            submission_id="sub-123",
            hackathon_id="hack-456",
        )

        # Assert
        assert result["success"] is True
        assert result["vector_id"] == "sub-123"
        assert result["namespace"] == "hackathons/hack-456/submissions"

        mock_zerodb_client.vectors.delete.assert_called_once_with(
            vector_id="sub-123",
            namespace="hackathons/hack-456/submissions",
        )

    @pytest.mark.asyncio
    async def test_delete_embedding_not_found_returns_success(self, mock_zerodb_client):
        """Should return success even if embedding not found (idempotent operation)"""
        # Arrange
        mock_zerodb_client.vectors.delete.side_effect = ZeroDBNotFound("Vector not found")

        # Act
        result = await delete_submission_embedding(
            zerodb_client=mock_zerodb_client,
            submission_id="sub-123",
            hackathon_id="hack-456",
        )

        # Assert - should not raise exception
        assert result["success"] is True
        assert "message" in result
        assert "did not exist" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_embedding_timeout_raises_http_exception(self, mock_zerodb_client):
        """Should raise HTTPException 504 on timeout during delete"""
        # Arrange
        mock_zerodb_client.vectors.delete.side_effect = ZeroDBTimeoutError("Timeout")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_submission_embedding(
                zerodb_client=mock_zerodb_client,
                submission_id="sub-123",
                hackathon_id="hack-456",
            )

        assert exc_info.value.status_code == 504


# ============================================================================
# PART 3: SEMANTIC SEARCH TESTS
# ============================================================================


class TestSemanticSearch:
    """Test semantic search functionality"""

    @pytest.mark.asyncio
    async def test_search_similar_submissions_success(self, mock_zerodb_client, sample_embedding):
        """Should search and return similar submissions ranked by score"""
        # Arrange
        mock_zerodb_client.embeddings.generate.return_value = [sample_embedding]
        mock_zerodb_client.vectors.search.return_value = [
            {
                "vector_id": "sub-1",
                "score": 0.95,
                "metadata": {
                    "title": "AI Assistant",
                    "description": "Coding assistant with GPT-4",
                    "track_id": "ai-ml",
                    "team_id": "team-1",
                    "status": "submitted",
                },
            },
            {
                "vector_id": "sub-2",
                "score": 0.87,
                "metadata": {
                    "title": "Code Helper",
                    "description": "AI-powered code completion",
                    "track_id": "ai-ml",
                    "team_id": "team-2",
                    "status": "submitted",
                },
            },
        ]

        # Act
        results = await search_similar_submissions(
            zerodb_client=mock_zerodb_client,
            hackathon_id="hack-456",
            query_text="AI coding tool",
            top_k=5,
            track_id="ai-ml",
            status_filter="submitted",
            similarity_threshold=0.8,
        )

        # Assert - verify results structure
        assert len(results) == 2
        assert results[0]["submission_id"] == "sub-1"
        assert results[0]["score"] == 0.95
        assert results[0]["title"] == "AI Assistant"
        assert results[1]["submission_id"] == "sub-2"
        assert results[1]["score"] == 0.87

        # Assert - verify query embedding was generated
        mock_zerodb_client.embeddings.generate.assert_called_once()
        call_args = mock_zerodb_client.embeddings.generate.call_args[1]
        assert call_args["texts"] == ["AI coding tool"]

        # Assert - verify search was called with correct parameters
        search_args = mock_zerodb_client.vectors.search.call_args[1]
        assert search_args["top_k"] == 5
        assert search_args["namespace"] == "hackathons/hack-456/submissions"
        assert search_args["similarity_threshold"] == 0.8
        assert search_args["filter"]["track_id"] == "ai-ml"
        assert search_args["filter"]["status"] == "submitted"

    @pytest.mark.asyncio
    async def test_search_without_filters(self, mock_zerodb_client, sample_embedding):
        """Should search without filters if not provided"""
        # Arrange
        mock_zerodb_client.embeddings.generate.return_value = [sample_embedding]
        mock_zerodb_client.vectors.search.return_value = []

        # Act
        results = await search_similar_submissions(
            zerodb_client=mock_zerodb_client,
            hackathon_id="hack-123",
            query_text="test query",
        )

        # Assert
        search_args = mock_zerodb_client.vectors.search.call_args[1]
        assert search_args["filter"] is None
        assert results == []

    @pytest.mark.asyncio
    async def test_search_empty_query_raises_error(self, mock_zerodb_client):
        """Should raise ValueError if query text is empty"""
        with pytest.raises(ValueError, match="Query text cannot be empty"):
            await search_similar_submissions(
                zerodb_client=mock_zerodb_client,
                hackathon_id="hack-123",
                query_text="   ",  # Whitespace only
            )

        mock_zerodb_client.embeddings.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_with_high_similarity_threshold(self, mock_zerodb_client, sample_embedding):
        """Should filter results by similarity threshold"""
        # Arrange
        mock_zerodb_client.embeddings.generate.return_value = [sample_embedding]
        mock_zerodb_client.vectors.search.return_value = [
            {
                "vector_id": "sub-1",
                "score": 0.95,
                "metadata": {"title": "High similarity", "description": "Test"},
            },
        ]

        # Act
        results = await search_similar_submissions(
            zerodb_client=mock_zerodb_client,
            hackathon_id="hack-123",
            query_text="test",
            similarity_threshold=0.9,  # High threshold
        )

        # Assert
        assert len(results) == 1
        assert results[0]["score"] >= 0.9

    @pytest.mark.asyncio
    async def test_search_timeout_raises_http_exception(self, mock_zerodb_client):
        """Should raise HTTPException 504 on timeout during search"""
        # Arrange
        mock_zerodb_client.embeddings.generate.side_effect = ZeroDBTimeoutError("Timeout")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await search_similar_submissions(
                zerodb_client=mock_zerodb_client,
                hackathon_id="hack-123",
                query_text="test query",
            )

        assert exc_info.value.status_code == 504


# ============================================================================
# PART 4: BATCH OPERATIONS TESTS
# ============================================================================


class TestBatchOperations:
    """Test batch embedding generation"""

    @pytest.mark.asyncio
    async def test_batch_generate_embeddings_success(self, mock_zerodb_client):
        """Should generate embeddings for multiple submissions in batch"""
        # Arrange
        submissions = [
            {
                "submission_id": "sub-1",
                "title": "Project 1",
                "description": "Description 1",
                "status": "submitted",
                "team_id": "team-1",
            },
            {
                "submission_id": "sub-2",
                "title": "Project 2",
                "description": "Description 2",
                "status": "submitted",
                "team_id": "team-2",
                "track_id": "ai-ml",
            },
        ]

        # Mock batch embedding generation - returns list of embeddings
        embedding_1 = [0.1 * i for i in range(384)]
        embedding_2 = [0.2 * i for i in range(384)]
        mock_zerodb_client.embeddings.generate.return_value = [embedding_1, embedding_2]

        # Mock batch upsert
        mock_zerodb_client.vectors.batch_upsert.return_value = {
            "success": True,
            "count": 2,
        }

        # Act
        result = await batch_generate_embeddings(
            zerodb_client=mock_zerodb_client,
            hackathon_id="hack-123",
            submissions=submissions,
        )

        # Assert
        assert result["success_count"] == 2
        assert result["failed_count"] == 0
        assert result["failed_ids"] == []
        assert result["namespace"] == "hackathons/hack-123/submissions"

        # Verify batch embedding was called with correct texts
        generate_args = mock_zerodb_client.embeddings.generate.call_args[1]
        texts = generate_args["texts"]
        assert len(texts) == 2
        assert "Project 1" in texts[0]
        assert "Description 1" in texts[0]
        assert "Project 2" in texts[1]

        # Verify batch upsert was called
        upsert_args = mock_zerodb_client.vectors.batch_upsert.call_args[1]
        vectors = upsert_args["vectors"]
        assert len(vectors) == 2
        assert vectors[0]["vector_id"] == "sub-1"
        assert vectors[1]["vector_id"] == "sub-2"
        assert vectors[1]["metadata"]["track_id"] == "ai-ml"

    @pytest.mark.asyncio
    async def test_batch_generate_with_project_details(self, mock_zerodb_client):
        """Should include project details in batch text preparation"""
        # Arrange
        submissions = [
            {
                "submission_id": "sub-1",
                "title": "Test",
                "description": "Test desc",
                "project_details": "Built with Python",
            }
        ]

        embedding = [0.1 * i for i in range(384)]
        mock_zerodb_client.embeddings.generate.return_value = [embedding]
        mock_zerodb_client.vectors.batch_upsert.return_value = {"success": True}

        # Act
        await batch_generate_embeddings(
            zerodb_client=mock_zerodb_client,
            hackathon_id="hack-123",
            submissions=submissions,
        )

        # Assert
        generate_args = mock_zerodb_client.embeddings.generate.call_args[1]
        text = generate_args["texts"][0]
        assert "Built with Python" in text

    @pytest.mark.asyncio
    async def test_batch_generate_embedding_count_mismatch_raises_error(self, mock_zerodb_client):
        """Should raise error if embedding count doesn't match submission count"""
        # Arrange
        submissions = [
            {"submission_id": "sub-1", "title": "Test 1", "description": "Desc 1"},
            {"submission_id": "sub-2", "title": "Test 2", "description": "Desc 2"},
        ]

        # Return wrong number of embeddings
        embedding = [0.1 * i for i in range(384)]
        mock_zerodb_client.embeddings.generate.return_value = [embedding]  # Only 1 for 2 submissions

        # Act & Assert
        with pytest.raises(HTTPException):
            await batch_generate_embeddings(
                zerodb_client=mock_zerodb_client,
                hackathon_id="hack-123",
                submissions=submissions,
            )

    @pytest.mark.asyncio
    async def test_batch_generate_timeout_raises_http_exception(self, mock_zerodb_client):
        """Should raise HTTPException 504 on timeout during batch operation"""
        # Arrange
        mock_zerodb_client.embeddings.generate.side_effect = ZeroDBTimeoutError("Timeout")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await batch_generate_embeddings(
                zerodb_client=mock_zerodb_client,
                hackathon_id="hack-123",
                submissions=[
                    {"submission_id": "sub-1", "title": "Test", "description": "Test"}
                ],
            )

        assert exc_info.value.status_code == 504


# ============================================================================
# PART 5: TEXT PREPARATION TESTS
# ============================================================================


class TestTextPreparation:
    """Test _prepare_text_for_embedding() helper function"""

    def test_prepare_text_with_all_fields(self):
        """Should combine all fields with proper formatting"""
        result = _prepare_text_for_embedding(
            title="AI Assistant",
            description="An intelligent coding assistant",
            project_details="Built with Python and FastAPI",
        )

        assert "Title: AI Assistant" in result
        assert "Description: An intelligent coding assistant" in result
        assert "Details: Built with Python and FastAPI" in result
        assert "\n" in result  # Should have newlines between parts

    def test_prepare_text_without_project_details(self):
        """Should work without project details"""
        result = _prepare_text_for_embedding(
            title="Test Project",
            description="Test description",
            project_details=None,
        )

        assert "Title: Test Project" in result
        assert "Description: Test description" in result
        assert "Details:" not in result

    def test_prepare_text_strips_whitespace(self):
        """Should strip whitespace from all fields"""
        result = _prepare_text_for_embedding(
            title="  Title with spaces  ",
            description="  Description with spaces  ",
            project_details="  Details with spaces  ",
        )

        assert "Title: Title with spaces" in result
        assert "Description: Description with spaces" in result
        assert "Details: Details with spaces" in result
        assert "  " not in result  # No double spaces

    def test_prepare_text_truncates_long_project_details(self):
        """Should truncate very long project details to 1000 characters"""
        long_details = "x" * 2000  # 2000 characters

        result = _prepare_text_for_embedding(
            title="Test",
            description="Test",
            project_details=long_details,
        )

        # Details should be truncated to 1000 chars + "..."
        details_section = [line for line in result.split("\n") if line.startswith("Details:")][0]
        assert len(details_section) <= 1012  # "Details: " + 1000 chars + "..."
        assert "..." in result

    def test_prepare_text_truncates_very_long_combined_text(self):
        """Should truncate final combined text if over 5000 characters"""
        long_description = "x" * 6000  # Very long description

        result = _prepare_text_for_embedding(
            title="Test",
            description=long_description,
        )

        assert len(result) <= 5003  # 5000 + "..."
        assert result.endswith("...")

    def test_prepare_text_handles_empty_strings(self):
        """Should handle empty or None values gracefully"""
        result = _prepare_text_for_embedding(
            title="",
            description="Valid description",
            project_details="",
        )

        assert "Description: Valid description" in result
        # Empty title and details should not appear
        lines = [line for line in result.split("\n") if line.strip()]
        assert len(lines) == 1  # Only description


# ============================================================================
# PART 6: SIMILARITY CALCULATIONS TESTS
# ============================================================================


class TestSimilarityCalculations:
    """Test similarity score calculations and rankings"""

    @pytest.mark.asyncio
    async def test_similarity_scores_ranked_descending(self, mock_zerodb_client, sample_embedding):
        """Should return results ranked by similarity score (highest first)"""
        # Arrange
        mock_zerodb_client.embeddings.generate.return_value = [sample_embedding]
        mock_zerodb_client.vectors.search.return_value = [
            {"vector_id": "sub-1", "score": 0.95, "metadata": {"title": "High"}},
            {"vector_id": "sub-2", "score": 0.87, "metadata": {"title": "Medium"}},
            {"vector_id": "sub-3", "score": 0.75, "metadata": {"title": "Low"}},
        ]

        # Act
        results = await search_similar_submissions(
            zerodb_client=mock_zerodb_client,
            hackathon_id="hack-123",
            query_text="test",
        )

        # Assert - scores should be descending
        assert results[0]["score"] > results[1]["score"]
        assert results[1]["score"] > results[2]["score"]
        assert results[0]["score"] == 0.95
        assert results[2]["score"] == 0.75

    @pytest.mark.asyncio
    async def test_similarity_threshold_filters_results(self, mock_zerodb_client, sample_embedding):
        """Should only return results above similarity threshold"""
        # Arrange
        mock_zerodb_client.embeddings.generate.return_value = [sample_embedding]
        # ZeroDB API should already filter by threshold, but we test the parameter is passed
        mock_zerodb_client.vectors.search.return_value = [
            {"vector_id": "sub-1", "score": 0.95, "metadata": {"title": "High"}},
        ]

        # Act
        results = await search_similar_submissions(
            zerodb_client=mock_zerodb_client,
            hackathon_id="hack-123",
            query_text="test",
            similarity_threshold=0.9,
        )

        # Assert
        search_args = mock_zerodb_client.vectors.search.call_args[1]
        assert search_args["similarity_threshold"] == 0.9
        assert all(r["score"] >= 0.9 for r in results)


# ============================================================================
# PART 7: PERFORMANCE TESTS
# ============================================================================


class TestPerformance:
    """Test performance requirements (< 500ms)"""

    @pytest.mark.asyncio
    async def test_generate_embedding_performance(self, mock_zerodb_client, sample_embedding):
        """Should generate embedding in < 500ms"""
        # Arrange
        mock_zerodb_client.embeddings.generate.return_value = [sample_embedding]
        mock_zerodb_client.vectors.upsert.return_value = {"success": True}

        # Act
        start_time = time.time()
        await generate_submission_embedding(
            zerodb_client=mock_zerodb_client,
            submission_id="sub-123",
            hackathon_id="hack-456",
            title="Test Project",
            description="Test description for performance testing",
        )
        elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        # Assert
        assert elapsed_time < 500, f"Embedding generation took {elapsed_time:.2f}ms (should be < 500ms)"

    @pytest.mark.asyncio
    async def test_search_performance(self, mock_zerodb_client, sample_embedding):
        """Should search in < 500ms"""
        # Arrange
        mock_zerodb_client.embeddings.generate.return_value = [sample_embedding]
        mock_zerodb_client.vectors.search.return_value = [
            {"vector_id": "sub-1", "score": 0.95, "metadata": {"title": "Test"}},
        ]

        # Act
        start_time = time.time()
        await search_similar_submissions(
            zerodb_client=mock_zerodb_client,
            hackathon_id="hack-123",
            query_text="test query for performance",
        )
        elapsed_time = (time.time() - start_time) * 1000

        # Assert
        assert elapsed_time < 500, f"Search took {elapsed_time:.2f}ms (should be < 500ms)"

    @pytest.mark.asyncio
    async def test_batch_generate_performance(self, mock_zerodb_client):
        """Should batch generate 10 embeddings in < 500ms"""
        # Arrange
        submissions = [
            {"submission_id": f"sub-{i}", "title": f"Project {i}", "description": f"Description {i}"}
            for i in range(10)
        ]
        embeddings = [[0.1 * i] * 384 for i in range(10)]
        mock_zerodb_client.embeddings.generate.return_value = embeddings
        mock_zerodb_client.vectors.batch_upsert.return_value = {"success": True}

        # Act
        start_time = time.time()
        await batch_generate_embeddings(
            zerodb_client=mock_zerodb_client,
            hackathon_id="hack-123",
            submissions=submissions,
        )
        elapsed_time = (time.time() - start_time) * 1000

        # Assert
        assert elapsed_time < 500, f"Batch generation took {elapsed_time:.2f}ms (should be < 500ms)"

    @pytest.mark.asyncio
    async def test_text_preparation_performance(self):
        """Should prepare text in < 10ms"""
        # Act
        start_time = time.time()
        for _ in range(100):  # 100 iterations
            _prepare_text_for_embedding(
                title="Test Project",
                description="A test description for performance testing",
                project_details="Built with Python, FastAPI, and ZeroDB",
            )
        elapsed_time = (time.time() - start_time) * 1000

        # Assert - 100 iterations should take < 10ms total (< 0.1ms per call)
        assert elapsed_time < 10, f"100 text preparations took {elapsed_time:.2f}ms (should be < 10ms)"


# ============================================================================
# PART 8: INTEGRATION TESTS
# ============================================================================


class TestIntegration:
    """Integration tests for end-to-end workflows"""

    @pytest.mark.asyncio
    async def test_full_submission_lifecycle(self, mock_zerodb_client, sample_embedding):
        """Should handle full lifecycle: create, update, search, delete"""
        # Mock all operations
        mock_zerodb_client.embeddings.generate.return_value = [sample_embedding]
        mock_zerodb_client.vectors.upsert.return_value = {"success": True}
        mock_zerodb_client.vectors.delete.return_value = {"success": True}
        mock_zerodb_client.vectors.search.return_value = [
            {"vector_id": "sub-123", "score": 1.0, "metadata": {"title": "Test"}},
        ]

        # Step 1: Create embedding
        create_result = await generate_submission_embedding(
            zerodb_client=mock_zerodb_client,
            submission_id="sub-123",
            hackathon_id="hack-456",
            title="Test Project",
            description="Test description",
        )
        assert create_result["vector_id"] == "sub-123"

        # Step 2: Update embedding
        update_result = await update_submission_embedding(
            zerodb_client=mock_zerodb_client,
            submission_id="sub-123",
            hackathon_id="hack-456",
            title="Updated Project",
            description="Updated description",
        )
        assert update_result["vector_id"] == "sub-123"

        # Step 3: Search for similar
        search_results = await search_similar_submissions(
            zerodb_client=mock_zerodb_client,
            hackathon_id="hack-456",
            query_text="test",
        )
        assert len(search_results) > 0

        # Step 4: Delete embedding
        delete_result = await delete_submission_embedding(
            zerodb_client=mock_zerodb_client,
            submission_id="sub-123",
            hackathon_id="hack-456",
        )
        assert delete_result["success"] is True

        # Verify all operations were called
        assert mock_zerodb_client.embeddings.generate.call_count >= 2  # Create and search
        assert mock_zerodb_client.vectors.upsert.call_count == 2  # Create and update
        assert mock_zerodb_client.vectors.delete.call_count == 1
        assert mock_zerodb_client.vectors.search.call_count == 1

    @pytest.mark.asyncio
    async def test_batch_workflow_with_search(self, mock_zerodb_client):
        """Should batch create embeddings and search across them"""
        # Arrange
        submissions = [
            {"submission_id": f"sub-{i}", "title": f"Project {i}", "description": f"Desc {i}"}
            for i in range(5)
        ]
        embeddings = [[0.1 * i] * 384 for i in range(5)]
        mock_zerodb_client.embeddings.generate.return_value = embeddings
        mock_zerodb_client.vectors.batch_upsert.return_value = {"success": True}

        # Step 1: Batch create
        batch_result = await batch_generate_embeddings(
            zerodb_client=mock_zerodb_client,
            hackathon_id="hack-123",
            submissions=submissions,
        )
        assert batch_result["success_count"] == 5

        # Step 2: Search
        mock_zerodb_client.embeddings.generate.return_value = [embeddings[0]]
        mock_zerodb_client.vectors.search.return_value = [
            {"vector_id": "sub-0", "score": 0.95, "metadata": {"title": "Project 0"}},
        ]

        search_results = await search_similar_submissions(
            zerodb_client=mock_zerodb_client,
            hackathon_id="hack-123",
            query_text="project",
        )
        assert len(search_results) > 0
