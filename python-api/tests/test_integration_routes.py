"""Tests for the integration API routes."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


class TestIntegrationRoutesAuth:
    """Verify all endpoints require authentication."""

    def test_connect_requires_auth(self, client):
        response = client.post("/api/v1/integrations/luma/connect", json={"api_key": "test-key-12345"})
        assert response.status_code in (401, 403)

    def test_status_requires_auth(self, client):
        response = client.get("/api/v1/integrations/luma/status")
        assert response.status_code in (401, 403)

    def test_disconnect_requires_auth(self, client):
        response = client.delete("/api/v1/integrations/luma/disconnect")
        assert response.status_code in (401, 403)

    def test_sync_options_requires_auth(self, client):
        response = client.put("/api/v1/integrations/luma/sync-options", json={"events": True, "guests": True, "contacts": False})
        assert response.status_code in (401, 403)

    def test_events_requires_auth(self, client):
        response = client.get("/api/v1/integrations/luma/events")
        assert response.status_code in (401, 403)

    def test_import_requires_auth(self, client):
        response = client.post("/api/v1/integrations/luma/import-event", json={"luma_event_id": "evt-1"})
        assert response.status_code in (401, 403)

    def test_sync_guests_requires_auth(self, client):
        response = client.post("/api/v1/integrations/luma/sync-guests", json={"luma_event_id": "evt-1", "hackathon_id": "h-1"})
        assert response.status_code in (401, 403)

    def test_contacts_requires_auth(self, client):
        response = client.get("/api/v1/integrations/luma/contacts")
        assert response.status_code in (401, 403)


class TestConnectEndpoint:
    @patch("api.routes.integrations.LumaIntegrationService")
    def test_connect_success(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.connect = AsyncMock(return_value={
            "success": True,
            "integration_id": "int-123",
            "calendar_name": "My Calendar",
            "status": "connected",
            "message": "Luma connected successfully",
        })

        response = authenticated_client.post(
            "/api/v1/integrations/luma/connect",
            json={"api_key": "valid-luma-key-12345"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["calendar_name"] == "My Calendar"

    @patch("api.routes.integrations.LumaIntegrationService")
    def test_connect_invalid_key(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.connect = AsyncMock(side_effect=HTTPException(status_code=400, detail="Invalid Luma API key"))

        response = authenticated_client.post(
            "/api/v1/integrations/luma/connect",
            json={"api_key": "bad-key-12345678"},
        )
        assert response.status_code == 400

    def test_connect_short_key_validation(self, authenticated_client):
        response = authenticated_client.post(
            "/api/v1/integrations/luma/connect",
            json={"api_key": "short"},
        )
        assert response.status_code == 422


class TestStatusEndpoint:
    @patch("api.routes.integrations.LumaIntegrationService")
    def test_status_connected(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.get_status = AsyncMock(return_value={
            "connected": True,
            "integration_id": "int-123",
            "calendar_name": "Test Cal",
            "status": "connected",
            "sync_options": {"events": True, "guests": True, "contacts": False},
            "last_synced_at": "2025-01-01T00:00:00Z",
        })

        response = authenticated_client.get("/api/v1/integrations/luma/status")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True

    @patch("api.routes.integrations.LumaIntegrationService")
    def test_status_not_connected(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.get_status = AsyncMock(return_value={"connected": False})

        response = authenticated_client.get("/api/v1/integrations/luma/status")
        assert response.status_code == 200
        assert response.json()["connected"] is False


class TestDisconnectEndpoint:
    @patch("api.routes.integrations.LumaIntegrationService")
    def test_disconnect_success(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.disconnect = AsyncMock(return_value={"success": True, "message": "Luma disconnected"})

        response = authenticated_client.delete("/api/v1/integrations/luma/disconnect")
        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch("api.routes.integrations.LumaIntegrationService")
    def test_disconnect_not_connected(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.disconnect = AsyncMock(side_effect=HTTPException(status_code=404, detail="Luma not connected"))

        response = authenticated_client.delete("/api/v1/integrations/luma/disconnect")
        assert response.status_code == 404


class TestSyncOptionsEndpoint:
    @patch("api.routes.integrations.LumaIntegrationService")
    def test_update_sync_options(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.update_sync_options = AsyncMock(return_value={
            "connected": True,
            "integration_id": "int-123",
            "calendar_name": "Cal",
            "status": "connected",
            "sync_options": {"events": False, "guests": True, "contacts": True},
            "last_synced_at": None,
        })

        response = authenticated_client.put(
            "/api/v1/integrations/luma/sync-options",
            json={"events": False, "guests": True, "contacts": True},
        )
        assert response.status_code == 200
        assert response.json()["sync_options"]["contacts"] is True


class TestEventsEndpoint:
    @patch("api.routes.integrations.LumaIntegrationService")
    def test_list_events(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.list_luma_events = AsyncMock(return_value={
            "events": [
                {"event_id": "evt-1", "name": "Hack 2025", "start_at": "2025-01-01", "end_at": "2025-01-03",
                 "location": "Denver", "is_online": False, "cover_url": None, "guest_count": 50, "url": "https://lu.ma/hack"},
            ],
            "total": 1,
        })

        response = authenticated_client.get("/api/v1/integrations/luma/events")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["events"][0]["name"] == "Hack 2025"


class TestImportEventEndpoint:
    @patch("api.routes.integrations.LumaIntegrationService")
    def test_import_event(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.import_event = AsyncMock(return_value={
            "success": True,
            "hackathon_id": "h-123",
            "hackathon_name": "AI Hack",
            "message": "Imported 'AI Hack' as draft hackathon",
        })

        response = authenticated_client.post(
            "/api/v1/integrations/luma/import-event",
            json={"luma_event_id": "evt-ai"},
        )
        assert response.status_code == 200
        assert response.json()["hackathon_id"] == "h-123"


class TestSyncGuestsEndpoint:
    @patch("api.routes.integrations.LumaIntegrationService")
    def test_sync_guests(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.sync_guests = AsyncMock(return_value={
            "success": True,
            "imported": 10,
            "skipped": 2,
            "total": 12,
            "message": "Imported 10 guests, skipped 2",
        })

        response = authenticated_client.post(
            "/api/v1/integrations/luma/sync-guests",
            json={"luma_event_id": "evt-1", "hackathon_id": "h-1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["imported"] == 10
        assert data["skipped"] == 2


class TestContactsEndpoint:
    @patch("api.routes.integrations.LumaIntegrationService")
    def test_list_contacts(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.list_contacts = AsyncMock(return_value={
            "contacts": [
                {"email": "a@b.com", "name": "Alice", "event_count": 3},
            ],
            "total": 1,
        })

        response = authenticated_client.get("/api/v1/integrations/luma/contacts")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["contacts"][0]["email"] == "a@b.com"
