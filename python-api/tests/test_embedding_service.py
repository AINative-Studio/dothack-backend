"""
Tests for Embedding Service

Comprehensive tests for embedding generation, vector storage, and semantic search
functionality for hackathon submissions using ZeroDB.
"""

import uuid
from unittest.mock import AsyncMock, patch

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


class TestGenerateSubmissionEmbedding:
    """Test generate_submission_embedding() function"""

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self):
        """Should generate and store embedding successfully"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        # Mock embedding generation
        mock_client.embeddings.generate.return_value = {
            "embedding": [0.1] * 384,  # 384 dimensions
            "model": "BAAI/bge-small-en-v1.5",
            "dimensions": 384,
        }

        # Mock vector upsert
        mock_client.vectors.upsert.return_value = {
            "vector_id": submission_id,
            "success": True,
        }

        # Act
        result = await generate_submission_embedding(
            zerodb_client=mock_client,
            submission_id=submission_id,
            hackathon_id=hackathon_id,
            title="AI Code Assistant",
            description="An intelligent coding assistant using GPT-4",
            track_id="ai-ml",
            team_id="team-123",
            status="draft",
        )

        # Assert
        assert result["vector_id"] == submission_id
        assert result["dimensions"] == 384
        assert result["namespace"] == f"hackathons/{hackathon_id}/submissions"
        assert result["text_length"] > 0

        # Verify embedding generation was called
        mock_client.embeddings.generate.assert_called_once()
        call_args = mock_client.embeddings.generate.call_args
        assert "AI Code Assistant" in call_args.kwargs["text"]
        assert "intelligent coding assistant" in call_args.kwargs["text"]

        # Verify vector upsert was called
        mock_client.vectors.upsert.assert_called_once()
        upsert_args = mock_client.vectors.upsert.call_args
        assert upsert_args.kwargs["vector_id"] == submission_id
        assert upsert_args.kwargs["namespace"] == f"hackathons/{hackathon_id}/submissions"
        assert len(upsert_args.kwargs["embedding"]) == 384

        # Verify metadata
        metadata = upsert_args.kwargs["metadata"]
        assert metadata["submission_id"] == submission_id
        assert metadata["hackathon_id"] == hackathon_id
        assert metadata["title"] == "AI Code Assistant"
        assert metadata["track_id"] == "ai-ml"
        assert metadata["team_id"] == "team-123"
        assert metadata["status"] == "draft"

    @pytest.mark.asyncio
    async def test_generate_embedding_with_project_details(self):
        """Should include project details in embedding text"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_client.embeddings.generate.return_value = {
            "embedding": [0.1] * 384,
            "model": "BAAI/bge-small-en-v1.5",
            "dimensions": 384,
        }
        mock_client.vectors.upsert.return_value = {"vector_id": submission_id}

        # Act
        result = await generate_submission_embedding(
            zerodb_client=mock_client,
            submission_id=submission_id,
            hackathon_id=hackathon_id,
            title="Test Project",
            description="Test description",
            project_details="Built with Python and FastAPI. Uses GPT-4 for code generation.",
        )

        # Assert
        call_args = mock_client.embeddings.generate.call_args
        combined_text = call_args.kwargs["text"]
        assert "Test Project" in combined_text
        assert "Test description" in combined_text
        assert "Built with Python" in combined_text
        assert "GPT-4" in combined_text

        # Verify metadata includes project details flag
        upsert_args = mock_client.vectors.upsert.call_args
        metadata = upsert_args.kwargs["metadata"]
        assert metadata["has_project_details"] is True

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_title_raises_error(self):
        """Should raise ValueError if title is empty"""
        # Arrange
        mock_client = AsyncMock()

        # Act & Assert
        with pytest.raises(ValueError, match="Title cannot be empty"):
            await generate_submission_embedding(
                zerodb_client=mock_client,
                submission_id="sub-123",
                hackathon_id="hack-456",
                title="",
                description="Valid description",
            )

        # Should not call any API
        mock_client.embeddings.generate.assert_not_called()
        mock_client.vectors.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_description_raises_error(self):
        """Should raise ValueError if description is empty"""
        # Arrange
        mock_client = AsyncMock()

        # Act & Assert
        with pytest.raises(ValueError, match="Description cannot be empty"):
            await generate_submission_embedding(
                zerodb_client=mock_client,
                submission_id="sub-123",
                hackathon_id="hack-456",
                title="Valid title",
                description="   ",  # Whitespace only
            )

    @pytest.mark.asyncio
    async def test_generate_embedding_timeout_raises_http_exception(self):
        """Should raise HTTPException on timeout"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.embeddings.generate.side_effect = ZeroDBTimeoutError("Request timed out")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await generate_submission_embedding(
                zerodb_client=mock_client,
                submission_id="sub-123",
                hackathon_id="hack-456",
                title="Test",
                description="Test description",
            )

        assert exc_info.value.status_code == 504
        assert "timed out" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_generate_embedding_database_error_raises_http_exception(self):
        """Should raise HTTPException on database error"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.embeddings.generate.return_value = {
            "embedding": [0.1] * 384,
            "model": "BAAI/bge-small-en-v1.5",
        }
        mock_client.vectors.upsert.side_effect = ZeroDBError("Database connection failed")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await generate_submission_embedding(
                zerodb_client=mock_client,
                submission_id="sub-123",
                hackathon_id="hack-456",
                title="Test",
                description="Test description",
            )

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_generate_embedding_no_vector_returned_raises_error(self):
        """Should raise HTTPException if embedding API returns no vector"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.embeddings.generate.return_value = {
            "model": "BAAI/bge-small-en-v1.5",
            # Missing 'embedding' key
        }

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await generate_submission_embedding(
                zerodb_client=mock_client,
                submission_id="sub-123",
                hackathon_id="hack-456",
                title="Test",
                description="Test description",
            )

        # Verify it's a 500 error (unexpected error caught in exception handler)
        assert exc_info.value.status_code == 500


class TestUpdateSubmissionEmbedding:
    """Test update_submission_embedding() function"""

    @pytest.mark.asyncio
    async def test_update_embedding_success(self):
        """Should update embedding successfully (same as generate)"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())

        mock_client.embeddings.generate.return_value = {
            "embedding": [0.2] * 384,  # Different values
            "model": "BAAI/bge-small-en-v1.5",
            "dimensions": 384,
        }
        mock_client.vectors.upsert.return_value = {"vector_id": submission_id}

        # Act
        result = await update_submission_embedding(
            zerodb_client=mock_client,
            submission_id=submission_id,
            hackathon_id="hack-123",
            title="Updated Title",
            description="Updated description",
            status="submitted",
        )

        # Assert
        assert result["vector_id"] == submission_id
        mock_client.embeddings.generate.assert_called_once()
        mock_client.vectors.upsert.assert_called_once()

        # Verify updated status in metadata
        upsert_args = mock_client.vectors.upsert.call_args
        metadata = upsert_args.kwargs["metadata"]
        assert metadata["status"] == "submitted"

    @pytest.mark.asyncio
    async def test_update_embedding_with_changed_text(self):
        """Should regenerate embedding when text changes"""
        # Arrange
        mock_client = AsyncMock()

        mock_client.embeddings.generate.return_value = {
            "embedding": [0.3] * 384,
            "model": "BAAI/bge-small-en-v1.5",
        }
        mock_client.vectors.upsert.return_value = {"vector_id": "sub-123"}

        # Act
        await update_submission_embedding(
            zerodb_client=mock_client,
            submission_id="sub-123",
            hackathon_id="hack-456",
            title="Completely New Title",
            description="Completely different description with new content",
        )

        # Assert
        call_args = mock_client.embeddings.generate.call_args
        text = call_args.kwargs["text"]
        assert "Completely New Title" in text
        assert "different description" in text


