"""
Embedding Generation Service

Automatically generates and manages vector embeddings for hackathon submissions
using ZeroDB's Embeddings API for semantic search functionality.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from fastapi import status as http_status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)

# Configure logger
logger = logging.getLogger(__name__)

# Default embedding model
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_DIMENSIONS = 384


async def generate_submission_embedding(
    zerodb_client: ZeroDBClient,
    submission_id: str,
    hackathon_id: str,
    title: str,
    description: str,
    project_details: Optional[str] = None,
    track_id: Optional[str] = None,
    team_id: Optional[str] = None,
    status: str = "draft",
) -> Dict[str, Any]:
    """
    Generate and store embedding for a submission.

    Combines submission title, description, and project details into a single
    text representation, generates an embedding using ZeroDB's Embeddings API,
    and stores it in the vectors namespace for semantic search.

    Args:
        zerodb_client: ZeroDB client instance
        submission_id: Unique submission ID (used as vector_id)
        hackathon_id: Hackathon ID for namespace organization
        title: Submission project title
        description: Submission project description
        project_details: Optional additional project details
        track_id: Optional track ID for filtering
        team_id: Optional team ID for metadata
        status: Submission status (draft, submitted, scored)

    Returns:
        Dict containing:
            - vector_id: ID of the stored vector (same as submission_id)
            - dimensions: Number of embedding dimensions
            - namespace: Vector namespace used
            - text_length: Length of combined text

    Raises:
        ValueError: If title or description is empty
        HTTPException: 500 if embedding generation or storage fails
        HTTPException: 504 if request times out

    Example:
        >>> result = await generate_submission_embedding(
        ...     client,
        ...     submission_id="sub-123",
        ...     hackathon_id="hack-456",
        ...     title="AI Assistant",
        ...     description="An intelligent coding assistant using GPT-4",
        ...     track_id="ai-ml",
        ...     team_id="team-789"
        ... )
        >>> print(f"Stored vector with {result['dimensions']} dimensions")
    """
    # Validate inputs first (before try block to let ValueError propagate)
    if not title or not title.strip():
        raise ValueError("Title cannot be empty")
    if not description or not description.strip():
        raise ValueError("Description cannot be empty")

    try:
        # Combine text fields for embedding
        combined_text = _prepare_text_for_embedding(title, description, project_details)

        logger.info(
            f"Generating embedding for submission {submission_id} "
            f"({len(combined_text)} characters)"
        )

        # Generate embedding using ZeroDB Embeddings API
        embedding_result = await zerodb_client.embeddings.generate(
            text=combined_text,
            model=DEFAULT_MODEL,
        )

        embedding_vector = embedding_result.get("embedding")
        if not embedding_vector:
            raise ValueError("Embedding generation returned no vector")

        # Prepare metadata for vector storage
        metadata = {
            "submission_id": submission_id,
            "hackathon_id": hackathon_id,
            "title": title.strip(),
            "description": description.strip()[:500],  # Truncate for storage
            "status": status,
            "text_length": len(combined_text),
        }

        # Add optional metadata
        if track_id:
            metadata["track_id"] = track_id
        if team_id:
            metadata["team_id"] = team_id
        if project_details:
            metadata["has_project_details"] = True

        # Store embedding in vectors namespace
        namespace = f"hackathons/{hackathon_id}/submissions"
        await zerodb_client.vectors.upsert(
            vector_id=submission_id,
            embedding=embedding_vector,
            metadata=metadata,
            namespace=namespace,
        )

        logger.info(
            f"Successfully stored embedding for submission {submission_id} "
            f"in namespace {namespace}"
        )

        return {
            "vector_id": submission_id,
            "dimensions": len(embedding_vector),
            "namespace": namespace,
            "text_length": len(combined_text),
        }

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout generating embedding for submission {submission_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Embedding generation timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"Database error generating embedding for submission {submission_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embedding. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error generating embedding for submission {submission_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embedding. Please contact support.",
        )


async def update_submission_embedding(
    zerodb_client: ZeroDBClient,
    submission_id: str,
    hackathon_id: str,
    title: str,
    description: str,
    project_details: Optional[str] = None,
    track_id: Optional[str] = None,
    team_id: Optional[str] = None,
    status: str = "draft",
) -> Dict[str, Any]:
    """
    Update existing embedding for a submission.

    Regenerates the embedding with updated text and metadata. Uses upsert
    operation, so it will create the embedding if it doesn't exist.

    Args:
        zerodb_client: ZeroDB client instance
        submission_id: Submission ID to update embedding for
        hackathon_id: Hackathon ID
        title: Updated project title
        description: Updated project description
        project_details: Optional updated project details
        track_id: Optional track ID
        team_id: Optional team ID
        status: Updated submission status

    Returns:
        Dict containing updated vector information

    Raises:
        ValueError: If title or description is empty
        HTTPException: 500 if update fails
        HTTPException: 504 if request times out

    Example:
        >>> result = await update_submission_embedding(
        ...     client,
        ...     submission_id="sub-123",
        ...     hackathon_id="hack-456",
        ...     title="Updated AI Assistant",
        ...     description="An intelligent coding assistant with new features",
        ...     status="submitted"
        ... )
    """
    # Update is the same as generate - upsert will replace existing vector
    return await generate_submission_embedding(
        zerodb_client=zerodb_client,
        submission_id=submission_id,
        hackathon_id=hackathon_id,
        title=title,
        description=description,
        project_details=project_details,
        track_id=track_id,
        team_id=team_id,
        status=status,
    )


async def delete_submission_embedding(
    zerodb_client: ZeroDBClient,
    submission_id: str,
    hackathon_id: str,
) -> Dict[str, Any]:
    """
    Delete embedding for a submission.

    Removes the vector embedding from the vectors namespace when a submission
    is deleted.

    Args:
        zerodb_client: ZeroDB client instance
        submission_id: Submission ID to delete embedding for
        hackathon_id: Hackathon ID for namespace

    Returns:
        Dict with deletion confirmation containing:
            - success: True if deleted
            - vector_id: ID of deleted vector
            - namespace: Namespace where vector was deleted from

    Raises:
        HTTPException: 404 if embedding not found
        HTTPException: 500 if deletion fails
        HTTPException: 504 if request times out

    Example:
        >>> result = await delete_submission_embedding(
        ...     client,
        ...     submission_id="sub-123",
        ...     hackathon_id="hack-456"
        ... )
        >>> assert result["success"] is True
    """
    try:
        namespace = f"hackathons/{hackathon_id}/submissions"

        logger.info(f"Deleting embedding for submission {submission_id} from {namespace}")

        # Delete vector from namespace
        await zerodb_client.vectors.delete(
            vector_id=submission_id,
            namespace=namespace,
        )

        logger.info(f"Successfully deleted embedding for submission {submission_id}")

        return {
            "success": True,
            "vector_id": submission_id,
            "namespace": namespace,
        }

    except ZeroDBNotFound:
        # Vector not found - this is acceptable, may not have been created yet
        logger.warning(
            f"Embedding not found for submission {submission_id}, may not have been created"
        )
        return {
            "success": True,
            "vector_id": submission_id,
            "namespace": namespace,
            "message": "Embedding did not exist",
        }

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout deleting embedding for submission {submission_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except ZeroDBError as e:
        logger.error(
            f"Database error deleting embedding for submission {submission_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete embedding. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error deleting embedding for submission {submission_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete embedding. Please contact support.",
        )


async def search_similar_submissions(
    zerodb_client: ZeroDBClient,
    hackathon_id: str,
    query_text: str,
    top_k: int = 10,
    track_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    similarity_threshold: float = 0.7,
) -> List[Dict[str, Any]]:
    """
    Search for similar submissions using semantic search.

    Generates an embedding for the query text and searches for similar
    submission embeddings using cosine similarity.

    Args:
        zerodb_client: ZeroDB client instance
        hackathon_id: Hackathon ID to search within
        query_text: Text to search for (e.g., keywords, description)
        top_k: Number of results to return (default: 10)
        track_id: Optional filter by track ID
        status_filter: Optional filter by status (draft, submitted, scored)
        similarity_threshold: Minimum similarity score (0.0-1.0, default: 0.7)

    Returns:
        List of similar submissions with scores, each containing:
            - submission_id: Submission ID
            - score: Similarity score (0.0-1.0)
            - title: Submission title
            - description: Submission description
            - metadata: Additional metadata

    Raises:
        ValueError: If query_text is empty
        HTTPException: 500 if search fails
        HTTPException: 504 if request times out

    Example:
        >>> results = await search_similar_submissions(
        ...     client,
        ...     hackathon_id="hack-456",
        ...     query_text="AI-powered code assistant",
        ...     top_k=5,
        ...     track_id="ai-ml",
        ...     status_filter="submitted"
        ... )
        >>> for result in results:
        ...     print(f"{result['title']}: {result['score']:.2f}")
    """
    # Validate input first (before try block to let ValueError propagate)
    if not query_text or not query_text.strip():
        raise ValueError("Query text cannot be empty")

    try:
        logger.info(
            f"Searching for similar submissions in hackathon {hackathon_id} "
            f"with query: '{query_text[:100]}...'"
        )

        # Generate embedding for query
        embedding_result = await zerodb_client.embeddings.generate(
            text=query_text.strip(),
            model=DEFAULT_MODEL,
        )

        query_vector = embedding_result.get("embedding")
        if not query_vector:
            raise ValueError("Query embedding generation returned no vector")

        # Build metadata filter
        filter_dict = {}
        if track_id:
            filter_dict["track_id"] = track_id
        if status_filter:
            filter_dict["status"] = status_filter

        # Search for similar vectors
        namespace = f"hackathons/{hackathon_id}/submissions"
        results = await zerodb_client.vectors.search(
            query_vector=query_vector,
            top_k=top_k,
            namespace=namespace,
            filter=filter_dict if filter_dict else None,
            similarity_threshold=similarity_threshold,
        )

        logger.info(f"Found {len(results)} similar submissions")

        # Format results
        formatted_results = []
        for result in results:
            metadata = result.get("metadata", {})
            formatted_results.append(
                {
                    "submission_id": result.get("vector_id"),
                    "score": result.get("score", 0.0),
                    "title": metadata.get("title", ""),
                    "description": metadata.get("description", ""),
                    "track_id": metadata.get("track_id"),
                    "team_id": metadata.get("team_id"),
                    "status": metadata.get("status", "draft"),
                    "metadata": metadata,
                }
            )

        return formatted_results

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout searching similar submissions: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Search request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error searching similar submissions: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search submissions. Please contact support.",
        )

    except Exception as e:
        logger.error(f"Unexpected error searching similar submissions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search submissions. Please contact support.",
        )


async def batch_generate_embeddings(
    zerodb_client: ZeroDBClient,
    hackathon_id: str,
    submissions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generate embeddings for multiple submissions in batch.

    More efficient than generating embeddings one at a time. Useful for
    backfilling embeddings for existing submissions.

    Args:
        zerodb_client: ZeroDB client instance
        hackathon_id: Hackathon ID for namespace
        submissions: List of submission dicts, each containing:
            - submission_id: Unique ID
            - title: Project title
            - description: Project description
            - project_details: Optional project details
            - track_id: Optional track ID
            - team_id: Optional team ID
            - status: Submission status

    Returns:
        Dict containing:
            - success_count: Number of successfully generated embeddings
            - failed_count: Number of failed embeddings
            - failed_ids: List of submission IDs that failed
            - namespace: Namespace used

    Raises:
        HTTPException: 500 if batch operation fails
        HTTPException: 504 if request times out

    Example:
        >>> submissions = [
        ...     {
        ...         "submission_id": "sub-1",
        ...         "title": "Project 1",
        ...         "description": "Description 1",
        ...         "status": "submitted"
        ...     },
        ...     {
        ...         "submission_id": "sub-2",
        ...         "title": "Project 2",
        ...         "description": "Description 2",
        ...         "status": "submitted"
        ...     }
        ... ]
        >>> result = await batch_generate_embeddings(client, "hack-123", submissions)
        >>> print(f"Generated {result['success_count']} embeddings")
    """
    try:
        logger.info(f"Batch generating embeddings for {len(submissions)} submissions")

        # Prepare texts for batch embedding generation
        texts = []
        metadata_list = []

        for submission in submissions:
            # Combine text fields
            text = _prepare_text_for_embedding(
                submission.get("title", ""),
                submission.get("description", ""),
                submission.get("project_details"),
            )
            texts.append(text)

            # Prepare metadata
            metadata = {
                "submission_id": submission["submission_id"],
                "hackathon_id": hackathon_id,
                "title": submission.get("title", "").strip(),
                "description": submission.get("description", "").strip()[:500],
                "status": submission.get("status", "draft"),
                "text_length": len(text),
            }

            # Add optional fields
            if submission.get("track_id"):
                metadata["track_id"] = submission["track_id"]
            if submission.get("team_id"):
                metadata["team_id"] = submission["team_id"]

            metadata_list.append(metadata)

        # Generate embeddings in batch
        batch_result = await zerodb_client.embeddings.batch_generate(
            texts=texts,
            model=DEFAULT_MODEL,
        )

        embeddings = batch_result.get("embeddings", [])

        if len(embeddings) != len(submissions):
            raise ValueError(
                f"Embedding count mismatch: expected {len(submissions)}, got {len(embeddings)}"
            )

        # Prepare vectors for batch upsert
        vectors = []
        for i, submission in enumerate(submissions):
            vectors.append(
                {
                    "vector_id": submission["submission_id"],
                    "embedding": embeddings[i],
                    "metadata": metadata_list[i],
                }
            )

        # Batch upsert vectors
        namespace = f"hackathons/{hackathon_id}/submissions"
        await zerodb_client.vectors.batch_upsert(
            vectors=vectors,
            namespace=namespace,
        )

        logger.info(
            f"Successfully generated and stored {len(submissions)} embeddings "
            f"in namespace {namespace}"
        )

        return {
            "success_count": len(submissions),
            "failed_count": 0,
            "failed_ids": [],
            "namespace": namespace,
        }

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout in batch embedding generation: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Batch operation timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error in batch embedding generation: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate batch embeddings. Please contact support.",
        )

    except Exception as e:
        logger.error(f"Unexpected error in batch embedding generation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate batch embeddings. Please contact support.",
        )


def _prepare_text_for_embedding(
    title: str,
    description: str,
    project_details: Optional[str] = None,
) -> str:
    """
    Prepare combined text for embedding generation.

    Combines title, description, and optional project details into a single
    text representation with proper formatting and length limits.

    Args:
        title: Project title
        description: Project description
        project_details: Optional additional project details

    Returns:
        Combined text string optimized for embedding

    Example:
        >>> text = _prepare_text_for_embedding(
        ...     "AI Assistant",
        ...     "An intelligent coding assistant",
        ...     "Built with GPT-4 and Python"
        ... )
        >>> assert "AI Assistant" in text
    """
    # Start with title and description
    parts = []

    if title and title.strip():
        parts.append(f"Title: {title.strip()}")

    if description and description.strip():
        parts.append(f"Description: {description.strip()}")

    if project_details and project_details.strip():
        # Truncate project details if too long (embeddings work better with shorter text)
        details = project_details.strip()
        if len(details) > 1000:
            details = details[:1000] + "..."
        parts.append(f"Details: {details}")

    # Combine with newlines for better semantic understanding
    combined = "\n".join(parts)

    # Final length check (most embedding models have token limits)
    if len(combined) > 5000:
        combined = combined[:5000] + "..."

    return combined
