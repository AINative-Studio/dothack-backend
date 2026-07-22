"""Tests for the Luma Integration Service."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from integrations.luma.exceptions import LumaAuthError, LumaError
from integrations.zerodb.exceptions import ZeroDBNotFound
from services.luma_integration_service import LumaIntegrationService


@pytest.fixture
def mock_zerodb():
    client = MagicMock()
    client.tables = MagicMock()
    client.tables.query_rows = AsyncMock(return_value=[])
    client.tables.insert_rows = AsyncMock()
    client.tables.update_row = AsyncMock()
    client.tables.delete_row = AsyncMock()
    return client


@pytest.fixture
def service(mock_zerodb):
    return LumaIntegrationService(mock_zerodb)


@pytest.fixture
def connected_row():
    return {
        "row_data": {
            "_row_id": "row-123",
            "id": str(uuid.uuid4()),
            "user_id": "user-1",
            "integration_type": "luma",
            "api_key_encrypted": "",
            "calendar_name": "Test Calendar",
            "status": "connected",
            "sync_options": json.dumps({"events": True, "guests": True, "contacts": False}),
            "last_synced_at": None,
        }
    }


class TestGetStatus:
    @pytest.mark.asyncio
    async def test_not_connected(self, service, mock_zerodb):
        mock_zerodb.tables.query_rows.return_value = []
        result = await service.get_status("user-1")
        assert result["connected"] is False

    @pytest.mark.asyncio
    async def test_connected(self, service, mock_zerodb, connected_row):
        mock_zerodb.tables.query_rows.return_value = [connected_row]
        result = await service.get_status("user-1")
        assert result["connected"] is True
        assert result["calendar_name"] == "Test Calendar"
        assert result["sync_options"]["events"] is True

    @pytest.mark.asyncio
    async def test_zerodb_not_found_table(self, service, mock_zerodb):
        mock_zerodb.tables.query_rows.side_effect = ZeroDBNotFound("integration_settings not found")
        result = await service.get_status("user-1")
        assert result["connected"] is False


class TestConnect:
    @pytest.mark.asyncio
    async def test_connect_new(self, service, mock_zerodb):
        mock_zerodb.tables.query_rows.return_value = []

        mock_client = AsyncMock()
        mock_client.verify_key.return_value = {"name": "My Cal"}
        mock_client.close = AsyncMock()

        with patch("services.luma_integration_service.LumaClient", return_value=mock_client):
            with patch("services.luma_integration_service.encrypt_value", return_value="enc-key"):
                result = await service.connect("user-1", "luma-api-key-12345")

        assert result["success"] is True
        assert result["calendar_name"] == "My Cal"
        assert result["status"] == "connected"
        mock_zerodb.tables.insert_rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_update_existing(self, service, mock_zerodb, connected_row):
        mock_zerodb.tables.query_rows.return_value = [connected_row]

        mock_client = AsyncMock()
        mock_client.verify_key.return_value = {"name": "Updated Cal"}
        mock_client.close = AsyncMock()

        with patch("services.luma_integration_service.LumaClient", return_value=mock_client):
            with patch("services.luma_integration_service.encrypt_value", return_value="enc-key"):
                result = await service.connect("user-1", "new-key-12345678")

        assert result["success"] is True
        assert result["calendar_name"] == "Updated Cal"
        mock_zerodb.tables.update_row.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_invalid_key(self, service):
        mock_client = AsyncMock()
        mock_client.verify_key.side_effect = LumaAuthError("invalid")
        mock_client.close = AsyncMock()

        with patch("services.luma_integration_service.LumaClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await service.connect("user-1", "bad-key-12345")
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_connect_luma_api_error(self, service):
        mock_client = AsyncMock()
        mock_client.verify_key.side_effect = LumaError("server error")
        mock_client.close = AsyncMock()

        with patch("services.luma_integration_service.LumaClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await service.connect("user-1", "some-key-12345")
            assert exc_info.value.status_code == 502


class TestDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_success(self, service, mock_zerodb, connected_row):
        mock_zerodb.tables.query_rows.return_value = [connected_row]
        result = await service.disconnect("user-1")
        assert result["success"] is True
        mock_zerodb.tables.delete_row.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_not_connected(self, service, mock_zerodb):
        mock_zerodb.tables.query_rows.return_value = []
        with pytest.raises(HTTPException) as exc_info:
            await service.disconnect("user-1")
        assert exc_info.value.status_code == 404


class TestUpdateSyncOptions:
    @pytest.mark.asyncio
    async def test_update_success(self, service, mock_zerodb, connected_row):
        mock_zerodb.tables.query_rows.return_value = [connected_row]
        result = await service.update_sync_options(
            "user-1", {"events": False, "guests": True, "contacts": True}
        )
        assert result["connected"] is True
        mock_zerodb.tables.update_row.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_connected(self, service, mock_zerodb):
        mock_zerodb.tables.query_rows.return_value = []
        with pytest.raises(HTTPException) as exc_info:
            await service.update_sync_options("user-1", {"events": True, "guests": True, "contacts": False})
        assert exc_info.value.status_code == 404


class TestListLumaEvents:
    @pytest.mark.asyncio
    async def test_list_events(self, service, mock_zerodb, connected_row):
        mock_zerodb.tables.query_rows.return_value = [connected_row]

        mock_client = AsyncMock()
        mock_client.list_events.return_value = {
            "entries": [
                {"id": "evt-1", "name": "Hackathon", "start_at": "2025-01-01T00:00:00Z",
                 "end_at": "2025-01-03T00:00:00Z", "location_type": "online",
                 "cover_url": "https://img.com/1.jpg", "guest_count": 42, "url": "https://lu.ma/test"},
            ],
            "next_cursor": None,
        }
        mock_client.close = AsyncMock()

        with patch("services.luma_integration_service.decrypt_value", return_value="key"):
            with patch("services.luma_integration_service.LumaClient", return_value=mock_client):
                result = await service.list_luma_events("user-1")

        assert result["total"] == 1
        assert result["events"][0]["event_id"] == "evt-1"
        assert result["events"][0]["name"] == "Hackathon"
        assert result["events"][0]["is_online"] is True
        assert result["events"][0]["guest_count"] == 42

    @pytest.mark.asyncio
    async def test_list_events_not_connected(self, service, mock_zerodb):
        mock_zerodb.tables.query_rows.return_value = []
        with pytest.raises(HTTPException) as exc_info:
            await service.list_luma_events("user-1")
        assert exc_info.value.status_code == 404


class TestImportEvent:
    @pytest.mark.asyncio
    async def test_import_creates_hackathon(self, service, mock_zerodb, connected_row):
        mock_zerodb.tables.query_rows.return_value = [connected_row]

        mock_client = AsyncMock()
        mock_client.get_event.return_value = {
            "name": "AI Builders Hackathon",
            "description_md": "Build AI stuff",
            "start_at": "2025-06-01T00:00:00Z",
            "end_at": "2025-06-03T00:00:00Z",
            "location_type": "online",
            "cover_url": "https://img.com/cover.jpg",
            "url": "https://lu.ma/ai-hack",
        }
        mock_client.close = AsyncMock()

        with patch("services.luma_integration_service.decrypt_value", return_value="key"):
            with patch("services.luma_integration_service.LumaClient", return_value=mock_client):
                result = await service.import_event("user-1", "evt-ai-hack")

        assert result["success"] is True
        assert result["hackathon_name"] == "AI Builders Hackathon"
        assert result["hackathon_id"] is not None
        assert mock_zerodb.tables.insert_rows.call_count == 2


class TestSyncGuests:
    @pytest.mark.asyncio
    async def test_sync_imports_new_guests(self, service, mock_zerodb, connected_row):
        mock_zerodb.tables.query_rows.side_effect = [
            [connected_row],  # _get_settings for _get_luma_client
            [],  # existing hackathon_participants
            [connected_row],  # _get_settings for last_synced_at update
        ]

        mock_client = AsyncMock()
        mock_client.list_guests.return_value = {
            "entries": [
                {"user_email": "alice@test.com", "user_name": "Alice", "approval_status": "approved"},
                {"user_email": "bob@test.com", "user_name": "Bob", "approval_status": "approved"},
            ],
            "next_cursor": None,
        }
        mock_client.close = AsyncMock()

        with patch("services.luma_integration_service.decrypt_value", return_value="key"):
            with patch("services.luma_integration_service.LumaClient", return_value=mock_client):
                with patch("services.authorization.check_organizer", new_callable=AsyncMock):
                    result = await service.sync_guests("user-1", "evt-1", "hack-1")

        assert result["success"] is True
        assert result["imported"] == 2
        assert result["skipped"] == 0
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_sync_skips_duplicates(self, service, mock_zerodb, connected_row):
        existing_participant = {
            "row_data": {
                "hackathon_id": "hack-1",
                "metadata": json.dumps({"ainative_user_email": "alice@test.com"}),
            }
        }
        mock_zerodb.tables.query_rows.side_effect = [
            [connected_row],  # _get_settings
            [existing_participant],  # existing participants
            [connected_row],  # _get_settings for update
        ]

        mock_client = AsyncMock()
        mock_client.list_guests.return_value = {
            "entries": [
                {"user_email": "alice@test.com", "user_name": "Alice", "approval_status": "approved"},
                {"user_email": "charlie@test.com", "user_name": "Charlie", "approval_status": "approved"},
            ],
            "next_cursor": None,
        }
        mock_client.close = AsyncMock()

        with patch("services.luma_integration_service.decrypt_value", return_value="key"):
            with patch("services.luma_integration_service.LumaClient", return_value=mock_client):
                with patch("services.authorization.check_organizer", new_callable=AsyncMock):
                    result = await service.sync_guests("user-1", "evt-1", "hack-1")

        assert result["imported"] == 1
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_sync_skips_rejected_guests(self, service, mock_zerodb, connected_row):
        mock_zerodb.tables.query_rows.side_effect = [
            [connected_row],
            [],
            [connected_row],
        ]

        mock_client = AsyncMock()
        mock_client.list_guests.return_value = {
            "entries": [
                {"user_email": "good@test.com", "user_name": "Good", "approval_status": "approved"},
                {"user_email": "declined@test.com", "user_name": "Declined", "approval_status": "declined"},
            ],
            "next_cursor": None,
        }
        mock_client.close = AsyncMock()

        with patch("services.luma_integration_service.decrypt_value", return_value="key"):
            with patch("services.luma_integration_service.LumaClient", return_value=mock_client):
                with patch("services.authorization.check_organizer", new_callable=AsyncMock):
                    result = await service.sync_guests("user-1", "evt-1", "hack-1")

        assert result["imported"] == 1
        assert result["skipped"] == 1


class TestListContacts:
    @pytest.mark.asyncio
    async def test_list_contacts(self, service, mock_zerodb, connected_row):
        mock_zerodb.tables.query_rows.return_value = [connected_row]

        mock_client = AsyncMock()
        mock_client.list_contacts.return_value = {
            "entries": [
                {"email": "a@b.com", "name": "Alice", "event_approved_count": 5},
                {"email": "c@d.com", "name": "Charlie", "event_approved_count": 2},
            ],
            "next_cursor": None,
        }
        mock_client.close = AsyncMock()

        with patch("services.luma_integration_service.decrypt_value", return_value="key"):
            with patch("services.luma_integration_service.LumaClient", return_value=mock_client):
                result = await service.list_contacts("user-1")

        assert result["total"] == 2
        assert result["contacts"][0]["email"] == "a@b.com"
        assert result["contacts"][0]["event_count"] == 5