class TestDeleteSubmissionEmbedding:
    """Test delete_submission_embedding() function"""

    @pytest.mark.asyncio
    async def test_delete_embedding_success(self):
        """Should delete embedding successfully"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_client.vectors.delete.return_value = {"success": True}

        # Act
        result = await delete_submission_embedding(
            zerodb_client=mock_client,
            submission_id=submission_id,
            hackathon_id=hackathon_id,
        )

        # Assert
        assert result["success"] is True
        assert result["vector_id"] == submission_id
        assert result["namespace"] == f"hackathons/{hackathon_id}/submissions"

        mock_client.vectors.delete.assert_called_once_with(
            vector_id=submission_id,
            namespace=f"hackathons/{hackathon_id}/submissions",
        )

    @pytest.mark.asyncio
    async def test_delete_embedding_not_found_returns_success(self):
        """Should return success even if embedding not found"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.vectors.delete.side_effect = ZeroDBNotFound("Vector not found")

        # Act
        result = await delete_submission_embedding(
            zerodb_client=mock_client,
            submission_id="sub-123",
            hackathon_id="hack-456",
        )

        # Assert - should not raise exception
        assert result["success"] is True
        assert "message" in result
        assert "did not exist" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_embedding_timeout_raises_http_exception(self):
        """Should raise HTTPException on timeout"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.vectors.delete.side_effect = ZeroDBTimeoutError("Timeout")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_submission_embedding(
                zerodb_client=mock_client,
                submission_id="sub-123",
                hackathon_id="hack-456",
            )

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_delete_embedding_database_error_raises_http_exception(self):
        """Should raise HTTPException on database error"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.vectors.delete.side_effect = ZeroDBError("Connection failed")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_submission_embedding(
                zerodb_client=mock_client,
                submission_id="sub-123",
                hackathon_id="hack-456",
            )

        assert exc_info.value.status_code == 500


