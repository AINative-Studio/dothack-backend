"""
Event Service for DotHack Event Streaming

Publishes events to ZeroDB Events API for real-time event-driven architecture.
Handles event validation, metadata enrichment, error handling, and retry logic.

Performance Target: < 50ms for event delivery
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBRateLimitError,
    ZeroDBTimeoutError,
)
from api.schemas.events import (
    BaseEventMetadata,
    HackathonEventData,
    TeamEventData,
    SubmissionEventData,
    ScoreEventData,
)

# Configure logger
logger = logging.getLogger(__name__)

# Event type constants
HACKATHON_CREATED = "hackathon.created"
HACKATHON_STARTED = "hackathon.started"
HACKATHON_CLOSED = "hackathon.closed"
TEAM_FORMED = "team.formed"
TEAM_UPDATED = "team.updated"
TEAM_MEMBER_ADDED = "team.member_added"
TEAM_MEMBER_REMOVED = "team.member_removed"
SUBMISSION_CREATED = "submission.created"
SUBMISSION_UPDATED = "submission.updated"
SUBMISSION_FINALIZED = "submission.finalized"
SCORE_SUBMITTED = "score.submitted"
SCORE_UPDATED = "score.updated"
JUDGING_COMPLETED = "judging.completed"


class EventService:
    """
    Event publishing service for DotHack platform.

    Provides methods for publishing events to ZeroDB Events API with:
    - Automatic metadata enrichment
    - Schema validation via Pydantic models
    - Error handling and retry logic
    - Correlation ID tracking for event chains

    Example:
        >>> service = EventService(zerodb_client)
        >>> await service.publish_hackathon_created(
        ...     hackathon_id="hack-123",
        ...     name="AI Hackathon",
        ...     status="draft",
        ...     organizer_id="user-456",
        ...     user_id="user-456"
        ... )
    """

    def __init__(self, zerodb_client: ZeroDBClient):
        """
        Initialize EventService with ZeroDB client.

        Args:
            zerodb_client: ZeroDBClient instance for event publishing
        """
        self.client = zerodb_client

    def _create_metadata(
        self,
        user_id: str,
        correlation_id: Optional[str] = None,
        source: str = "dothack-api",
    ) -> BaseEventMetadata:
        """
        Create event metadata with timestamp and correlation ID.

        Args:
            user_id: User ID who triggered the event
            correlation_id: Optional correlation ID (auto-generated if not provided)
            source: Event source identifier (default: "dothack-api")

        Returns:
            BaseEventMetadata with enriched fields
        """
        if not correlation_id:
            correlation_id = f"corr-{uuid.uuid4().hex[:12]}"

        return BaseEventMetadata(
            user_id=user_id,
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id,
            source=source,
        )

    async def _publish_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Internal method to publish events to ZeroDB Events API.

        Handles errors gracefully - logs failures but doesn't raise exceptions
        to avoid breaking the main application flow.

        Args:
            event_type: Event type (e.g., "hackathon.created")
            event_data: Event payload data (already validated)
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dict with event confirmation or error details

        Performance:
            Target: < 50ms for successful delivery
        """
        try:
            logger.info(f"Publishing event: {event_type}", extra={
                "event_type": event_type,
                "correlation_id": correlation_id
            })

            result = await self.client.events.create(
                event_type=event_type,
                data=event_data,
                source="dothack-api",
                correlation_id=correlation_id,
            )

            logger.info(f"Event published successfully: {event_type}", extra={
                "event_type": event_type,
                "event_id": result.get("event_id"),
                "correlation_id": correlation_id
            })

            return result

        except ZeroDBTimeoutError as e:
            logger.error(f"Timeout publishing event {event_type}: {str(e)}", extra={
                "event_type": event_type,
                "correlation_id": correlation_id,
                "error": "timeout"
            })
            return {"success": False, "error": "timeout", "message": str(e)}

        except ZeroDBRateLimitError as e:
            logger.warning(f"Rate limit publishing event {event_type}: {str(e)}", extra={
                "event_type": event_type,
                "correlation_id": correlation_id,
                "error": "rate_limit"
            })
            return {"success": False, "error": "rate_limit", "message": str(e)}

        except ZeroDBError as e:
            logger.error(f"ZeroDB error publishing event {event_type}: {str(e)}", extra={
                "event_type": event_type,
                "correlation_id": correlation_id,
                "error": "zerodb_error"
            })
            return {"success": False, "error": "zerodb_error", "message": str(e)}

        except Exception as e:
            logger.exception(f"Unexpected error publishing event {event_type}: {str(e)}", extra={
                "event_type": event_type,
                "correlation_id": correlation_id,
                "error": "unexpected"
            })
            return {"success": False, "error": "unexpected", "message": str(e)}

    # Hackathon Events

    async def publish_hackathon_created(
        self,
        hackathon_id: str,
        name: str,
        status: str,
        organizer_id: str,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        location: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publish hackathon.created event.

        Args:
            hackathon_id: Unique hackathon identifier
            name: Hackathon name
            status: Current status (typically "draft")
            organizer_id: Organizer user ID
            user_id: User who created the hackathon (for metadata)
            start_date: Optional start date
            end_date: Optional end date
            location: Optional location
            correlation_id: Optional correlation ID

        Returns:
            Dict with event confirmation
        """
        metadata = self._create_metadata(user_id, correlation_id)

        event_data = HackathonEventData(
            hackathon_id=hackathon_id,
            name=name,
            status=status,
            organizer_id=organizer_id,
            start_date=start_date,
            end_date=end_date,
            location=location,
            metadata=metadata,
        )

        return await self._publish_event(
            event_type=HACKATHON_CREATED,
            event_data=event_data.model_dump(mode="json"),
            correlation_id=metadata.correlation_id,
        )

    async def publish_hackathon_started(
        self,
        hackathon_id: str,
        name: str,
        organizer_id: str,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        location: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publish hackathon.started event (when status changes to "active").

        Args:
            hackathon_id: Unique hackathon identifier
            name: Hackathon name
            organizer_id: Organizer user ID
            user_id: User who started the hackathon (for metadata)
            start_date: Start date
            end_date: End date
            location: Optional location
            correlation_id: Optional correlation ID

        Returns:
            Dict with event confirmation
        """
        metadata = self._create_metadata(user_id, correlation_id)

        event_data = HackathonEventData(
            hackathon_id=hackathon_id,
            name=name,
            status="active",
            organizer_id=organizer_id,
            start_date=start_date,
            end_date=end_date,
            location=location,
            metadata=metadata,
        )

        return await self._publish_event(
            event_type=HACKATHON_STARTED,
            event_data=event_data.model_dump(mode="json"),
            correlation_id=metadata.correlation_id,
        )

    async def publish_hackathon_closed(
        self,
        hackathon_id: str,
        name: str,
        status: str,
        organizer_id: str,
        user_id: str,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publish hackathon.closed event (when status changes to "completed" or "cancelled").

        Args:
            hackathon_id: Unique hackathon identifier
            name: Hackathon name
            status: Final status ("completed" or "cancelled")
            organizer_id: Organizer user ID
            user_id: User who closed the hackathon (for metadata)
            correlation_id: Optional correlation ID

        Returns:
            Dict with event confirmation
        """
        metadata = self._create_metadata(user_id, correlation_id)

        event_data = HackathonEventData(
            hackathon_id=hackathon_id,
            name=name,
            status=status,
            organizer_id=organizer_id,
            metadata=metadata,
        )

        return await self._publish_event(
            event_type=HACKATHON_CLOSED,
            event_data=event_data.model_dump(mode="json"),
            correlation_id=metadata.correlation_id,
        )

    # Team Events

    async def publish_team_formed(
        self,
        team_id: str,
        hackathon_id: str,
        name: str,
        creator_id: str,
        user_id: str,
        status: str = "FORMING",
        member_count: int = 1,
        track_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publish team.formed event (when new team is created).

        Args:
            team_id: Unique team identifier
            hackathon_id: Associated hackathon ID
            name: Team name
            creator_id: Team creator/lead user ID
            user_id: User who formed the team (for metadata, usually same as creator_id)
            status: Team status (default: "FORMING")
            member_count: Number of members (default: 1)
            track_id: Optional track ID
            correlation_id: Optional correlation ID

        Returns:
            Dict with event confirmation
        """
        metadata = self._create_metadata(user_id, correlation_id)

        event_data = TeamEventData(
            team_id=team_id,
            hackathon_id=hackathon_id,
            name=name,
            creator_id=creator_id,
            status=status,
            member_count=member_count,
            track_id=track_id,
            metadata=metadata,
        )

        return await self._publish_event(
            event_type=TEAM_FORMED,
            event_data=event_data.model_dump(mode="json"),
            correlation_id=metadata.correlation_id,
        )

    # Submission Events

    async def publish_submission_created(
        self,
        submission_id: str,
        hackathon_id: str,
        team_id: str,
        title: str,
        submitted_by: str,
        user_id: str,
        status: str = "DRAFT",
        track_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publish submission.created event (when new submission is created).

        Args:
            submission_id: Unique submission identifier
            hackathon_id: Associated hackathon ID
            team_id: Submitting team ID
            title: Submission title
            submitted_by: User ID who created the submission
            user_id: User who triggered the event (for metadata, usually same as submitted_by)
            status: Submission status (default: "DRAFT")
            track_id: Optional track ID
            correlation_id: Optional correlation ID

        Returns:
            Dict with event confirmation
        """
        metadata = self._create_metadata(user_id, correlation_id)

        event_data = SubmissionEventData(
            submission_id=submission_id,
            hackathon_id=hackathon_id,
            team_id=team_id,
            track_id=track_id,
            title=title,
            status=status,
            submitted_by=submitted_by,
            metadata=metadata,
        )

        return await self._publish_event(
            event_type=SUBMISSION_CREATED,
            event_data=event_data.model_dump(mode="json"),
            correlation_id=metadata.correlation_id,
        )

    # Score/Judging Events

    async def publish_score_submitted(
        self,
        score_id: str,
        submission_id: str,
        hackathon_id: str,
        judge_id: str,
        user_id: str,
        technical_score: Optional[float] = None,
        creativity_score: Optional[float] = None,
        impact_score: Optional[float] = None,
        presentation_score: Optional[float] = None,
        total_score: Optional[float] = None,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publish score.submitted event (when judge submits scores).

        Args:
            score_id: Unique score identifier
            submission_id: Submission being scored
            hackathon_id: Associated hackathon ID
            judge_id: Judge user ID
            user_id: User who submitted the score (for metadata, usually same as judge_id)
            technical_score: Optional technical score (0-10)
            creativity_score: Optional creativity score (0-10)
            impact_score: Optional impact score (0-10)
            presentation_score: Optional presentation score (0-10)
            total_score: Optional total/average score
            correlation_id: Optional correlation ID

        Returns:
            Dict with event confirmation
        """
        metadata = self._create_metadata(user_id, correlation_id)

        event_data = ScoreEventData(
            score_id=score_id,
            submission_id=submission_id,
            hackathon_id=hackathon_id,
            judge_id=judge_id,
            technical_score=technical_score,
            creativity_score=creativity_score,
            impact_score=impact_score,
            presentation_score=presentation_score,
            total_score=total_score,
            metadata=metadata,
        )

        return await self._publish_event(
            event_type=SCORE_SUBMITTED,
            event_data=event_data.model_dump(mode="json"),
            correlation_id=metadata.correlation_id,
        )


# Convenience function for creating EventService instance
def get_event_service(zerodb_client: ZeroDBClient) -> EventService:
    """
    Factory function to create EventService instance.

    Args:
        zerodb_client: ZeroDBClient instance

    Returns:
        EventService instance
    """
    return EventService(zerodb_client)
