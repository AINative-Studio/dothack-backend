"""
ZeroDB Vectors API Wrapper

Provides methods for vector embeddings and semantic search.
"""

from typing import Any, Optional


class VectorsAPI:
    """
    Wrapper for ZeroDB Vectors API operations.

    Provides methods for:
    - Upserting vectors (single and batch)
    - Searching vectors by similarity
    - Deleting vectors
    - Getting vector details
    - Listing vectors
    """

    def __init__(self, client):
        """
        Initialize VectorsAPI wrapper.

        Args:
            client: ZeroDBClient instance
        """
        self.client = client

    async def upsert(
        self,
        vector_id: str,
        embedding: list[float],
        metadata: Optional[dict[str, Any]] = None,
        namespace: str = "default",
    ) -> dict[str, Any]:
        """
        Upsert a single vector embedding.

        Args:
            vector_id: Unique identifier for the vector
            embedding: Vector embedding (list of floats)
            metadata: Optional metadata to store with the vector
            namespace: Vector namespace (default: "default")

        Returns:
            Dict with upsert confirmation

        Example:
            await client.vectors.upsert(
                vector_id="doc-123",
                embedding=[0.1, 0.2, 0.3, ...],
                metadata={"title": "Document 123", "type": "blog"},
                namespace="submissions"
            )
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/vectors/upsert"
        payload = {
            "vector_id": vector_id,
            "embedding": embedding,
            "namespace": namespace,
        }
        if metadata:
            payload["metadata"] = metadata

        return await self.client._request("POST", path, json=payload)

    async def batch_upsert(
        self,
        vectors: list[dict[str, Any]],
        namespace: str = "default",
    ) -> dict[str, Any]:
        """
        Upsert multiple vectors in a single request.

        Args:
            vectors: List of vector objects, each containing:
                - vector_id: Unique identifier
                - embedding: Vector embedding
                - metadata: Optional metadata
            namespace: Vector namespace (default: "default")

        Returns:
            Dict with batch upsert confirmation

        Example:
            vectors = [
                {
                    "vector_id": "doc-1",
                    "embedding": [0.1, 0.2, ...],
                    "metadata": {"title": "Doc 1"}
                },
                {
                    "vector_id": "doc-2",
                    "embedding": [0.3, 0.4, ...],
                    "metadata": {"title": "Doc 2"}
                }
            ]
            await client.vectors.batch_upsert(vectors, namespace="submissions")
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/vectors/upsert-batch"
        payload = {"vectors": vectors, "namespace": namespace}
        return await self.client._request("POST", path, json=payload)

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        namespace: str = "default",
        filter: Optional[dict[str, Any]] = None,
        similarity_threshold: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar vectors using cosine similarity.

        Args:
            query_vector: Query embedding to search for
            top_k: Number of results to return (default: 10)
            namespace: Vector namespace to search in
            filter: Optional metadata filter
            similarity_threshold: Minimum similarity score (0.0 - 1.0)

        Returns:
            List of similar vectors with scores

        Example:
            results = await client.vectors.search(
                query_vector=[0.1, 0.2, ...],
                top_k=5,
                namespace="submissions",
                filter={"track_id": "ai-ml"},
                similarity_threshold=0.7
            )
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/vectors/search"
        payload = {
            "query_vector": query_vector,
            "top_k": top_k,
            "namespace": namespace,
        }
        if filter:
            payload["filter"] = filter
        if similarity_threshold is not None:
            payload["similarity_threshold"] = similarity_threshold

        response = await self.client._request("POST", path, json=payload)
        return response.get("results", [])

    async def delete(self, vector_id: str, namespace: str = "default") -> dict[str, Any]:
        """
        Delete a vector by ID.

        Args:
            vector_id: ID of the vector to delete
            namespace: Vector namespace

        Returns:
            Dict with deletion confirmation
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/vectors/{vector_id}"
        params = {"namespace": namespace}
        return await self.client._request("DELETE", path, params=params)

    async def get(self, vector_id: str, namespace: str = "default") -> dict[str, Any]:
        """
        Get a vector by ID.

        Args:
            vector_id: ID of the vector to retrieve
            namespace: Vector namespace

        Returns:
            Dict with vector details
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/vectors/{vector_id}"
        params = {"namespace": namespace}
        return await self.client._request("GET", path, params=params)

    async def list(
        self,
        namespace: str = "default",
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        List vectors in a namespace.

        Args:
            namespace: Vector namespace
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of vectors
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/vectors"
        params = {"namespace": namespace, "skip": skip, "limit": limit}
        response = await self.client._request("GET", path, params=params)
        return response.get("vectors", [])