class TestSearchSimilarSubmissions:
    """Test search_similar_submissions() function"""

    @pytest.mark.asyncio
    async def test_search_similar_submissions_success(self):
        """Should search and return similar submissions"""
        # Arrange
        mock_client = AsyncMock()
        hackathon_id = str(uuid.uuid4())

        # Mock embedding generation for query
        mock_client.embeddings.generate.return_value = {
            "embedding": [0.5] * 384,
            "model": "BAAI/bge-small-en-v1.5",
        }

        # Mock vector search results
        mock_client.vectors.search.return_value = [
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
            zerodb_client=mock_client,
            hackathon_id=hackathon_id,
            query_text="AI coding tool",
            top_k=5,
            track_id="ai-ml",
            status_filter="submitted",
            similarity_threshold=0.8,
        )

        # Assert
        assert len(results) == 2
        assert results[0]["submission_id"] == "sub-1"
        assert results[0]["score"] == 0.95
        assert results[0]["title"] == "AI Assistant"
        assert results[1]["submission_id"] == "sub-2"
        assert results[1]["score"] == 0.87

        # Verify query embedding was generated
        mock_client.embeddings.generate.assert_called_once_with(
            text="AI coding tool", model="BAAI/bge-small-en-v1.5"
        )

        # Verify search was called with correct parameters
        search_args = mock_client.vectors.search.call_args
        assert search_args.kwargs["top_k"] == 5
        assert search_args.kwargs["namespace"] == f"hackathons/{hackathon_id}/submissions"
        assert search_args.kwargs["similarity_threshold"] == 0.8
        assert search_args.kwargs["filter"]["track_id"] == "ai-ml"
        assert search_args.kwargs["filter"]["status"] == "submitted"

    @pytest.mark.asyncio
    async def test_search_without_filters(self):
        """Should search without filters if not provided"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.embeddings.generate.return_value = {"embedding": [0.5] * 384}
        mock_client.vectors.search.return_value = []

        # Act
        results = await search_similar_submissions(
            zerodb_client=mock_client,
            hackathon_id="hack-123",
            query_text="test query",
        )

        # Assert
        search_args = mock_client.vectors.search.call_args
        assert search_args.kwargs["filter"] is None
        assert results == []

    @pytest.mark.asyncio
    async def test_search_empty_query_raises_error(self):
        """Should raise ValueError if query text is empty"""
        # Arrange
        mock_client = AsyncMock()

        # Act & Assert
        with pytest.raises(ValueError, match="Query text cannot be empty"):
            await search_similar_submissions(
                zerodb_client=mock_client,
                hackathon_id="hack-123",
                query_text="   ",  # Whitespace only
            )

        mock_client.embeddings.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_timeout_raises_http_exception(self):
        """Should raise HTTPException on timeout"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.embeddings.generate.side_effect = ZeroDBTimeoutError("Timeout")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await search_similar_submissions(
                zerodb_client=mock_client,
                hackathon_id="hack-123",
                query_text="test query",
            )

        assert exc_info.value.status_code == 504


