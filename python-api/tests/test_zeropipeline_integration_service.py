"""Tests for the ZeroPipeline Integration Service."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from integrations.zeropipeline.exceptions import ZeroPipelineAuthError, ZeroPipelineError
from integrations.zerodb.exceptions import ZeroDBNotFound
from services.zeropipeline_integration_service import ZeroPipelineIntegrationService


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
    return ZeroPipelineIntegrationService(mock_zerodb)


@pytest.fixture
def connected_row():
    return {
        "row_data": {
            "_row_id": "row-456",
            "id": str(uuid.uuid4()),
            "user_id": "user-1",
            "integration_type": "zeropipeline",
            "api_key_encrypted": "",
            "account_name": "Test CRM Account",
            "status": "connected",
            "sync_options": json.dumps(
                {"pipelines": True, "deals": True, "customers": True, "tasks": False}
            ),
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
        assert result["account_name"] == "Test CRM Account"
        assert result["sync_options"]["pipelines"] is True

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
        mock_client.verify_key.return_value = {"email": "crm@test.com"}
        mock_client.close = AsyncMock()

        with patch("services.zeropipeline_integration_service.ZeroPipelineClient", return_value=mock_client):
            with patch("services.zeropipeline_integration_service.encrypt_value", return_value="enc-key"):
                result = await service.connect("user-1", "zpk-api-key-12345")

        assert result["success"] is True
        assert result["account_name"] == "crm@test.com"
        assert result["status"] == "connected"
        mock_zerodb.tables.insert_rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_update_existing(self, service, mock_zerodb, connected_row):
        mock_zerodb.tables.query_rows.return_value = [connected_row]

        mock_client = AsyncMock()
        mock_client.verify_key.return_value = {"email": "updated@crm.com"}
        mock_client.close = AsyncMock()

        with patch("services.zeropipeline_integration_service.ZeroPipelineClient", return_value=mock_client):
            with patch("services.zeropipeline_integration_service.encrypt_value", return_value="enc-key"):
                result = await service.connect("user-1", "new-key-12345678")

        assert result["success"] is True
        assert result["account_name"] == "updated@crm.com"
        mock_zerodb.tables.update_row.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_invalid_key(self, service):
        mock_client = AsyncMock()
        mock_client.verify_key.side_effect = ZeroPipelineAuthError("invalid")
        mock_client.close = AsyncMock()

        with patch("services.zeropipeline_integration_service.ZeroPipelineClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await service.connect("user-1", "bad-key-12345")
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_connect_api_error(self, service):
        mock_client = AsyncMock()
        mock_client.verify_key.side_effect = ZeroPipelineError("server error")
        mock_client.close = AsyncMock()

        with patch("services.zeropipeline_integration_service.ZeroPipelineClient", return_value=mock_client):
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
            "user-1", {"pipelines": False, "deals": True, "customers": True, "tasks": True}
        )
        assert result["connected"] is True
        mock_zerodb.tables.update_row.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_connected(self, service, mock_zerodb):
        mock_zerodb.tables.query_rows.return_value = []
        with pytest.raises(HTTPException) as exc_info:
            await service.update_sync_options(
                "user-1", {"pipelines": True, "deals": True, "customers": True, "tasks": False}
            )
        assert exc_info.value.status_code == 404


class TestListPipelines:
    @pytest.mark.asyncio
    async def test_list_pipelines(self, service, mock_zerodb, connected_row):
        mock_zerodb.tables.query_rows.return_value = [connected_row]

        mock_client = AsyncMock()
        mock_client.list_pipelines.return_value = {
            "items": [
                {"id": "pip-1", "name": "Sales Pipeline", "stages": ["Stage A", "Stage B"], "deals": []},
                {"id": "pip-2", "name": "Growth Pipeline", "stages": [], "deals": ["deal-1"]},
            ],
        }
        mock_client.close = AsyncMock()

        with patch("services.zeropipeline_integration_service.decrypt_value", return_value="key"):
            with patch("services.zeropipeline_integration_service.ZeroPipelineClient", return_value=mock_client):
                result = await service.list_pipelines("user-1")

        assert result["total"] == 2
        assert result["pipelines"][0]["pipeline_id"] == "pip-1"
        assert result["pipelines"][0]["name"] == "Sales Pipeline"
        assert result["pipelines"][0]["stage_count"] == 2


class TestListDeals:
    @pytest.mark.asyncio
    async def test_list_deals(self, service, mock_zerodb, connected_row):
        mock_zerodb.tables.query_rows.return_value = [connected_row]

        mock_client = AsyncMock()
        mock_client.list_deals.return_value = {
            "items": [
                {
                    "id": "deal-1",
                    "title": "Enterprise Deal",
                    "value": 50000.0,
                    "currency": "USD",
                    "stage": {"name": "Proposal"},
                    "status": "open",
                    "customer": {"name": "Acme Corp"},
                },
            ],
        }
        mock_client.close = AsyncMock()

        with patch("services.zeropipeline_integration_service.decrypt_value", return_value="key"):
            with patch("services.zeropipeline_integration_service.ZeroPipelineClient", return_value=mock_client):
                result = await service.list_deals("user-1")

        assert result["total"] == 1
        assert result["deals"][0]["deal_id"] == "deal-1"
        assert result["deals"][0]["title"] == "Enterprise Deal"
        assert result["deals"][0]["stage"] == "Proposal"
        assert result["deals"][0]["customer_name"] == "Acme Corp"


class TestListCustomers:
    @pytest.mark.asyncio
    async def test_list_customers(self, service, mock_zerodb, connected_row):
        mock_zerodb.tables.query_rows.return_value = [connected_row]

        mock_client = AsyncMock()
        mock_client.list_customers.return_value = {
            "items": [
                {"id": "cust-1", "name": "Alice Smith", "email": "alice@example.com", "company": "Acme"},
                {"id": "cust-2", "name": "Bob Jones", "email": "bob@example.com", "company": None},
            ],
        }
        mock_client.close = AsyncMock()

        with patch("services.zeropipeline_integration_service.decrypt_value", return_value="key"):
            with patch("services.zeropipeline_integration_service.ZeroPipelineClient", return_value=mock_client):
                result = await service.list_customers("user-1")

        assert result["total"] == 2
        assert result["customers"][0]["customer_id"] == "cust-1"
        assert result["customers"][0]["email"] == "alice@example.com"
        assert result["customers"][0]["company"] == "Acme"


class TestImportCustomers:
    @pytest.mark.asyncio
    async def test_import_new_customers(self, service, mock_zerodb, connected_row):
        # Calls: _get_settings for _get_client, then query existing participants, then _get_settings for last_synced_at
        mock_zerodb.tables.query_rows.side_effect = [
            [connected_row],  # _get_client -> _get_settings
            [],               # existing hackathon_participants
            [connected_row],  # _get_settings for last_synced_at update
        ]

        mock_client = AsyncMock()
        mock_client.list_customers.return_value = {
            "items": [
                {"id": "cust-1", "name": "Alice", "email": "alice@example.com", "company": "Acme"},
                {"id": "cust-2", "name": "Bob", "email": "bob@example.com", "company": None},
            ],
        }
        mock_client.close = AsyncMock()

        with patch("services.zeropipeline_integration_service.decrypt_value", return_value="key"):
            with patch("services.zeropipeline_integration_service.ZeroPipelineClient", return_value=mock_client):
                with patch("services.authorization.check_organizer", new_callable=AsyncMock):
                    result = await service.import_customers("user-1", "hack-1")

        assert result["success"] is True
        assert result["imported"] == 2
        assert result["skipped"] == 0
        assert result["total"] == 2
        assert mock_zerodb.tables.insert_rows.call_count >= 2

    @pytest.mark.asyncio
    async def test_import_skips_duplicates(self, service, mock_zerodb, connected_row):
        existing_participant = {
            "row_data": {
                "hackathon_id": "hack-1",
                "metadata": json.dumps({"ainative_user_email": "alice@example.com"}),
            }
        }
        mock_zerodb.tables.query_rows.side_effect = [
            [connected_row],          # _get_client -> _get_settings
            [existing_participant],   # existing hackathon_participants
            [connected_row],          # _get_settings for last_synced_at update
        ]

        mock_client = AsyncMock()
        mock_client.list_customers.return_value = {
            "items": [
                {"id": "cust-1", "name": "Alice", "email": "alice@example.com", "company": "Acme"},
                {"id": "cust-3", "name": "Charlie", "email": "charlie@example.com", "company": None},
            ],
        }
        mock_client.close = AsyncMock()

        with patch("services.zeropipeline_integration_service.decrypt_value", return_value="key"):
            with patch("services.zeropipeline_integration_service.ZeroPipelineClient", return_value=mock_client):
                with patch("services.authorization.check_organizer", new_callable=AsyncMock):
                    result = await service.import_customers("user-1", "hack-1")

        assert result["imported"] == 1
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_import_not_connected(self, service, mock_zerodb):
        mock_zerodb.tables.query_rows.return_value = []

        with patch("services.authorization.check_organizer", new_callable=AsyncMock):
            with pytest.raises(HTTPException) as exc_info:
                await service.import_customers("user-1", "hack-1")
            assert exc_info.value.status_code == 404


class TestGetDashboard:
    @pytest.mark.asyncio
    async def test_get_dashboard(self, service, mock_zerodb, connected_row):
        mock_zerodb.tables.query_rows.return_value = [connected_row]

        mock_client = AsyncMock()
        mock_client.get_analytics_dashboard.return_value = {
            "total_deals": 42,
            "total_customers": 100,
            "total_revenue": 250000.0,
            "pipeline_count": 3,
        }
        mock_client.close = AsyncMock()

        with patch("services.zeropipeline_integration_service.decrypt_value", return_value="key"):
            with patch("services.zeropipeline_integration_service.ZeroPipelineClient", return_value=mock_client):
                result = await service.get_dashboard("user-1")

        assert result["total_deals"] == 42
        assert result["total_customers"] == 100
        assert result["total_revenue"] == 250000.0
        assert result["pipeline_count"] == 3
