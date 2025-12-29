"""
ZeroDB Events API Wrapper

Provides methods for event streaming operations.
"""

from typing import Any, Optional


class EventsAPI:
    """
    Wrapper for ZeroDB Events API operations.

    Provides methods for:
    - Creating events
    - Publishing events to the event stream
    - Event-driven architecture support
    """

    def __init__(self, client):
        """
        Initialize EventsAPI wrapper.

        Args:
            client: ZeroDBClient instance
        """
        self.client = client

    async def create(
        self,
        event_type: str,
        data: dict[str, Any],
        source: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create and publish an event to the event stream.

        Args:
            event_type: Type of event (e.g., "hackathon.created", "submission.created")
            data: Event payload data
            source: Optional event source identifier
            correlation_id: Optional correlation ID for event tracking

        Returns:
            Dict with event confirmation including event_id

        Example:
            await client.events.create(
                event_type="submission.created",
                data={
                    "submission_id": "uuid-123",
                    "hackathon_id": "uuid-456",
                    "team_id": "uuid-789"
                },
                source="dothack-api",
                correlation_id="correlation-abc"
            )
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/events"
        payload = {
            "event_type": event_type,
            "data": data,
        }
        if source:
            payload["source"] = source
        if correlation_id:
            payload["correlation_id"] = correlation_id

        return await self.client._request("POST", path, json=payload)

    async def publish(
        self,
        event_type: str,
        data: dict[str, Any],
        **kwargs,
    ) -> dict[str, Any]:
        """
        Alias for create() method - publishes an event.

        Args:
            event_type: Type of event
            data: Event payload data
            **kwargs: Additional arguments (source, correlation_id)

        Returns:
            Dict with event confirmation
        """
        return await self.create(event_type, data, **kwargs)
