"""
ZeroDB Embeddings API Wrapper

Provides methods for generating embeddings using ZeroDB's embedding service.
"""

from typing import Any, Optional


class EmbeddingsAPI:
    """
    Wrapper for ZeroDB Embeddings API operations.

    Provides methods for:
    - Generating embeddings for text using various models
    - Batch embedding generation
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
        text: str,
        model: str = "BAAI/bge-small-en-v1.5",
        namespace: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Generate embedding for a single text input.

        Args:
            text: Text to generate embedding for
            model: Embedding model to use (default: "BAAI/bge-small-en-v1.5")
            namespace: Optional namespace for organizing embeddings

        Returns:
            Dict containing:
                - embedding: List of floats (vector)
                - model: Model name used
                - dimensions: Number of dimensions

        Example:
            result = await client.embeddings.generate(
                text="This is a test document",
                model="BAAI/bge-small-en-v1.5"
            )
            embedding = result["embedding"]  # [0.1, 0.2, ...]
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/embeddings/generate"
        payload = {
            "text": text,
            "model": model,
        }
        if namespace:
            payload["namespace"] = namespace

        return await self.client._request("POST", path, json=payload)

    async def batch_generate(
        self,
        texts: list[str],
        model: str = "BAAI/bge-small-en-v1.5",
        namespace: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Generate embeddings for multiple texts in a single request.

        Args:
            texts: List of text strings to generate embeddings for
            model: Embedding model to use (default: "BAAI/bge-small-en-v1.5")
            namespace: Optional namespace for organizing embeddings

        Returns:
            Dict containing:
                - embeddings: List of embedding vectors
                - model: Model name used
                - dimensions: Number of dimensions
                - count: Number of embeddings generated

        Example:
            result = await client.embeddings.batch_generate(
                texts=["First document", "Second document"],
                model="BAAI/bge-small-en-v1.5"
            )
            embeddings = result["embeddings"]  # [[0.1, 0.2, ...], [0.3, 0.4, ...]]
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/embeddings/generate-batch"
        payload = {
            "texts": texts,
            "model": model,
        }
        if namespace:
            payload["namespace"] = namespace

        return await self.client._request("POST", path, json=payload)

    async def get_models(self) -> list[dict[str, Any]]:
        """
        Get list of available embedding models.

        Returns:
            List of model information dictionaries containing:
                - name: Model name
                - dimensions: Number of dimensions
                - description: Model description

        Example:
            models = await client.embeddings.get_models()
            for model in models:
                print(f"{model['name']}: {model['dimensions']} dimensions")
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/embeddings/models"
        response = await self.client._request("GET", path)
        return response.get("models", [])
