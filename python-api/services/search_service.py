"""
Search Service for Semantic Submission Search

Provides semantic search functionality to find similar hackathon submissions
using natural language queries and vector similarity. Leverages ZeroDB's
embedding generation and vector search capabilities.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)

# Configure logger
logger = logging.getLogger(__name__)

# Default embedding model
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


@dataclass
class SearchResult:
    """
    Search result with submission data and similarity score.

    Attributes:
        submission_id: Unique identifier for the submission
        hackathon_id: Hackathon the submission belongs to
        title: Project title/name
        description: Project description
        similarity_score: Cosine similarity score (0.0 - 1.0)
        metadata: Additional submission metadata (track, status, etc.)
    """
    submission_id: str
    hackathon_id: str
    title: str
    description: str
    similarity_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert SearchResult to dictionary"""
        return {
            "submission_id": self.submission_id,
            "hackathon_id": self.hackathon_id,
            "title": self.title,
            "description": self.description,
            "similarity_score": self.similarity_score,
            "metadata": self.metadata,
        }


class SearchService:
    """
    Service for semantic search of hackathon submissions.

    Provides methods for:
    - Natural language search queries
    - Finding similar submissions
    - Filtering by hackathon, track, and status
    - Ranking results by similarity score

    Example:
        >>> service = SearchService(zerodb_client)
        >>> results = await service.search_by_query(
        ...     query="AI healthcare solutions",
        ...     hackathon_id="hack-123",
        ...     top_k=10
        ... )
    """

    def __init__(
        self,
        zerodb_client: ZeroDBClient,
        model: str = DEFAULT_EMBEDDING_MODEL
    ):
        """
        Initialize SearchService.

        Args:
            zerodb_client: ZeroDB client instance
            model: Embedding model to use (default: BAAI/bge-small-en-v1.5)
        """
        self.client = zerodb_client
        self.model = model
        logger.info(f"SearchService initialized with model: {model}")

    async def search_by_query(
        self,
        query: str,
        hackathon_id: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_similarity: float = 0.5
    ) -> List[SearchResult]:
        """
        Search submissions using natural language query.

        Converts the query to an embedding and performs vector similarity
        search against submission embeddings in ZeroDB.

        Args:
            query: Natural language search query (e.g., "AI-powered healthcare")
            hackathon_id: Hackathon to search within
            top_k: Number of results to return (default: 10, max: 50)
            filters: Additional metadata filters (track_id, status, etc.)
            min_similarity: Minimum similarity threshold 0.0-1.0 (default: 0.5)

        Returns:
            List of SearchResult objects sorted by similarity (highest first)

        Raises:
            ValueError: If query is empty or top_k is invalid
            ZeroDBError: If embedding generation or search fails

        Example:
            >>> results = await service.search_by_query(
            ...     query="machine learning projects",
            ...     hackathon_id="hack-123",
            ...     top_k=5,
            ...     filters={"track_id": "ai-ml", "status": "SUBMITTED"}
            ... )
        """
        # Validate inputs
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        if top_k < 1 or top_k > 50:
            raise ValueError("top_k must be between 1 and 50")

        if min_similarity < 0.0 or min_similarity > 1.0:
            raise ValueError("min_similarity must be between 0.0 and 1.0")

        logger.info(
            f"Searching submissions with query='{query}', "
            f"hackathon_id={hackathon_id}, top_k={top_k}"
        )

        try:
            # Generate query embedding
            query_embedding = await self._generate_query_embedding(query)

            # Build namespace for this hackathon
            namespace = f"hackathons/{hackathon_id}/submissions"

            # Merge hackathon_id into filters
            search_filters = filters.copy() if filters else {}
            search_filters["hackathon_id"] = hackathon_id

            # Search vectors in ZeroDB
            results = await self.client.vectors.search(
                query_vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                filter=search_filters,
                similarity_threshold=min_similarity
            )

            # Convert to SearchResult objects
            search_results = self._convert_to_search_results(results)

            logger.info(f"Found {len(search_results)} matching submissions")
            return search_results

        except ZeroDBTimeoutError as e:
            logger.error(f"Timeout during search: {e}")
            raise ZeroDBError(f"Search request timed out: {e}")
        except ZeroDBError as e:
            logger.error(f"ZeroDB error during search: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            raise ZeroDBError(f"Search failed: {e}")

    async def find_similar_submissions(
        self,
        submission_id: str,
        hackathon_id: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Find submissions similar to a given submission.

        Retrieves the embedding for the reference submission and searches
        for similar submissions using vector similarity.

        Args:
            submission_id: Reference submission ID
            hackathon_id: Hackathon context
            top_k: Number of similar submissions to return (default: 10)
            filters: Additional metadata filters (track_id, status, etc.)

        Returns:
            List of similar SearchResult objects (excludes reference submission)

        Raises:
            ValueError: If submission_id is empty or top_k is invalid
            ZeroDBNotFound: If reference submission not found
            ZeroDBError: If search fails

        Example:
            >>> results = await service.find_similar_submissions(
            ...     submission_id="sub-123",
            ...     hackathon_id="hack-456",
            ...     top_k=10
            ... )
        """
        # Validate inputs
        if not submission_id or not submission_id.strip():
            raise ValueError("submission_id cannot be empty")

        if top_k < 1 or top_k > 50:
            raise ValueError("top_k must be between 1 and 50")

        logger.info(
            f"Finding similar submissions for submission_id={submission_id}, "
            f"hackathon_id={hackathon_id}, top_k={top_k}"
        )

        try:
            # Build namespace
            namespace = f"hackathons/{hackathon_id}/submissions"

            # Get the submission's embedding from ZeroDB
            vector_data = await self.client.vectors.get(
                vector_id=submission_id,
                namespace=namespace
            )

            if not vector_data or "embedding" not in vector_data:
                raise ZeroDBNotFound(
                    f"Embedding not found for submission {submission_id}"
                )

            # Build filters
            search_filters = filters.copy() if filters else {}
            search_filters["hackathon_id"] = hackathon_id

            # Search for similar vectors (request top_k + 1 to account for self)
            results = await self.client.vectors.search(
                query_vector=vector_data["embedding"],
                top_k=top_k + 1,
                namespace=namespace,
                filter=search_filters
            )

            # Remove the source submission from results
            filtered_results = [
                r for r in results
                if r.get("vector_id") != submission_id or
                r.get("metadata", {}).get("submission_id") != submission_id
            ][:top_k]

            # Convert to SearchResult objects
            search_results = self._convert_to_search_results(filtered_results)

            logger.info(f"Found {len(search_results)} similar submissions")
            return search_results

        except ZeroDBNotFound:
            raise
        except ZeroDBTimeoutError as e:
            logger.error(f"Timeout finding similar submissions: {e}")
            raise ZeroDBError(f"Search request timed out: {e}")
        except ZeroDBError as e:
            logger.error(f"ZeroDB error finding similar submissions: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error finding similar submissions: {e}")
            raise ZeroDBError(f"Search failed: {e}")

    async def search_with_pagination(
        self,
        query: str,
        hackathon_id: str,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_similarity: float = 0.5
    ) -> Dict[str, Any]:
        """
        Search submissions with pagination support.

        Args:
            query: Natural language search query
            hackathon_id: Hackathon to search within
            page: Page number (1-indexed, default: 1)
            page_size: Results per page (default: 10, max: 50)
            filters: Additional metadata filters
            min_similarity: Minimum similarity threshold

        Returns:
            Dict containing:
                - results: List of SearchResult objects for current page
                - page: Current page number
                - page_size: Results per page
                - total: Total number of results

        Raises:
            ValueError: If page or page_size is invalid
            ZeroDBError: If search fails
        """
        # Validate pagination parameters
        if page < 1:
            raise ValueError("page must be >= 1")

        if page_size < 1 or page_size > 50:
            raise ValueError("page_size must be between 1 and 50")

        # Calculate offset
        offset = (page - 1) * page_size

        # For vector search, we need to fetch all results up to the end of
        # the requested page, then slice. This is a limitation of vector search.
        # We'll fetch up to offset + page_size results.
        fetch_limit = min(offset + page_size, 50)

        # Perform search
        all_results = await self.search_by_query(
            query=query,
            hackathon_id=hackathon_id,
            top_k=fetch_limit,
            filters=filters,
            min_similarity=min_similarity
        )

        # Slice for pagination
        paginated_results = all_results[offset:offset + page_size]

        return {
            "results": paginated_results,
            "page": page,
            "page_size": page_size,
            "total": len(all_results),
            "has_more": len(all_results) > offset + page_size
        }

    async def _generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for search query.

        Args:
            query: Text query to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            ZeroDBError: If embedding generation fails
        """
        try:
            response = await self.client.embeddings.generate(
                text=query,
                model=self.model
            )

            if "embedding" not in response:
                raise ZeroDBError(
                    "Invalid response from embedding service: missing 'embedding' field"
                )

            embedding = response["embedding"]
            logger.debug(
                f"Generated embedding for query (dimensions: {len(embedding)})"
            )
            return embedding

        except ZeroDBError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise ZeroDBError(f"Embedding generation failed: {e}")

    def _convert_to_search_results(
        self,
        results: List[Dict[str, Any]]
    ) -> List[SearchResult]:
        """
        Convert ZeroDB vector search results to SearchResult objects.

        Args:
            results: Raw results from ZeroDB vector search

        Returns:
            List of SearchResult objects
        """
        search_results = []

        for result in results:
            metadata = result.get("metadata", {})

            # Extract fields with fallbacks
            submission_id = (
                metadata.get("submission_id") or
                result.get("vector_id") or
                result.get("id") or
                ""
            )

            hackathon_id = metadata.get("hackathon_id", "")
            title = metadata.get("project_name") or metadata.get("title", "")
            description = metadata.get("description", "")

            # Get similarity score
            similarity = result.get("similarity") or result.get("score", 0.0)

            # Create SearchResult
            search_results.append(SearchResult(
                submission_id=submission_id,
                hackathon_id=hackathon_id,
                title=title,
                description=description,
                similarity_score=similarity,
                metadata=metadata
            ))

        return search_results


# Convenience function for quick searches
async def quick_search(
    zerodb_client: ZeroDBClient,
    query: str,
    hackathon_id: str,
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Quick search function for simple use cases.

    Args:
        zerodb_client: ZeroDB client instance
        query: Natural language search query
        hackathon_id: Hackathon to search within
        top_k: Number of results to return

    Returns:
        List of search result dictionaries

    Example:
        >>> results = await quick_search(
        ...     zerodb_client=client,
        ...     query="blockchain projects",
        ...     hackathon_id="hack-123"
        ... )
    """
    service = SearchService(zerodb_client)
    results = await service.search_by_query(
        query=query,
        hackathon_id=hackathon_id,
        top_k=top_k
    )
    return [r.to_dict() for r in results]
