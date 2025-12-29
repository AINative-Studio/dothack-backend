"""
ZeroDB Memory API Wrapper

Provides methods for storing and retrieving AI agent memory context.
Supports session-based memory, semantic search, and context window management.
"""

from typing import Any, Dict, List, Optional

import logging

logger = logging.getLogger(__name__)


class MemoryAPI:
    """
    ZeroDB Memory API operations for AI agent persistent context.

    Features:
    - Store agent memories with role (user/assistant/system)
    - Retrieve context window for AI assistants
    - Semantic search across memories
    - Session and agent ID tracking
    - Token-aware context retrieval

    Example:
        >>> async with ZeroDBClient(api_key="...", project_id="...") as client:
        ...     # Store memory
        ...     await client.memory.store(
        ...         content="Judge prefers innovative AI solutions",
        ...         role="assistant",
        ...         agent_id="judge-123",
        ...         session_id="hackathon-456",
        ...         metadata={"category": "preference", "hackathon_id": "456"}
        ...     )
        ...
        ...     # Retrieve context
        ...     context = await client.memory.get_context(
        ...         session_id="hackathon-456",
        ...         max_tokens=4000
        ...     )
        ...
        ...     # Search memories
        ...     results = await client.memory.search(
        ...         query="What does the judge prefer?",
        ...         limit=5
        ...     )
    """

    def __init__(self, client):
        """
        Initialize Memory API wrapper.

        Args:
            client: ZeroDBClient instance
        """
        self._client = client

    async def store(
        self,
        content: str,
        role: str = "assistant",
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Store a memory in ZeroDB.

        Args:
            content: Memory content to store
            role: Message role (user, assistant, system)
            agent_id: Optional agent identifier (defaults to None)
            session_id: Optional session identifier (defaults to None)
            metadata: Optional additional metadata (user_id, hackathon_id, etc.)

        Returns:
            Dict with storage result including memory_id

        Raises:
            ZeroDBError: If storage fails
            ZeroDBTimeoutError: If request times out

        Example:
            >>> result = await memory.store(
            ...     content="Judge scored highly on innovation",
            ...     role="assistant",
            ...     agent_id="judge-123",
            ...     metadata={"user_id": "user-456", "hackathon_id": "hack-789"}
            ... )
        """
        payload = {
            "content": content,
            "role": role,
        }

        if agent_id:
            payload["agent_id"] = agent_id

        if session_id:
            payload["session_id"] = session_id

        if metadata:
            payload["metadata"] = metadata

        logger.debug(
            f"Storing memory: role={role}, agent_id={agent_id}, "
            f"session_id={session_id}, content_length={len(content)}"
        )

        result = await self._client._request(
            "POST",
            "/v1/memory/store",
            json=payload,
        )

        logger.info(
            f"Successfully stored memory with ID: {result.get('memory_id', 'unknown')}"
        )

        return result

    async def get_context(
        self,
        session_id: str,
        agent_id: Optional[str] = None,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """
        Retrieve context window for an AI assistant.

        Returns recent memories from the session, formatted for inclusion
        in AI prompts. Respects max_tokens limit to prevent context overflow.

        Args:
            session_id: Session identifier to retrieve context for
            agent_id: Optional agent identifier to filter by
            max_tokens: Maximum tokens to include in context (default: 4000)

        Returns:
            Dict with keys:
            - memories: List of memory objects
            - total_memories: Total count of memories
            - total_tokens: Estimated token count
            - truncated: Boolean indicating if context was truncated

        Raises:
            ZeroDBError: If retrieval fails
            ZeroDBTimeoutError: If request times out

        Example:
            >>> context = await memory.get_context(
            ...     session_id="hackathon-123",
            ...     max_tokens=4000
            ... )
            >>> print(f"Retrieved {len(context['memories'])} memories")
        """
        params = {
            "session_id": session_id,
            "max_tokens": max_tokens,
        }

        if agent_id:
            params["agent_id"] = agent_id

        logger.debug(
            f"Retrieving context: session_id={session_id}, "
            f"agent_id={agent_id}, max_tokens={max_tokens}"
        )

        result = await self._client._request(
            "GET",
            "/v1/memory/context",
            params=params,
        )

        logger.info(
            f"Retrieved {result.get('total_memories', 0)} memories "
            f"({result.get('total_tokens', 0)} tokens) for session {session_id}"
        )

        return result

    async def search(
        self,
        query: str,
        limit: int = 10,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        role: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Semantic search across memories.

        Uses vector similarity to find relevant memories based on the query.
        Supports filtering by agent, session, role, and custom metadata.

        Args:
            query: Search query text
            limit: Maximum number of results to return (default: 10)
            agent_id: Optional agent ID filter
            session_id: Optional session ID filter
            role: Optional role filter (user, assistant, system)
            metadata_filter: Optional metadata filters (e.g., {"hackathon_id": "123"})

        Returns:
            Dict with keys:
            - results: List of memory objects with similarity scores
            - total_results: Total count of matching memories
            - query: Original search query

        Raises:
            ZeroDBError: If search fails
            ZeroDBTimeoutError: If request times out

        Example:
            >>> results = await memory.search(
            ...     query="What scoring patterns does this judge have?",
            ...     limit=5,
            ...     agent_id="judge-123"
            ... )
            >>> for result in results['results']:
            ...     print(f"Similarity: {result['similarity']}, Content: {result['content']}")
        """
        payload = {
            "query": query,
            "limit": limit,
        }

        if agent_id:
            payload["agent_id"] = agent_id

        if session_id:
            payload["session_id"] = session_id

        if role:
            payload["role"] = role

        if metadata_filter:
            payload["metadata_filter"] = metadata_filter

        logger.debug(
            f"Searching memories: query='{query[:50]}...', limit={limit}, "
            f"agent_id={agent_id}, session_id={session_id}"
        )

        result = await self._client._request(
            "POST",
            "/v1/memory/search",
            json=payload,
        )

        logger.info(
            f"Search returned {result.get('total_results', 0)} results for query: '{query[:30]}...'"
        )

        return result

    async def delete(
        self,
        memory_id: str,
    ) -> Dict[str, Any]:
        """
        Delete a specific memory by ID.

        Args:
            memory_id: Unique identifier of the memory to delete

        Returns:
            Dict with deletion confirmation

        Raises:
            ZeroDBNotFound: If memory doesn't exist
            ZeroDBError: If deletion fails
            ZeroDBTimeoutError: If request times out

        Example:
            >>> result = await memory.delete("mem-abc-123")
            >>> print(result['success'])
            True
        """
        logger.debug(f"Deleting memory: memory_id={memory_id}")

        result = await self._client._request(
            "DELETE",
            f"/v1/memory/{memory_id}",
        )

        logger.info(f"Successfully deleted memory {memory_id}")

        return result

    async def delete_session(
        self,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Delete all memories for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dict with deletion confirmation and count

        Raises:
            ZeroDBError: If deletion fails
            ZeroDBTimeoutError: If request times out

        Example:
            >>> result = await memory.delete_session("hackathon-123")
            >>> print(f"Deleted {result['deleted_count']} memories")
        """
        logger.debug(f"Deleting session memories: session_id={session_id}")

        result = await self._client._request(
            "DELETE",
            f"/v1/memory/session/{session_id}",
        )

        logger.info(
            f"Successfully deleted {result.get('deleted_count', 0)} memories "
            f"for session {session_id}"
        )

        return result
