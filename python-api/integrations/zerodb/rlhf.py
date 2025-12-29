"""
ZeroDB RLHF API Wrapper

Provides interface to ZeroDB's RLHF (Reinforcement Learning from Human Feedback) API
for collecting and analyzing AI interaction feedback.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RLHFAPI:
    """
    ZeroDB RLHF API wrapper.

    Provides methods for:
    - Logging AI interactions
    - Collecting user feedback
    - Generating improvement reports
    - Session tracking
    """

    def __init__(self, client):
        """
        Initialize RLHF API.

        Args:
            client: ZeroDBClient instance
        """
        self.client = client

    async def log_interaction(
        self,
        prompt: str,
        response: str,
        context: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Log an AI interaction for RLHF tracking.

        Args:
            prompt: User's input/request
            response: AI's response/suggestion
            context: Additional context (user_id, hackathon_id, feature_type, etc.)
            agent_id: Agent identifier (defaults to "dothack_backend")
            session_id: Session identifier for conversation tracking

        Returns:
            Dict containing interaction_id and success status

        Raises:
            ZeroDBError: If logging fails

        Example:
            >>> interaction = await rlhf.log_interaction(
            ...     prompt="Recommend submissions for judge-123",
            ...     response="Recommended 5 submissions based on expertise",
            ...     context={"user_id": "judge-123", "hackathon_id": "hack-456"},
            ...     agent_id="recommendations_service"
            ... )
        """
        path = "/v1/rlhf/interactions"

        payload = {
            "prompt": prompt,
            "response": response,
            "context": context or {},
            "agent_id": agent_id or "dothack_backend",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        result = await self.client._request("POST", path, json=payload)

        logger.info(f"Logged RLHF interaction: {result.get('interaction_id')}")

        return result

    async def submit_feedback(
        self,
        interaction_id: str,
        feedback_type: str,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Submit user feedback for an interaction.

        Args:
            interaction_id: ID of the interaction being rated
            feedback_type: Type of feedback ("thumbs_up", "thumbs_down", "rating")
            rating: Rating value 1-5 (required if feedback_type is "rating")
            comment: Optional user comment
            metadata: Additional metadata (e.g., outcome, action_taken)

        Returns:
            Dict with success status

        Raises:
            ZeroDBError: If submission fails
            ValueError: If invalid feedback_type or missing rating

        Example:
            >>> await rlhf.submit_feedback(
            ...     interaction_id="int-123",
            ...     feedback_type="rating",
            ...     rating=5,
            ...     comment="Perfect recommendations!"
            ... )
        """
        # Validate feedback_type
        valid_types = ["thumbs_up", "thumbs_down", "rating"]
        if feedback_type not in valid_types:
            raise ValueError(
                f"Invalid feedback_type: {feedback_type}. Must be one of: {valid_types}"
            )

        # Validate rating if feedback_type is "rating"
        if feedback_type == "rating":
            if rating is None or not (1 <= rating <= 5):
                raise ValueError(
                    "Rating must be between 1 and 5 for feedback_type='rating'"
                )

        path = f"/v1/rlhf/feedback"

        payload = {
            "interaction_id": interaction_id,
            "feedback_type": feedback_type,
            "rating": rating,
            "comment": comment,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        result = await self.client._request("POST", path, json=payload)

        logger.info(
            f"Submitted {feedback_type} feedback for interaction {interaction_id}"
        )

        return result

    async def get_interaction(
        self,
        interaction_id: str,
    ) -> Dict[str, Any]:
        """
        Get details of a specific interaction.

        Args:
            interaction_id: Interaction ID

        Returns:
            Dict with interaction details including prompt, response, feedback

        Raises:
            ZeroDBNotFound: If interaction doesn't exist
            ZeroDBError: If retrieval fails
        """
        path = f"/v1/rlhf/interactions/{interaction_id}"

        result = await self.client._request("GET", path)

        return result

    async def get_summary_report(
        self,
        time_range: str = "day",
        agent_id: Optional[str] = None,
        feature_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate RLHF summary report.

        Args:
            time_range: Time range for report ("hour", "day", "week", "month")
            agent_id: Filter by agent identifier
            feature_type: Filter by feature type (recommendations, search, etc.)

        Returns:
            Dict containing:
            - total_interactions: Total count
            - feedback_stats: Breakdown by type (thumbs_up, thumbs_down, rating)
            - average_rating: Average rating across all feedback
            - feedback_rate: % of interactions with feedback
            - top_issues: Common complaints or issues
            - improvement_suggestions: AI-generated suggestions

        Raises:
            ZeroDBError: If report generation fails

        Example:
            >>> report = await rlhf.get_summary_report(
            ...     time_range="week",
            ...     agent_id="recommendations_service"
            ... )
            >>> print(f"Total interactions: {report['total_interactions']}")
            >>> print(f"Average rating: {report['average_rating']}")
        """
        path = "/v1/rlhf/reports/summary"

        params = {
            "time_range": time_range,
        }

        if agent_id:
            params["agent_id"] = agent_id

        if feature_type:
            params["feature_type"] = feature_type

        result = await self.client._request("GET", path, params=params)

        logger.info(
            f"Generated RLHF summary report: {result.get('total_interactions')} interactions"
        )

        return result

    async def list_interactions(
        self,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        List recent interactions with optional filters.

        Args:
            agent_id: Filter by agent identifier
            session_id: Filter by session ID
            limit: Maximum results (default: 100)
            offset: Pagination offset

        Returns:
            Dict containing:
            - interactions: List of interaction objects
            - total_count: Total matching interactions
            - has_more: Whether more results exist

        Raises:
            ZeroDBError: If listing fails
        """
        path = "/v1/rlhf/interactions"

        params = {
            "limit": limit,
            "offset": offset,
        }

        if agent_id:
            params["agent_id"] = agent_id

        if session_id:
            params["session_id"] = session_id

        result = await self.client._request("GET", path, params=params)

        return result

    async def start_session(
        self,
        session_id: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Start RLHF data collection for a session.

        Args:
            session_id: Unique session identifier
            config: Session configuration

        Returns:
            Dict with session status

        Raises:
            ZeroDBError: If session start fails
        """
        path = "/v1/rlhf/sessions/start"

        payload = {
            "session_id": session_id,
            "config": config or {},
            "started_at": datetime.utcnow().isoformat(),
        }

        result = await self.client._request("POST", path, json=payload)

        logger.info(f"Started RLHF session: {session_id}")

        return result

    async def stop_session(
        self,
        session_id: str,
        export_data: bool = False,
    ) -> Dict[str, Any]:
        """
        Stop RLHF data collection for a session.

        Args:
            session_id: Session identifier
            export_data: Whether to export collected data

        Returns:
            Dict with session summary

        Raises:
            ZeroDBError: If session stop fails
        """
        path = "/v1/rlhf/sessions/stop"

        payload = {
            "session_id": session_id,
            "export_data": export_data,
            "stopped_at": datetime.utcnow().isoformat(),
        }

        result = await self.client._request("POST", path, json=payload)

        logger.info(f"Stopped RLHF session: {session_id}")

        return result
