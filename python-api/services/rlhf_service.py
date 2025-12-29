"""
RLHF Service

Provides Reinforcement Learning from Human Feedback (RLHF) functionality for
collecting and analyzing AI interaction feedback.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBNotFound, ZeroDBTimeoutError

logger = logging.getLogger(__name__)


class RLHFService:
    """Service for RLHF feedback collection and analysis."""

    def __init__(self, zerodb_client: ZeroDBClient):
        """
        Initialize RLHF service.

        Args:
            zerodb_client: ZeroDB client instance
        """
        self.zerodb = zerodb_client

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
            Dict containing:
            - success: Whether logging was successful
            - interaction_id: Unique interaction identifier
            - timestamp: When interaction was logged

        Raises:
            HTTPException: 500 if logging fails

        Example:
            >>> result = await rlhf_service.log_interaction(
            ...     prompt="Recommend submissions for judge-123",
            ...     response="Recommended 5 submissions",
            ...     context={"user_id": "judge-123", "hackathon_id": "hack-456"},
            ...     agent_id="recommendations_service"
            ... )
        """
        try:
            # Generate interaction ID
            interaction_id = f"int-{uuid.uuid4()}"

            # Log interaction using ZeroDB RLHF API
            result = await self.zerodb.rlhf.log_interaction(
                prompt=prompt,
                response=response,
                context=context or {},
                agent_id=agent_id or "dothack_backend",
                session_id=session_id,
            )

            logger.info(
                f"Logged RLHF interaction {interaction_id} "
                f"for agent {agent_id or 'dothack_backend'}"
            )

            return {
                "success": True,
                "interaction_id": result.get("interaction_id", interaction_id),
                "timestamp": datetime.utcnow(),
            }

        except (ZeroDBError, ZeroDBTimeoutError) as e:
            logger.error(f"Error logging RLHF interaction: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to log interaction",
            )

    async def submit_feedback(
        self,
        interaction_id: str,
        feedback_type: str,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Submit user feedback for an AI interaction.

        Args:
            interaction_id: ID of the interaction being rated
            feedback_type: Type of feedback ("thumbs_up", "thumbs_down", "rating")
            rating: Rating value 1-5 (required if feedback_type is "rating")
            comment: Optional user comment or explanation
            metadata: Additional metadata (e.g., outcome, action_taken)

        Returns:
            Dict containing:
            - success: Whether submission was successful
            - interaction_id: Interaction ID
            - feedback_tracked: Whether feedback was tracked
            - timestamp: When feedback was submitted

        Raises:
            HTTPException: 400 if invalid feedback_type or missing rating
            HTTPException: 404 if interaction not found
            HTTPException: 500 if submission fails

        Example:
            >>> result = await rlhf_service.submit_feedback(
            ...     interaction_id="int-123",
            ...     feedback_type="rating",
            ...     rating=5,
            ...     comment="Perfect recommendations!"
            ... )
        """
        try:
            # Validate feedback_type
            valid_types = ["thumbs_up", "thumbs_down", "rating"]
            if feedback_type not in valid_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid feedback_type. Must be one of: {valid_types}",
                )

            # Validate rating if feedback_type is "rating"
            if feedback_type == "rating":
                if rating is None or not (1 <= rating <= 5):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Rating must be between 1 and 5 for feedback_type='rating'",
                    )

            # Submit feedback using ZeroDB RLHF API
            result = await self.zerodb.rlhf.submit_feedback(
                interaction_id=interaction_id,
                feedback_type=feedback_type,
                rating=rating,
                comment=comment,
                metadata=metadata or {},
            )

            logger.info(
                f"Submitted {feedback_type} feedback for interaction {interaction_id}"
            )

            return {
                "success": True,
                "interaction_id": interaction_id,
                "feedback_tracked": True,
                "timestamp": datetime.utcnow(),
            }

        except ZeroDBNotFound:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interaction {interaction_id} not found",
            )
        except HTTPException:
            raise
        except (ZeroDBError, ZeroDBTimeoutError) as e:
            logger.error(f"Error submitting RLHF feedback: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit feedback",
            )

    async def get_interaction(
        self,
        interaction_id: str,
    ) -> Dict[str, Any]:
        """
        Get details of a specific interaction.

        Args:
            interaction_id: Interaction ID

        Returns:
            Dict containing interaction details including prompt, response, feedback

        Raises:
            HTTPException: 404 if interaction not found
            HTTPException: 500 if retrieval fails
        """
        try:
            result = await self.zerodb.rlhf.get_interaction(
                interaction_id=interaction_id
            )

            logger.info(f"Retrieved RLHF interaction {interaction_id}")

            return result

        except ZeroDBNotFound:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interaction {interaction_id} not found",
            )
        except (ZeroDBError, ZeroDBTimeoutError) as e:
            logger.error(f"Error retrieving RLHF interaction: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve interaction",
            )

    async def generate_summary_report(
        self,
        time_range: str = "day",
        agent_id: Optional[str] = None,
        feature_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive RLHF summary report.

        Args:
            time_range: Time range for report ("hour", "day", "week", "month")
            agent_id: Filter by agent identifier
            feature_type: Filter by feature type (recommendations, search, etc.)

        Returns:
            Dict containing:
            - time_range: Report time range
            - generated_at: When report was generated
            - total_interactions: Total interaction count
            - feedback_stats: Breakdown by feedback type
            - top_issues: Common issues identified
            - improvement_suggestions: AI-generated suggestions
            - feature_breakdown: Breakdown by feature type

        Raises:
            HTTPException: 400 if invalid time_range
            HTTPException: 500 if report generation fails

        Example:
            >>> report = await rlhf_service.generate_summary_report(
            ...     time_range="week",
            ...     agent_id="recommendations_service"
            ... )
            >>> print(f"Total interactions: {report['total_interactions']}")
            >>> print(f"Average rating: {report['feedback_stats']['average_rating']}")
        """
        try:
            # Validate time_range
            valid_ranges = ["hour", "day", "week", "month"]
            if time_range not in valid_ranges:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid time_range. Must be one of: {valid_ranges}",
                )

            # Generate report using ZeroDB RLHF API
            result = await self.zerodb.rlhf.get_summary_report(
                time_range=time_range,
                agent_id=agent_id,
                feature_type=feature_type,
            )

            logger.info(
                f"Generated RLHF summary report for time_range={time_range}, "
                f"agent_id={agent_id}, feature_type={feature_type}"
            )

            # Add generated_at timestamp
            result["generated_at"] = datetime.utcnow()

            return result

        except HTTPException:
            raise
        except (ZeroDBError, ZeroDBTimeoutError) as e:
            logger.error(f"Error generating RLHF summary report: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate summary report",
            )

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
            limit: Maximum results (default: 100, max: 1000)
            offset: Pagination offset

        Returns:
            Dict containing:
            - interactions: List of interaction objects
            - total_count: Total matching interactions
            - limit: Applied limit
            - offset: Applied offset
            - has_more: Whether more results exist

        Raises:
            HTTPException: 400 if invalid limit
            HTTPException: 500 if listing fails
        """
        try:
            # Validate limit
            if not (1 <= limit <= 1000):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Limit must be between 1 and 1000",
                )

            # List interactions using ZeroDB RLHF API
            result = await self.zerodb.rlhf.list_interactions(
                agent_id=agent_id,
                session_id=session_id,
                limit=limit,
                offset=offset,
            )

            logger.info(
                f"Listed {len(result.get('interactions', []))} RLHF interactions "
                f"(agent_id={agent_id}, session_id={session_id})"
            )

            return result

        except HTTPException:
            raise
        except (ZeroDBError, ZeroDBTimeoutError) as e:
            logger.error(f"Error listing RLHF interactions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list interactions",
            )

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
            HTTPException: 500 if session start fails
        """
        try:
            result = await self.zerodb.rlhf.start_session(
                session_id=session_id,
                config=config or {},
            )

            logger.info(f"Started RLHF session {session_id}")

            return result

        except (ZeroDBError, ZeroDBTimeoutError) as e:
            logger.error(f"Error starting RLHF session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start session",
            )

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
            HTTPException: 404 if session not found
            HTTPException: 500 if session stop fails
        """
        try:
            result = await self.zerodb.rlhf.stop_session(
                session_id=session_id,
                export_data=export_data,
            )

            logger.info(f"Stopped RLHF session {session_id}")

            return result

        except ZeroDBNotFound:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )
        except (ZeroDBError, ZeroDBTimeoutError) as e:
            logger.error(f"Error stopping RLHF session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stop session",
            )
