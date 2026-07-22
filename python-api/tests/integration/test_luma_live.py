"""Live integration tests against the real Luma API.

Run with: pytest tests/integration/test_luma_live.py -v -s
Requires LUMA_API_KEY env var or uses the key from core/.env.
"""

import os
import sys

import pytest

LUMA_API_KEY = os.environ.get("LUMA_API_KEY", "secret-Ix0bVV0oVB19U8v6GRJtlrx6k")

pytestmark = pytest.mark.asyncio


@pytest.fixture
def luma_client():
    from integrations.luma.client import LumaClient
    return LumaClient(api_key=LUMA_API_KEY)


class TestLumaLiveAPI:
    async def test_verify_key(self, luma_client):
        result = await luma_client.verify_key()
        await luma_client.close()
        assert "id" in result
        assert "name" in result
        assert result["id"].startswith("usr-")

    async def test_list_events(self, luma_client):
        result = await luma_client.list_events()
        await luma_client.close()
        assert "entries" in result
        entries = result["entries"]
        assert len(entries) > 0
        first = entries[0]
        assert "id" in first
        assert "name" in first
        assert first["id"].startswith("evt-")

    async def test_list_events_pagination(self, luma_client):
        result = await luma_client.list_events()
        cursor = result.get("next_cursor")
        if cursor:
            page2 = await luma_client.list_events(cursor=cursor)
            assert "entries" in page2
        await luma_client.close()

    async def test_get_event(self, luma_client):
        events = await luma_client.list_events()
        entries = events["entries"]
        assert len(entries) > 0
        event_id = entries[0]["id"]

        detail = await luma_client.get_event(event_id)
        await luma_client.close()
        assert detail["id"] == event_id
        assert "name" in detail

    async def test_list_guests(self, luma_client):
        events = await luma_client.list_events()
        event_id = events["entries"][0]["id"]

        guests = await luma_client.list_guests(event_id)
        await luma_client.close()
        assert "entries" in guests
        if guests["entries"]:
            g = guests["entries"][0]
            assert "user_email" in g
            assert "approval_status" in g

    async def test_list_contacts(self, luma_client):
        result = await luma_client.list_contacts()
        await luma_client.close()
        assert "entries" in result
        entries = result["entries"]
        assert len(entries) > 0
        c = entries[0]
        assert "email" in c
        assert "name" in c

    async def test_invalid_key_raises_auth_error(self):
        from integrations.luma.client import LumaClient
        from integrations.luma.exceptions import LumaAuthError
        client = LumaClient(api_key="invalid-key-should-fail")
        with pytest.raises(LumaAuthError):
            await client.verify_key()
        await client.close()


class TestLumaServiceMappings:
    """Verify the service correctly maps real Luma API responses."""

    async def test_events_mapping(self, luma_client):
        from services.luma_integration_service import LumaIntegrationService
        result = await luma_client.list_events()
        await luma_client.close()

        entries = result["entries"]
        for entry in entries[:5]:
            event = entry.get("event", entry)
            event_id = event.get("api_id") or event.get("id", "")
            assert event_id, f"Event missing id: {list(event.keys())}"
            assert event.get("name"), f"Event missing name: {event_id}"

    async def test_contacts_mapping(self, luma_client):
        result = await luma_client.list_contacts()
        await luma_client.close()

        for entry in result["entries"][:5]:
            person = entry.get("person", entry)
            assert person.get("email"), f"Contact missing email: {list(person.keys())}"
            count = person.get("event_approved_count") or entry.get("event_count", 0)
            assert isinstance(count, int)

    async def test_guests_mapping(self, luma_client):
        events = await luma_client.list_events()
        event_id = events["entries"][0]["id"]
        guests = await luma_client.list_guests(event_id)
        await luma_client.close()

        for entry in guests["entries"][:5]:
            guest = entry.get("guest", entry)
            email = guest.get("user_email") or guest.get("email", "")
            assert email, f"Guest missing email: {list(guest.keys())}"
            name = guest.get("user_name") or guest.get("name", "")
            assert isinstance(name, str)
