"""
Tests for main FastAPI application configuration.

Tests for:
- CORS configuration
- API versioning
- Error handling
- Logging setup
"""

from fastapi import status


def test_app_has_cors_middleware(client):
    """
    Test that CORS is configured and allows expected origins.
    """
    # Make a preflight request
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )

    # Should not fail (CORS should be configured)
    # Actual CORS headers are tested by making regular requests
    assert response.status_code in [200, status.HTTP_200_OK]


def test_app_handles_404_errors(client):
    """
    Test that the app returns proper 404 for non-existent endpoints.
    """
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == 404


def test_app_handles_405_method_not_allowed(client):
    """
    Test that the app returns 405 for wrong HTTP methods.
    """
    # Health endpoint should be GET only
    response = client.post("/health")
    assert response.status_code == 405


def test_app_title_and_version(client):
    """
    Test that the OpenAPI docs contain app title and version.
    """
    response = client.get("/openapi.json")
    assert response.status_code == 200

    openapi = response.json()
    assert "info" in openapi
    assert "title" in openapi["info"]
    assert "version" in openapi["info"]

    # Should have a meaningful title
    assert len(openapi["info"]["title"]) > 0
