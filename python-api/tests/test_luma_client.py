"""Tests for the Luma API client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from integrations.luma.client import LumaClient
from integrations.luma.exceptions import (
    LumaAuthError,
    LumaError,
    LumaNotFound,
    LumaRateLimitError,
    LumaTimeoutError,
)


@pytest.fixture
def luma_client():
    return LumaClient(api_key="test-key-123456789")


class TestLumaClientInit:
    def test_sets_api_key_header(self, luma_client):
        assert luma_client.api_key == "test-key-123456789"

    def test_default_base_url(self, luma_client):
        assert "luma" in luma_client.base_url.lower()

    def test_custom_base_url(self):
        client = LumaClient(api_key="key", base_url="https://custom.api.com")
        assert client.base_url == "https://custom.api.com"


class TestLumaClientRequests:
    @pytest.mark.asyncio
    async def test_verify_key_success(self, luma_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "usr-123", "name": "Test User"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(luma_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response):
            result = await luma_client.verify_key()
            assert result["id"] == "usr-123"
            assert result["name"] == "Test User"

    @pytest.mark.asyncio
    async def test_verify_key_auth_error(self, luma_client):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = {"error": "invalid key"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_response
        )

        with patch.object(luma_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(LumaAuthError):
                await luma_client.verify_key()

    @pytest.mark.asyncio
    async def test_list_events_success(self, luma_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entries": [{"id": "evt-1", "name": "Event 1"}],
            "next_cursor": None,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(luma_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response):
            result = await luma_client.list_events()
            assert len(result["entries"]) == 1
            assert result["entries"][0]["name"] == "Event 1"

    @pytest.mark.asyncio
    async def test_list_events_with_cursor(self, luma_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entries": [], "next_cursor": None}
        mock_response.raise_for_status = MagicMock()

        with patch.object(luma_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response) as mock_req:
            await luma_client.list_events(cursor="abc123")
            call_kwargs = mock_req.call_args
            assert "abc123" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_get_event_success(self, luma_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "evt-1", "name": "My Event"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(luma_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response):
            result = await luma_client.get_event("evt-1")
            assert result["name"] == "My Event"

    @pytest.mark.asyncio
    async def test_list_guests_success(self, luma_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entries": [
                {"user_email": "a@b.com", "user_name": "Alice", "approval_status": "approved"}
            ],
            "next_cursor": None,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(luma_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response):
            result = await luma_client.list_guests("evt-1")
            assert len(result["entries"]) == 1

    @pytest.mark.asyncio
    async def test_list_contacts_success(self, luma_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entries": [
                {"email": "c@d.com", "name": "Charlie", "event_approved_count": 3}
            ],
            "next_cursor": None,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(luma_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response):
            result = await luma_client.list_contacts()
            assert result["entries"][0]["email"] == "c@d.com"

    @pytest.mark.asyncio
    async def test_404_raises_not_found(self, luma_client):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.json.return_value = {"error": "not found"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_response
        )

        with patch.object(luma_client._http_client, "request", new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(LumaNotFound):
                await luma_client.get_event("evt-nonexistent")

    @pytest.mark.asyncio
    async def test_timeout_raises(self, luma_client):
        with patch.object(
            luma_client._http_client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("timed out"),
        ):
            with pytest.raises(LumaTimeoutError):
                await luma_client.verify_key()

    @pytest.mark.asyncio
    async def test_close(self, luma_client):
        with patch.object(luma_client._http_client, "aclose", new_callable=AsyncMock) as mock_close:
            await luma_client.close()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        client = LumaClient(api_key="test-key-123456789")
        with patch.object(client._http_client, "aclose", new_callable=AsyncMock) as mock_close:
            async with client as c:
                assert c is client
            mock_close.assert_called_once()
