"""Tests for the ZeroPipeline API client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from integrations.zeropipeline.client import ZeroPipelineClient
from integrations.zeropipeline.exceptions import (
    ZeroPipelineAuthError,
    ZeroPipelineError,
    ZeroPipelineNotFound,
    ZeroPipelineRateLimitError,
    ZeroPipelineTimeoutError,
)


@pytest.fixture
def zp_client():
    return ZeroPipelineClient(api_key="test-key-123456789")


class TestZeroPipelineClientInit:
    def test_sets_api_key(self, zp_client):
        assert zp_client.api_key == "test-key-123456789"

    def test_default_base_url(self, zp_client):
        assert "pipeline" in zp_client.base_url.lower()

    def test_custom_base_url(self):
        client = ZeroPipelineClient(api_key="test-key-123456789", base_url="https://custom.api.com")
        assert client.base_url == "https://custom.api.com"


class TestZeroPipelineClientRequests:
    @pytest.mark.asyncio
    async def test_verify_key_success(self, zp_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "usr-123", "email": "test@test.com"}
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b'{"id": "usr-123", "email": "test@test.com"}'

        with patch.object(zp_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response):
            result = await zp_client.verify_key()
            assert result["id"] == "usr-123"
            assert result["email"] == "test@test.com"

    @pytest.mark.asyncio
    async def test_verify_key_auth_error(self, zp_client):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = {"error": "invalid key"}
        mock_response.content = b'{"error": "invalid key"}'
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_response
        )

        with patch.object(zp_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(ZeroPipelineAuthError):
                await zp_client.verify_key()

    @pytest.mark.asyncio
    async def test_list_pipelines_success(self, zp_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {"id": "pip-1", "name": "Sales Pipeline", "stages": [], "deals": []},
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b'{"items": []}'

        with patch.object(zp_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response):
            result = await zp_client.list_pipelines()
            assert len(result["items"]) == 1
            assert result["items"][0]["name"] == "Sales Pipeline"

    @pytest.mark.asyncio
    async def test_list_deals_success(self, zp_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {"id": "deal-1", "title": "Big Deal", "value": 5000.0, "status": "open"},
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b'{"items": []}'

        with patch.object(zp_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response):
            result = await zp_client.list_deals()
            assert len(result["items"]) == 1
            assert result["items"][0]["title"] == "Big Deal"

    @pytest.mark.asyncio
    async def test_list_deals_with_pipeline_filter(self, zp_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": [], "total": 0}
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b'{"items": []}'

        with patch.object(zp_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response) as mock_req:
            await zp_client.list_deals(pipeline_id="pip-abc")
            call_kwargs = mock_req.call_args
            assert "pip-abc" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_list_customers_success(self, zp_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {"id": "cust-1", "name": "Acme Corp", "email": "acme@corp.com"},
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b'{"items": []}'

        with patch.object(zp_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response):
            result = await zp_client.list_customers()
            assert len(result["items"]) == 1
            assert result["items"][0]["name"] == "Acme Corp"

    @pytest.mark.asyncio
    async def test_get_deal_success(self, zp_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "deal-1", "title": "Big Deal", "value": 5000.0}
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b'{"id": "deal-1"}'

        with patch.object(zp_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response):
            result = await zp_client.get_deal("deal-1")
            assert result["id"] == "deal-1"
            assert result["title"] == "Big Deal"

    @pytest.mark.asyncio
    async def test_get_analytics_dashboard(self, zp_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_deals": 42,
            "total_customers": 100,
            "total_revenue": 250000.0,
            "pipeline_count": 3,
        }
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b'{"total_deals": 42}'

        with patch.object(zp_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response):
            result = await zp_client.get_analytics_dashboard()
            assert result["total_deals"] == 42
            assert result["total_customers"] == 100

    @pytest.mark.asyncio
    async def test_404_raises_not_found(self, zp_client):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.json.return_value = {"error": "not found"}
        mock_response.content = b'{"error": "not found"}'
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_response
        )

        with patch.object(zp_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(ZeroPipelineNotFound):
                await zp_client.get_deal("deal-nonexistent")

    @pytest.mark.asyncio
    async def test_timeout_raises(self, zp_client):
        with patch.object(
            zp_client._http_client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("timed out"),
        ):
            with pytest.raises(ZeroPipelineTimeoutError):
                await zp_client.verify_key()

    @pytest.mark.asyncio
    async def test_close(self, zp_client):
        with patch.object(zp_client._http_client, "aclose", new_callable=AsyncMock) as mock_close:
            await zp_client.close()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        client = ZeroPipelineClient(api_key="test-key-123456789")
        with patch.object(client._http_client, "aclose", new_callable=AsyncMock) as mock_close:
            async with client as c:
                assert c is client
            mock_close.assert_called_once()