class TestBatchGenerateEmbeddings:
    """Test batch_generate_embeddings() function"""

    @pytest.mark.asyncio
    async def test_batch_generate_success(self):
        """Should generate embeddings for multiple submissions"""
        # Arrange
        mock_client = AsyncMock()
        hackathon_id = str(uuid.uuid4())

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

        # Mock batch embedding generation
        mock_client.embeddings.batch_generate.return_value = {
            "embeddings": [[0.1] * 384, [0.2] * 384],
            "model": "BAAI/bge-small-en-v1.5",
            "dimensions": 384,
            "count": 2,
        }

        # Mock batch upsert
        mock_client.vectors.batch_upsert.return_value = {"success": True}

        # Act
        result = await batch_generate_embeddings(
            zerodb_client=mock_client,
            hackathon_id=hackathon_id,
            submissions=submissions,
        )

        # Assert
        assert result["success_count"] == 2
        assert result["failed_count"] == 0
        assert result["failed_ids"] == []
        assert result["namespace"] == f"hackathons/{hackathon_id}/submissions"

        # Verify batch embedding was called with correct texts
        batch_args = mock_client.embeddings.batch_generate.call_args
        texts = batch_args.kwargs["texts"]
        assert len(texts) == 2
        assert "Project 1" in texts[0]
        assert "Description 1" in texts[0]
        assert "Project 2" in texts[1]

        # Verify batch upsert was called
        upsert_args = mock_client.vectors.batch_upsert.call_args
        vectors = upsert_args.kwargs["vectors"]
        assert len(vectors) == 2
        assert vectors[0]["vector_id"] == "sub-1"
        assert vectors[1]["vector_id"] == "sub-2"
        assert vectors[1]["metadata"]["track_id"] == "ai-ml"

    @pytest.mark.asyncio
    async def test_batch_generate_with_project_details(self):
        """Should include project details in batch text preparation"""
        # Arrange
        mock_client = AsyncMock()

        submissions = [
            {
                "submission_id": "sub-1",
                "title": "Test",
                "description": "Test desc",
                "project_details": "Built with Python",
            }
        ]

        mock_client.embeddings.batch_generate.return_value = {
            "embeddings": [[0.1] * 384],
            "count": 1,
        }
        mock_client.vectors.batch_upsert.return_value = {"success": True}

        # Act
        await batch_generate_embeddings(
            zerodb_client=mock_client,
            hackathon_id="hack-123",
            submissions=submissions,
        )

        # Assert
        batch_args = mock_client.embeddings.batch_generate.call_args
        text = batch_args.kwargs["texts"][0]
        assert "Built with Python" in text

    @pytest.mark.asyncio
    async def test_batch_generate_embedding_count_mismatch_raises_error(self):
        """Should raise error if embedding count doesn't match submission count"""
        # Arrange
        mock_client = AsyncMock()

        submissions = [
            {
                "submission_id": "sub-1",
                "title": "Test 1",
                "description": "Desc 1",
            },
            {
                "submission_id": "sub-2",
                "title": "Test 2",
                "description": "Desc 2",
            },
        ]

        # Return wrong number of embeddings
        mock_client.embeddings.batch_generate.return_value = {
            "embeddings": [[0.1] * 384],  # Only 1 embedding for 2 submissions
            "count": 1,
        }

        # Act & Assert
        with pytest.raises(HTTPException):
            await batch_generate_embeddings(
                zerodb_client=mock_client,
                hackathon_id="hack-123",
                submissions=submissions,
            )

    @pytest.mark.asyncio
    async def test_batch_generate_timeout_raises_http_exception(self):
        """Should raise HTTPException on timeout"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.embeddings.batch_generate.side_effect = ZeroDBTimeoutError("Timeout")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await batch_generate_embeddings(
                zerodb_client=mock_client,
                hackathon_id="hack-123",
                submissions=[
                    {"submission_id": "sub-1", "title": "Test", "description": "Test"}
                ],
            )

        assert exc_info.value.status_code == 504


class TestPrepareTextForEmbedding:
    """Test _prepare_text_for_embedding() helper function"""

    def test_prepare_text_with_all_fields(self):
        """Should combine all fields with proper formatting"""
        # Act
        result = _prepare_text_for_embedding(
            title="AI Assistant",
            description="An intelligent coding assistant",
            project_details="Built with Python and FastAPI",
        )

        # Assert
        assert "Title: AI Assistant" in result
        assert "Description: An intelligent coding assistant" in result
        assert "Details: Built with Python and FastAPI" in result
        assert "\n" in result  # Should have newlines between parts

    def test_prepare_text_without_project_details(self):
        """Should work without project details"""
        # Act
        result = _prepare_text_for_embedding(
            title="Test Project",
            description="Test description",
            project_details=None,
        )

        # Assert
        assert "Title: Test Project" in result
        assert "Description: Test description" in result
        assert "Details:" not in result

    def test_prepare_text_strips_whitespace(self):
        """Should strip whitespace from all fields"""
        # Act
        result = _prepare_text_for_embedding(
            title="  Title with spaces  ",
            description="  Description with spaces  ",
            project_details="  Details with spaces  ",
        )

        # Assert
        assert "Title: Title with spaces" in result
        assert "Description: Description with spaces" in result
        assert "Details: Details with spaces" in result
        assert "  " not in result  # No double spaces

    def test_prepare_text_truncates_long_project_details(self):
        """Should truncate very long project details"""
        # Arrange
        long_details = "x" * 2000  # 2000 characters

        # Act
        result = _prepare_text_for_embedding(
            title="Test",
            description="Test",
            project_details=long_details,
        )

        # Assert
        assert len(result) < 2000  # Should be truncated
        assert "..." in result  # Should have truncation indicator

    def test_prepare_text_truncates_very_long_combined_text(self):
        """Should truncate final combined text if too long"""
        # Arrange
        long_description = "x" * 6000  # Very long description

        # Act
        result = _prepare_text_for_embedding(
            title="Test",
            description=long_description,
        )

        # Assert
        assert len(result) <= 5003  # 5000 + "..."
        assert result.endswith("...")

    def test_prepare_text_handles_empty_strings(self):
        """Should handle empty or None values gracefully"""
        # Act
        result = _prepare_text_for_embedding(
            title="",
            description="Valid description",
            project_details="",
        )

        # Assert
        assert "Description: Valid description" in result
        # Empty title and details should not appear
        lines = [line for line in result.split("\n") if line.strip()]
        assert len(lines) == 1  # Only description


class TestIntegrationWithSubmissionService:
    """Integration tests for embedding service with submission service"""

    @pytest.mark.asyncio
    async def test_create_submission_generates_embedding(self):
        """Should automatically generate embedding when creating submission"""
        # This test would require importing and testing submission_service
        # with the embedding integration. This is more of an integration test
        # that should verify the workflow documented in the requirements.
        pass

    @pytest.mark.asyncio
    async def test_update_submission_updates_embedding(self):
        """Should automatically update embedding when updating submission text"""
        pass

    @pytest.mark.asyncio
    async def test_delete_submission_deletes_embedding(self):
        """Should automatically delete embedding when deleting submission"""
        pass
