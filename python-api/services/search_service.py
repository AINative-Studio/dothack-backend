"""
Search Service

Provides semantic search functionality across hackathons, submissions, projects, and teams.
Uses ZeroDB embeddings API for natural language search with < 200ms target response time.
"""

import logging
import time
from typing import Any, Optional

from fastapi import HTTPException, status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBTimeoutError

logger = logging.getLogger(__name__)


class SearchService:
    """Service for semantic search operations."""

    def __init__(self, zerodb_client: ZeroDBClient):
        """
        Initialize search service.

        Args:
            zerodb_client: ZeroDB client instance
        """
        self.zerodb = zerodb_client

    async def search_all(
        self,
        query: str,
        entity_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        similarity_threshold: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        Universal search across all hackathons and entities.

        Searches across submissions, projects, teams, and hackathons using
        semantic similarity.

        Args:
            query: Natural language search query
            entity_type: Filter by entity type (submission, project, team, hackathon)
            status: Filter by status (e.g., SUBMITTED, DRAFT, LIVE)
            limit: Maximum results (1-100)
            offset: Pagination offset
            similarity_threshold: Minimum similarity score (0.0-1.0)

        Returns:
            Dict containing:
            - results: List of search results with scores and metadata
            - total_results: Total count of matches
            - execution_time_ms: Search execution time

        Raises:
            HTTPException: 500 if search fails
            HTTPException: 504 if search times out
        """
        start_time = time.time()

        try:
            # Build metadata filter
            metadata_filter = {}
            if entity_type:
                metadata_filter["entity_type"] = entity_type
            if status:
                metadata_filter["status"] = status

            # Search across all namespaces (use global namespace)
            namespace = "global"

            # Perform semantic search
            search_results = await self.zerodb.embeddings.search(
                query=query,
                namespace=namespace,
                top_k=limit + offset,  # Get extra for pagination
                filter=metadata_filter if metadata_filter else None,
                similarity_threshold=similarity_threshold,
                include_metadata=True,
            )

            # Apply pagination
            paginated_results = search_results[offset : offset + limit]

            # Transform results to match API schema
            transformed_results = []
            for result in paginated_results:
                transformed_results.append(
                    {
                        "id": result.get("id"),
                        "score": result.get("score", 0.0),
                        "metadata": result.get("metadata", {}),
                    }
                )

            execution_time = (time.time() - start_time) * 1000  # Convert to ms

            logger.info(
                f"Universal search completed: query='{query}', "
                f"results={len(transformed_results)}, "
                f"execution_time={execution_time:.2f}ms"
            )

            return {
                "results": transformed_results,
                "total_results": len(search_results),
                "execution_time_ms": round(execution_time, 2),
            }

        except ZeroDBTimeoutError as e:
            logger.error(f"Search timeout: {e}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Search request timed out. Please try again.",
            )
        except ZeroDBError as e:
            logger.error(f"Search failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to execute search. Please try again.",
            )

    async def search_hackathon(
        self,
        hackathon_id: str,
        query: str,
        entity_type: Optional[str] = None,
        track_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        similarity_threshold: Optional[float] = 0.5,
    ) -> dict[str, Any]:
        """
        Search within a specific hackathon.

        Performs semantic search scoped to a hackathon, with optional filtering
        by track, entity type, and status.

        Args:
            hackathon_id: Hackathon UUID to search within
            query: Natural language search query
            entity_type: Filter by entity type (submission, project, team)
            track_id: Filter by track ID
            status: Filter by status (e.g., SUBMITTED, DRAFT)
            limit: Maximum results (1-100)
            offset: Pagination offset
            similarity_threshold: Minimum similarity score (0.0-1.0)

        Returns:
            Dict containing:
            - results: List of search results with scores and metadata
            - total_results: Total count of matches
            - execution_time_ms: Search execution time
            - hackathon_id: The hackathon scope

        Raises:
            HTTPException: 404 if hackathon not found
            HTTPException: 500 if search fails
            HTTPException: 504 if search times out

        Performance:
            Target: < 200ms execution time
        """
        start_time = time.time()

        try:
            # Verify hackathon exists
            hackathon_rows = await self.zerodb.tables.query_rows(
                "hackathons",
                filter={"hackathon_id": hackathon_id},
                limit=1,
            )

            if not hackathon_rows:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Hackathon {hackathon_id} not found",
                )

            # Build metadata filter
            metadata_filter = {"hackathon_id": hackathon_id}
            if entity_type:
                metadata_filter["entity_type"] = entity_type
            if track_id:
                metadata_filter["track_id"] = track_id
            if status:
                metadata_filter["status"] = status

            # Use hackathon-scoped namespace
            namespace = f"hackathons/{hackathon_id}"

            # Perform semantic search
            search_results = await self.zerodb.embeddings.search(
                query=query,
                namespace=namespace,
                top_k=limit + offset,  # Get extra for pagination
                filter=metadata_filter,
                similarity_threshold=similarity_threshold,
                include_metadata=True,
            )

            # Apply pagination
            paginated_results = search_results[offset : offset + limit]

            # Transform results to match API schema
            transformed_results = []
            for result in paginated_results:
                transformed_results.append(
                    {
                        "id": result.get("id"),
                        "score": result.get("score", 0.0),
                        "metadata": result.get("metadata", {}),
                    }
                )

            execution_time = (time.time() - start_time) * 1000  # Convert to ms

            # Log performance warning if > 200ms
            if execution_time > 200:
                logger.warning(
                    f"Search exceeded target time: "
                    f"hackathon={hackathon_id}, "
                    f"execution_time={execution_time:.2f}ms"
                )
            else:
                logger.info(
                    f"Hackathon search completed: "
                    f"hackathon={hackathon_id}, "
                    f"query='{query}', "
                    f"results={len(transformed_results)}, "
                    f"execution_time={execution_time:.2f}ms"
                )

            return {
                "results": transformed_results,
                "total_results": len(search_results),
                "execution_time_ms": round(execution_time, 2),
                "hackathon_id": hackathon_id,
            }

        except HTTPException:
            raise
        except ZeroDBTimeoutError as e:
            logger.error(f"Search timeout: hackathon={hackathon_id}, error={e}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Search request timed out. Please try again.",
            )
        except ZeroDBError as e:
            logger.error(f"Search failed: hackathon={hackathon_id}, error={e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to execute search. Please try again.",
            )
