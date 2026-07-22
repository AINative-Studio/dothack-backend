"""
ZeroPipeline Integration Service

Business logic for connecting, syncing, and importing data from ZeroPipeline CRM.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException

from integrations.zeropipeline.client import ZeroPipelineClient
from integrations.zeropipeline.exceptions import ZeroPipelineAuthError, ZeroPipelineError
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import ZeroDBNotFound
from utils.encryption import decrypt_value, encrypt_value
from config import settings

logger = logging.getLogger(__name__)


class ZeroPipelineIntegrationService:
    """Service for managing ZeroPipeline CRM integration lifecycle and data sync."""

    def __init__(self, zerodb_client: ZeroDBClient):
        self.zerodb = zerodb_client

    async def _get_settings(self, user_id: str) -> Optional[dict]:
        """Get integration settings row for a user."""
        try:
            rows = await self.zerodb.tables.query_rows(
                "integration_settings",
                filter={"user_id": user_id, "integration_type": "zeropipeline"},
                limit=1,
            )
            return rows[0] if rows else None
        except ZeroDBNotFound:
            return None

    async def _get_client(self, user_id: str) -> ZeroPipelineClient:
        """Build a ZeroPipelineClient from the user's stored encrypted API key."""
        row = await self._get_settings(user_id)
        if not row:
            raise HTTPException(status_code=404, detail="ZeroPipeline not connected")
        row_data = row.get("row_data", row)
        if row_data.get("status") != "connected":
            raise HTTPException(status_code=404, detail="ZeroPipeline not connected")
        api_key = decrypt_value(row_data.get("api_key_encrypted", ""))
        return ZeroPipelineClient(
            api_key=api_key, base_url=settings.ZEROPIPELINE_API_BASE_URL
        )

    async def connect(self, user_id: str, api_key: str) -> dict:
        """Verify a ZeroPipeline API key and store it encrypted in ZeroDB."""
        client = ZeroPipelineClient(
            api_key=api_key, base_url=settings.ZEROPIPELINE_API_BASE_URL
        )
        try:
            user_info = await client.verify_key()
        except ZeroPipelineAuthError:
            raise HTTPException(status_code=400, detail="Invalid ZeroPipeline API key")
        except ZeroPipelineError as e:
            raise HTTPException(
                status_code=502, detail=f"ZeroPipeline API error: {e.message}"
            )
        finally:
            await client.close()

        account_name = user_info.get("email") or user_info.get("name", "ZeroPipeline Account")
        encrypted_key = encrypt_value(api_key)
        now = datetime.now(timezone.utc).isoformat()

        existing = await self._get_settings(user_id)
        if existing:
            row_data = existing.get("row_data", existing)
            row_id = row_data.get("_row_id") or existing.get("_row_id")
            await self.zerodb.tables.update_row(
                "integration_settings",
                row_id,
                {
                    "api_key_encrypted": encrypted_key,
                    "account_name": account_name,
                    "status": "connected",
                    "updated_at": now,
                },
            )
            integration_id = row_data.get("id", str(row_id))
        else:
            integration_id = str(uuid.uuid4())
            await self.zerodb.tables.insert_rows(
                "integration_settings",
                [
                    {
                        "id": integration_id,
                        "user_id": user_id,
                        "integration_type": "zeropipeline",
                        "api_key_encrypted": encrypted_key,
                        "account_name": account_name,
                        "status": "connected",
                        "sync_options": json.dumps(
                            {
                                "pipelines": True,
                                "deals": True,
                                "customers": True,
                                "tasks": False,
                            }
                        ),
                        "created_at": now,
                        "updated_at": now,
                    }
                ],
            )

        return {
            "success": True,
            "integration_id": integration_id,
            "account_name": account_name,
            "status": "connected",
            "message": "ZeroPipeline connected successfully",
        }

    async def get_status(self, user_id: str) -> dict:
        """Return current ZeroPipeline connection status for the user."""
        row = await self._get_settings(user_id)
        if not row:
            return {"connected": False}
        row_data = row.get("row_data", row)
        sync_options = row_data.get("sync_options")
        if isinstance(sync_options, str):
            try:
                sync_options = json.loads(sync_options)
            except (json.JSONDecodeError, TypeError):
                sync_options = {
                    "pipelines": True,
                    "deals": True,
                    "customers": True,
                    "tasks": False,
                }
        return {
            "connected": row_data.get("status") == "connected",
            "integration_id": row_data.get("id"),
            "account_name": row_data.get("account_name"),
            "status": row_data.get("status"),
            "sync_options": sync_options,
            "last_synced_at": row_data.get("last_synced_at"),
        }

    async def disconnect(self, user_id: str) -> dict:
        """Remove the ZeroPipeline integration for a user."""
        row = await self._get_settings(user_id)
        if not row:
            raise HTTPException(status_code=404, detail="ZeroPipeline not connected")
        row_data = row.get("row_data", row)
        row_id = row_data.get("_row_id") or row.get("_row_id")
        await self.zerodb.tables.delete_row("integration_settings", row_id)
        return {"success": True, "message": "ZeroPipeline disconnected"}

    async def update_sync_options(self, user_id: str, options: dict) -> dict:
        """Persist updated sync option preferences."""
        row = await self._get_settings(user_id)
        if not row:
            raise HTTPException(status_code=404, detail="ZeroPipeline not connected")
        row_data = row.get("row_data", row)
        row_id = row_data.get("_row_id") or row.get("_row_id")
        now = datetime.now(timezone.utc).isoformat()
        await self.zerodb.tables.update_row(
            "integration_settings",
            row_id,
            {"sync_options": json.dumps(options), "updated_at": now},
        )
        return await self.get_status(user_id)

    async def list_pipelines(self, user_id: str) -> dict:
        """Fetch pipelines from the user's ZeroPipeline account."""
        client = await self._get_client(user_id)
        try:
            all_pipelines: list[dict[str, Any]] = []
            offset = 0
            limit = 25
            while True:
                result = await client.list_pipelines(limit=limit, offset=offset)
                items = result.get("items") or result.get("results") or result.get("pipelines", [])
                for item in items:
                    stages = item.get("stages") or []
                    deals = item.get("deals") or []
                    all_pipelines.append(
                        {
                            "pipeline_id": item.get("id", ""),
                            "name": item.get("name", "Untitled"),
                            "stage_count": len(stages) if isinstance(stages, list) else 0,
                            "deal_count": len(deals) if isinstance(deals, list) else item.get("deal_count", 0),
                        }
                    )
                if len(items) < limit:
                    break
                offset += limit
            return {"pipelines": all_pipelines, "total": len(all_pipelines)}
        finally:
            await client.close()

    async def list_deals(
        self, user_id: str, pipeline_id: Optional[str] = None
    ) -> dict:
        """Fetch deals from the user's ZeroPipeline account."""
        client = await self._get_client(user_id)
        try:
            all_deals: list[dict[str, Any]] = []
            offset = 0
            limit = 25
            while True:
                result = await client.list_deals(
                    pipeline_id=pipeline_id, limit=limit, offset=offset
                )
                items = result.get("items") or result.get("results") or result.get("deals", [])
                for item in items:
                    stage = item.get("stage")
                    stage_name = None
                    if isinstance(stage, dict):
                        stage_name = stage.get("name")
                    elif isinstance(stage, str):
                        stage_name = stage

                    customer = item.get("customer") or {}
                    customer_name = None
                    if isinstance(customer, dict):
                        customer_name = customer.get("name")
                    elif isinstance(customer, str):
                        customer_name = customer

                    all_deals.append(
                        {
                            "deal_id": item.get("id", ""),
                            "title": item.get("title") or item.get("name", "Untitled"),
                            "value": item.get("value"),
                            "currency": item.get("currency", "USD"),
                            "stage": stage_name,
                            "status": item.get("status"),
                            "customer_name": customer_name,
                        }
                    )
                if len(items) < limit:
                    break
                offset += limit
            return {"deals": all_deals, "total": len(all_deals)}
        finally:
            await client.close()

    async def list_customers(self, user_id: str) -> dict:
        """Fetch customers from the user's ZeroPipeline account."""
        client = await self._get_client(user_id)
        try:
            all_customers: list[dict[str, Any]] = []
            offset = 0
            limit = 25
            while True:
                result = await client.list_customers(limit=limit, offset=offset)
                items = result.get("items") or result.get("results") or result.get("customers", [])
                for item in items:
                    all_customers.append(
                        {
                            "customer_id": item.get("id", ""),
                            "name": item.get("name"),
                            "email": item.get("email"),
                            "company": item.get("company") or item.get("company_name"),
                        }
                    )
                if len(items) < limit:
                    break
                offset += limit
            return {"customers": all_customers, "total": len(all_customers)}
        finally:
            await client.close()

    async def import_customers(
        self,
        user_id: str,
        hackathon_id: str,
        pipeline_id: Optional[str] = None,
    ) -> dict:
        """Import customers from ZeroPipeline into hackathon participants."""
        from services.authorization import check_organizer

        await check_organizer(self.zerodb, user_id, hackathon_id)

        client = await self._get_client(user_id)
        try:
            all_customers: list[dict] = []
            offset = 0
            limit = 25
            while True:
                if pipeline_id:
                    # Fetch deals for the pipeline, extract unique customers
                    result = await client.list_deals(
                        pipeline_id=pipeline_id, limit=limit, offset=offset
                    )
                    items = result.get("items") or result.get("results") or result.get("deals", [])
                    for item in items:
                        customer = item.get("customer")
                        if isinstance(customer, dict) and customer.get("id"):
                            all_customers.append(customer)
                else:
                    result = await client.list_customers(limit=limit, offset=offset)
                    items = result.get("items") or result.get("results") or result.get("customers", [])
                    all_customers.extend(items)
                if len(items) < limit:
                    break
                offset += limit
        finally:
            await client.close()

        # Collect existing participant emails to avoid duplicates
        try:
            existing = await self.zerodb.tables.query_rows(
                "hackathon_participants",
                filter={"hackathon_id": hackathon_id},
                limit=10000,
            )
        except ZeroDBNotFound:
            existing = []

        existing_emails: set[str] = set()
        for p in existing:
            pd = p.get("row_data", p)
            meta = pd.get("metadata", {})
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except (json.JSONDecodeError, TypeError):
                    meta = {}
            email = meta.get("ainative_user_email", "")
            if email:
                existing_emails.add(email.lower())

        imported = 0
        skipped = 0
        now = datetime.now(timezone.utc).isoformat()

        # Deduplicate customers by email before importing
        seen_emails: set[str] = set()
        for customer in all_customers:
            email = customer.get("email", "")
            if not email or email.lower() in existing_emails or email.lower() in seen_emails:
                skipped += 1
                continue

            seen_emails.add(email.lower())
            name = customer.get("name", "")

            participant_id = str(uuid.uuid4())
            try:
                await self.zerodb.tables.insert_rows(
                    "participants",
                    [
                        {
                            "participant_id": participant_id,
                            "email": email,
                            "name": name,
                            "created_at": now,
                        }
                    ],
                )
            except Exception:
                pass  # May already exist

            await self.zerodb.tables.insert_rows(
                "hackathon_participants",
                [
                    {
                        "id": str(uuid.uuid4()),
                        "user_id": participant_id,
                        "hackathon_id": hackathon_id,
                        "role": "BUILDER",
                        "status": "active",
                        "joined_at": now,
                        "metadata": json.dumps(
                            {
                                "ainative_user_email": email,
                                "ainative_user_name": name,
                                "source": "zeropipeline",
                            }
                        ),
                    }
                ],
            )

            existing_emails.add(email.lower())
            imported += 1

        # Update last_synced_at on the integration settings row
        settings_row = await self._get_settings(user_id)
        if settings_row:
            row_data = settings_row.get("row_data", settings_row)
            row_id = row_data.get("_row_id") or settings_row.get("_row_id")
            await self.zerodb.tables.update_row(
                "integration_settings",
                row_id,
                {"last_synced_at": now, "updated_at": now},
            )

        return {
            "success": True,
            "imported": imported,
            "skipped": skipped,
            "total": len(all_customers),
            "message": f"Imported {imported} customers, skipped {skipped}",
        }

    async def get_dashboard(self, user_id: str) -> dict:
        """Fetch analytics dashboard summary from ZeroPipeline."""
        client = await self._get_client(user_id)
        try:
            result = await client.get_analytics_dashboard()
            return {
                "total_deals": result.get("total_deals", 0),
                "total_customers": result.get("total_customers", 0),
                "total_revenue": result.get("total_revenue"),
                "pipeline_count": result.get("pipeline_count", 0),
            }
        finally:
            await client.close()
