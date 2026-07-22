"""
Luma Integration Service

Business logic for connecting, syncing, and importing data from Luma.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException

from integrations.luma.client import LumaClient
from integrations.luma.exceptions import LumaAuthError, LumaError
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import ZeroDBNotFound
from utils.encryption import decrypt_value, encrypt_value
from config import settings

logger = logging.getLogger(__name__)


class LumaIntegrationService:
    """Service for managing Luma integration lifecycle and data sync."""

    def __init__(self, zerodb_client: ZeroDBClient):
        self.zerodb = zerodb_client

    async def _get_settings(self, user_id: str) -> Optional[dict]:
        """Get integration settings row for a user."""
        try:
            rows = await self.zerodb.tables.query_rows(
                "integration_settings",
                filter={"user_id": user_id, "integration_type": "luma"},
                limit=1,
            )
            return rows[0] if rows else None
        except ZeroDBNotFound:
            return None

    async def _get_luma_client(self, user_id: str) -> LumaClient:
        """Build a LumaClient from the user's stored encrypted API key."""
        row = await self._get_settings(user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Luma not connected")
        row_data = row.get("row_data", row)
        if row_data.get("status") != "connected":
            raise HTTPException(status_code=404, detail="Luma not connected")
        api_key = decrypt_value(row_data.get("api_key_encrypted", ""))
        return LumaClient(api_key=api_key, base_url=settings.LUMA_API_BASE_URL)

    async def connect(self, user_id: str, api_key: str) -> dict:
        """Verify a Luma API key and store it encrypted in ZeroDB."""
        client = LumaClient(api_key=api_key, base_url=settings.LUMA_API_BASE_URL)
        try:
            user_info = await client.verify_key()
        except LumaAuthError:
            raise HTTPException(status_code=400, detail="Invalid Luma API key")
        except LumaError as e:
            raise HTTPException(status_code=502, detail=f"Luma API error: {e.message}")
        finally:
            await client.close()

        calendar_name = user_info.get("name", "Luma Calendar")
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
                    "calendar_name": calendar_name,
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
                        "integration_type": "luma",
                        "api_key_encrypted": encrypted_key,
                        "calendar_name": calendar_name,
                        "status": "connected",
                        "sync_options": json.dumps(
                            {"events": True, "guests": True, "contacts": False}
                        ),
                        "created_at": now,
                        "updated_at": now,
                    }
                ],
            )

        return {
            "success": True,
            "integration_id": integration_id,
            "calendar_name": calendar_name,
            "status": "connected",
            "message": "Luma connected successfully",
        }

    async def get_status(self, user_id: str) -> dict:
        """Return current Luma connection status for the user."""
        row = await self._get_settings(user_id)
        if not row:
            return {"connected": False}
        row_data = row.get("row_data", row)
        sync_options = row_data.get("sync_options")
        if isinstance(sync_options, str):
            try:
                sync_options = json.loads(sync_options)
            except (json.JSONDecodeError, TypeError):
                sync_options = {"events": True, "guests": True, "contacts": False}
        return {
            "connected": row_data.get("status") == "connected",
            "integration_id": row_data.get("id"),
            "calendar_name": row_data.get("calendar_name"),
            "status": row_data.get("status"),
            "sync_options": sync_options,
            "last_synced_at": row_data.get("last_synced_at"),
        }

    async def disconnect(self, user_id: str) -> dict:
        """Remove the Luma integration for a user."""
        row = await self._get_settings(user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Luma not connected")
        row_data = row.get("row_data", row)
        row_id = row_data.get("_row_id") or row.get("_row_id")
        await self.zerodb.tables.delete_row("integration_settings", row_id)
        return {"success": True, "message": "Luma disconnected"}

    async def update_sync_options(self, user_id: str, options: dict) -> dict:
        """Persist updated sync option preferences."""
        row = await self._get_settings(user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Luma not connected")
        row_data = row.get("row_data", row)
        row_id = row_data.get("_row_id") or row.get("_row_id")
        now = datetime.now(timezone.utc).isoformat()
        await self.zerodb.tables.update_row(
            "integration_settings",
            row_id,
            {"sync_options": json.dumps(options), "updated_at": now},
        )
        return await self.get_status(user_id)

    async def list_luma_events(self, user_id: str) -> dict:
        """Fetch all events from the user's Luma calendar."""
        client = await self._get_luma_client(user_id)
        try:
            all_events: list[dict[str, Any]] = []
            cursor = None
            while True:
                result = await client.list_events(cursor=cursor)
                entries = result.get("entries", [])
                for entry in entries:
                    event = entry.get("event", entry)
                    geo = event.get("geo_address_info") or event.get("geo_address_json")
                    location = None
                    if isinstance(geo, dict):
                        location = geo.get("full_address")
                    all_events.append(
                        {
                            "event_id": event.get("api_id") or event.get("id", ""),
                            "name": event.get("name", "Untitled"),
                            "start_at": event.get("start_at"),
                            "end_at": event.get("end_at"),
                            "location": location,
                            "is_online": event.get("location_type") == "online",
                            "cover_url": event.get("cover_url"),
                            "guest_count": event.get("guest_count", 0),
                            "url": event.get("url"),
                        }
                    )
                cursor = result.get("next_cursor")
                if not cursor:
                    break
            return {"events": all_events, "total": len(all_events)}
        finally:
            await client.close()

    async def import_event(self, user_id: str, luma_event_id: str) -> dict:
        """Import a Luma event as a draft hackathon in DotHack."""
        client = await self._get_luma_client(user_id)
        try:
            result = await client.get_event(luma_event_id)
            event = result if isinstance(result, dict) and "name" in result else result.get("event", result)
        finally:
            await client.close()

        now = datetime.now(timezone.utc).isoformat()
        hackathon_id = str(uuid.uuid4())
        location = "virtual"
        if event.get("geo_address_info"):
            location = event["geo_address_info"].get("full_address", "virtual")

        hackathon_data = {
            "hackathon_id": hackathon_id,
            "name": event.get("name", "Imported Event"),
            "description": event.get("description_md") or event.get("description", ""),
            "organizer_id": user_id,
            "start_date": event.get("start_at", now),
            "end_date": event.get("end_at", now),
            "location": location,
            "is_online": event.get("location_type") == "online",
            "logo_url": event.get("cover_url", ""),
            "website_url": event.get("url", ""),
            "status": "draft",
            "luma_event_id": luma_event_id,
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
        }

        await self.zerodb.tables.insert_rows("hackathons", [hackathon_data])

        await self.zerodb.tables.insert_rows(
            "hackathon_participants",
            [
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "hackathon_id": hackathon_id,
                    "role": "ORGANIZER",
                    "status": "active",
                    "joined_at": now,
                }
            ],
        )

        return {
            "success": True,
            "hackathon_id": hackathon_id,
            "hackathon_name": hackathon_data["name"],
            "message": f"Imported '{hackathon_data['name']}' as draft hackathon",
        }

    async def sync_guests(
        self, user_id: str, luma_event_id: str, hackathon_id: str
    ) -> dict:
        """Pull guests from a Luma event into hackathon participants."""
        from services.authorization import check_organizer

        await check_organizer(self.zerodb, user_id, hackathon_id)

        client = await self._get_luma_client(user_id)
        try:
            all_guests: list[dict] = []
            cursor = None
            while True:
                result = await client.list_guests(luma_event_id, cursor=cursor)
                entries = result.get("entries", [])
                all_guests.extend(entries)
                cursor = result.get("next_cursor")
                if not cursor:
                    break
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

        for entry in all_guests:
            guest = entry.get("guest", entry)
            email = guest.get("user_email") or guest.get("email", "")
            if not email or email.lower() in existing_emails:
                skipped += 1
                continue

            approval_status = guest.get("approval_status", "")
            if approval_status not in ("approved", "going", ""):
                skipped += 1
                continue

            name = guest.get("user_name") or guest.get("name", "")

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
                                "source": "luma",
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
            "total": len(all_guests),
            "message": f"Imported {imported} guests, skipped {skipped}",
        }

    async def list_contacts(self, user_id: str) -> dict:
        """Fetch historical contacts from the user's Luma calendar."""
        client = await self._get_luma_client(user_id)
        try:
            all_contacts: list[dict[str, Any]] = []
            cursor = None
            while True:
                result = await client.list_contacts(cursor=cursor)
                entries = result.get("entries", [])
                for entry in entries:
                    person = entry.get("person", entry)
                    all_contacts.append(
                        {
                            "email": person.get("email", ""),
                            "name": person.get("name"),
                            "event_count": person.get("event_approved_count") or entry.get("event_count", 0),
                        }
                    )
                cursor = result.get("next_cursor")
                if not cursor:
                    break
            return {"contacts": all_contacts, "total": len(all_contacts)}
        finally:
            await client.close()
