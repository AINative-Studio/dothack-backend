"""Tests for the ZeroPipeline CRM integration API routes."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException


class TestZeroPipelineRoutesAuth:
    """Verify all ZeroPipeline endpoints require authentication."""

    def test_connect_requires_auth(self, client):
        response = client.post(
            "/api/v1/integrations/zeropipeline/connect",
            json={"api_key": "test-key-12345"},
        )
        assert response.status_code in (401, 403)

    def test_status_requires_auth(self, client):
        response = client.get("/api/v1/integrations/zeropipeline/status")
        assert response.status_code in (401, 403)

    def test_disconnect_requires_auth(self, client):
        response = client.delete("/api/v1/integrations/zeropipeline/disconnect")
        assert response.status_code in (401, 403)

    def test_sync_options_requires_auth(self, client):
        response = client.put(
            "/api/v1/integrations/zeropipeline/sync-options",
            json={"pipelines": True, "deals": True, "customers": True, "tasks": False},
        )
        assert response.status_code in (401, 403)

    def test_pipelines_requires_auth(self, client):
        response = client.get("/api/v1/integrations/zeropipeline/pipelines")
        assert response.status_code in (401, 403)

    def test_deals_requires_auth(self, client):
        response = client.get("/api/v1/integrations/zeropipeline/deals")
        assert response.status_code in (401, 403)

    def test_customers_requires_auth(self, client):
        response = client.get("/api/v1/integrations/zeropipeline/customers")
        assert response.status_code in (401, 403)

    def test_import_customers_requires_auth(self, client):
        response = client.post(
            "/api/v1/integrations/zeropipeline/import-customers",
            json={"hackathon_id": "h-1"},
        )
        assert response.status_code in (401, 403)

    def test_dashboard_requires_auth(self, client):
        response = client.get("/api/v1/integrations/zeropipeline/dashboard")
        assert response.status_code in (401, 403)


class TestConnectEndpoint:
    @patch("api.routes.zeropipeline.ZeroPipelineIntegrationService")
    def test_connect_success(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.connect = AsyncMock(return_value={
            "success": True,
            "integration_id": "int-456",
            "account_name": "crm@acme.com",
            "status": "connected",
            "message": "ZeroPipeline connected successfully",
        })

        response = authenticated_client.post(
            "/api/v1/integrations/zeropipeline/connect",
            json={"api_key": "valid-zpk-key-12345"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["account_name"] == "crm@acme.com"
        assert data["status"] == "connected"

    @patch("api.routes.zeropipeline.ZeroPipelineIntegrationService")
    def test_connect_invalid_key(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.connect = AsyncMock(
            side_effect=HTTPException(status_code=400, detail="Invalid ZeroPipeline API key")
        )

        response = authenticated_client.post(
            "/api/v1/integrations/zeropipeline/connect",
            json={"api_key": "bad-key-12345678"},
        )
        assert response.status_code == 400

    def test_connect_validation_error(self, authenticated_client):
        response = authenticated_client.post(
            "/api/v1/integrations/zeropipeline/connect",
            json={"api_key": "short"},
        )
        assert response.status_code == 422


class TestStatusEndpoint:
    @patch("api.routes.zeropipeline.ZeroPipelineIntegrationService")
    def test_status_success(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.get_status = AsyncMock(return_value={
            "connected": True,
            "integration_id": "int-456",
            "account_name": "crm@acme.com",
            "status": "connected",
            "sync_options": {"pipelines": True, "deals": True, "customers": True, "tasks": False},
            "last_synced_at": "2025-06-01T00:00:00Z",
        })

        response = authenticated_client.get("/api/v1/integrations/zeropipeline/status")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert data["account_name"] == "crm@acme.com"

    @patch("api.routes.zeropipeline.ZeroPipelineIntegrationService")
    def test_status_not_connected(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.get_status = AsyncMock(return_value={"connected": False})

        response = authenticated_client.get("/api/v1/integrations/zeropipeline/status")
        assert response.status_code == 200
        assert response.json()["connected"] is False


class TestDisconnectEndpoint:
    @patch("api.routes.zeropipeline.ZeroPipelineIntegrationService")
    def test_disconnect_success(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.disconnect = AsyncMock(
            return_value={"success": True, "message": "ZeroPipeline disconnected"}
        )

        response = authenticated_client.delete("/api/v1/integrations/zeropipeline/disconnect")
        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch("api.routes.zeropipeline.ZeroPipelineIntegrationService")
    def test_disconnect_not_connected(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.disconnect = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="ZeroPipeline not connected")
        )

        response = authenticated_client.delete("/api/v1/integrations/zeropipeline/disconnect")
        assert response.status_code == 404


class TestSyncOptionsEndpoint:
    @patch("api.routes.zeropipeline.ZeroPipelineIntegrationService")
    def test_sync_options_success(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.update_sync_options = AsyncMock(return_value={
            "connected": True,
            "integration_id": "int-456",
            "account_name": "crm@acme.com",
            "status": "connected",
            "sync_options": {"pipelines": False, "deals": True, "customers": True, "tasks": True},
            "last_synced_at": None,
        })

        response = authenticated_client.put(
            "/api/v1/integrations/zeropipeline/sync-options",
            json={"pipelines": False, "deals": True, "customers": True, "tasks": True},
        )
        assert response.status_code == 200
        assert response.json()["sync_options"]["tasks"] is True


class TestPipelinesEndpoint:
    @patch("api.routes.zeropipeline.ZeroPipelineIntegrationService")
    def test_pipelines_success(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.list_pipelines = AsyncMock(return_value={
            "pipelines": [
                {"pipeline_id": "pip-1", "name": "Sales Pipeline", "stage_count": 3, "deal_count": 12},
                {"pipeline_id": "pip-2", "name": "Growth Pipeline", "stage_count": 2, "deal_count": 5},
            ],
            "total": 2,
        })

        response = authenticated_client.get("/api/v1/integrations/zeropipeline/pipelines")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["pipelines"][0]["name"] == "Sales Pipeline"


class TestDealsEndpoint:
    @patch("api.routes.zeropipeline.ZeroPipelineIntegrationService")
    def test_deals_success(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.list_deals = AsyncMock(return_value={
            "deals": [
                {
                    "deal_id": "deal-1",
                    "title": "Enterprise Contract",
                    "value": 75000.0,
                    "currency": "USD",
                    "stage": "Proposal",
                    "status": "open",
                    "customer_name": "Acme Corp",
                },
            ],
            "total": 1,
        })

        response = authenticated_client.get("/api/v1/integrations/zeropipeline/deals")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["deals"][0]["title"] == "Enterprise Contract"
        assert data["deals"][0]["value"] == 75000.0


class TestCustomersEndpoint:
    @patch("api.routes.zeropipeline.ZeroPipelineIntegrationService")
    def test_customers_success(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.list_customers = AsyncMock(return_value={
            "customers": [
                {"customer_id": "cust-1", "name": "Alice Smith", "email": "alice@acme.com", "company": "Acme"},
                {"customer_id": "cust-2", "name": "Bob Jones", "email": "bob@example.com", "company": None},
            ],
            "total": 2,
        })

        response = authenticated_client.get("/api/v1/integrations/zeropipeline/customers")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["customers"][0]["email"] == "alice@acme.com"


class TestImportCustomersEndpoint:
    @patch("api.routes.zeropipeline.ZeroPipelineIntegrationService")
    def test_import_customers_success(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.import_customers = AsyncMock(return_value={
            "success": True,
            "imported": 8,
            "skipped": 2,
            "total": 10,
            "message": "Imported 8 customers, skipped 2",
        })

        response = authenticated_client.post(
            "/api/v1/integrations/zeropipeline/import-customers",
            json={"hackathon_id": "h-1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["imported"] == 8
        assert data["skipped"] == 2

    @patch("api.routes.zeropipeline.ZeroPipelineIntegrationService")
    def test_import_customers_not_organizer(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.import_customers = AsyncMock(
            side_effect=HTTPException(status_code=403, detail="Not an organizer of this hackathon")
        )

        response = authenticated_client.post(
            "/api/v1/integrations/zeropipeline/import-customers",
            json={"hackathon_id": "h-1"},
        )
        assert response.status_code == 403


class TestDashboardEndpoint:
    @patch("api.routes.zeropipeline.ZeroPipelineIntegrationService")
    def test_dashboard_success(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.get_dashboard = AsyncMock(return_value={
            "total_deals": 42,
            "total_customers": 100,
            "total_revenue": 250000.0,
            "pipeline_count": 3,
        })

        response = authenticated_client.get("/api/v1/integrations/zeropipeline/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["total_deals"] == 42
        assert data["total_customers"] == 100
        assert data["pipeline_count"] == 3

    @patch("api.routes.zeropipeline.ZeroPipelineIntegrationService")
    def test_dashboard_not_connected(self, MockService, authenticated_client):
        mock_svc = MockService.return_value
        mock_svc.get_dashboard = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="ZeroPipeline not connected")
        )

        response = authenticated_client.get("/api/v1/integrations/zeropipeline/dashboard")
        assert response.status_code == 404
