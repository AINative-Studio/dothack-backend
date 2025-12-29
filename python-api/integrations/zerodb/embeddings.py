"""
ZeroDB Embeddings API Wrapper

Provides methods for text embedding generation and semantic search.
Uses BAAI/bge-small-en-v1.5 model (384 dimensions).
"""

from typing import Any, Optional


class EmbeddingsAPI:
    """
    Wrapper for ZeroDB Embeddings API operations.

    Provides methods for:
    - Generating embeddings from text
    - Embedding and storing documents
    - Semantic search with natural language queries

    Model: BAAI/bge-small-en-v1.5 (384 dimensions)
    """

    def __init__(self, client):
        """
        Initialize EmbeddingsAPI wrapper.

        Args:
            client: ZeroDBClient instance
        """
        self.client = client

    async def generate(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        Generate embeddings for given texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (384 dimensions each)

        Example:
            embeddings = await client.embeddings.generate([
                "Machine learning project for healthcare",
                "AI-powered chatbot for customer support"
            ])
        """
        path = f"/v1/public/projects/{self.client.project_id}/embeddings/generate"
        payload = {"texts": texts}

        response = await self.client._request("POST", path, json=payload)
        return response.get("embeddings", [])

    async def embed_and_store(
        self,
        documents: list[dict[str, Any]],
        namespace: str,
        text_field: str = "text",
    ) -> dict[str, Any]:
        """
        Generate embeddings and store them in the vector database.

        Args:
            documents: List of documents to embed and store
                Each document must have:
                - id: Unique identifier
                - text (or custom text_field): Text to embed
                - metadata: Optional additional data
            namespace: Vector namespace for organization
            text_field: Name of the field containing text to embed (default: "text")

        Returns:
            Dict with count of stored embeddings

        Example:
            await client.embeddings.embed_and_store(
                documents=[
                    {
                        "id": "submission-123",
                        "text": "Our project uses AI to detect diseases...",
                        "metadata": {
                            "hackathon_id": "hack-456",
                            "track_id": "ai-track",
                            "team_id": "team-789"
                        }
                    }
                ],
                namespace="hackathons/hack-456/submissions"
            )
        """
        path = f"/v1/public/projects/{self.client.project_id}/embeddings/embed-and-store"
        payload = {
            "documents": documents,
            "namespace": namespace,
            "text_field": text_field,
        }

        return await self.client._request("POST", path, json=payload)

    async def search(
        self,
        query: str,
        namespace: str,
        top_k: int = 10,
        filter: Optional[dict[str, Any]] = None,
        similarity_threshold: Optional[float] = None,
        include_metadata: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Perform semantic search using natural language query.

        Automatically converts query text to embedding and searches for similar vectors.

        Args:
            query: Natural language search query
            namespace: Vector namespace to search in
            top_k: Number of results to return (default: 10)
            filter: Optional metadata filter (e.g., {"track_id": "ai-track"})
            similarity_threshold: Minimum similarity score 0.0-1.0 (default: None)
            include_metadata: Include metadata in results (default: True)

        Returns:
            List of search results, each containing:
            - id: Document ID
            - score: Similarity score (0.0 - 1.0)
            - metadata: Document metadata (if include_metadata=True)

        Example:
            results = await client.embeddings.search(
                query="machine learning healthcare projects",
                namespace="hackathons/hack-456/submissions",
                top_k=10,
                filter={"track_id": "ai-ml-track"},
                similarity_threshold=0.7
            )

            for result in results:
                print(f"ID: {result['id']}, Score: {result['score']}")
        """
        path = f"/v1/public/projects/{self.client.project_id}/embeddings/search"
        payload = {
            "query": query,
            "namespace": namespace,
            "top_k": top_k,
            "include_metadata": include_metadata,
        }

        if filter:
            payload["filter"] = filter
        if similarity_threshold is not None:
            payload["similarity_threshold"] = similarity_threshold

        response = await self.client._request("POST", path, json=payload)
        return response.get("results", [])
