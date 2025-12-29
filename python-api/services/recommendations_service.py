"""
AI-Powered Recommendations Service

Provides intelligent recommendations for judges and organizers using
semantic search, embeddings, and RLHF feedback tracking.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBTimeoutError

logger = logging.getLogger(__name__)


class RecommendationsService:
    """Service for AI-powered recommendations."""

    def __init__(self, zerodb_client: ZeroDBClient):
        """
        Initialize recommendations service.

        Args:
            zerodb_client: ZeroDB client instance
        """
        self.zerodb = zerodb_client

    async def recommend_submissions_for_judge(
        self,
        judge_id: str,
        hackathon_id: str,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """
        Recommend submissions for a judge to review.

        Uses judge's past evaluations and preferences to recommend
        relevant submissions they haven't scored yet.

        Args:
            judge_id: Judge user ID
            hackathon_id: Hackathon ID to recommend submissions from
            top_k: Maximum number of recommendations (default: 10)

        Returns:
            Dict containing:
            - recommended_submissions: List of submission recommendations
            - total_recommended: Total count
            - recommendation_reason: Why these were recommended

        Raises:
            HTTPException: 404 if judge or hackathon not found
            HTTPException: 500 if recommendation fails
        """
        start_time = time.time()

        try:
            # Verify judge is participant in hackathon
            judge_rows = await self.zerodb.tables.query_rows(
                "hackathon_participants",
                filter={
                    "hackathon_id": hackathon_id,
                    "participant_id": judge_id,
                    "role": "JUDGE",
                },
                limit=1,
            )

            if not judge_rows:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Judge {judge_id} not found in hackathon {hackathon_id}",
                )

            # Get submissions the judge has already scored
            scored_submissions = await self.zerodb.tables.query_rows(
                "scores",
                filter={
                    "hackathon_id": hackathon_id,
                    "judge_id": judge_id,
                },
                limit=1000,
            )
            scored_submission_ids = {
                score["submission_id"] for score in scored_submissions
            }

            # Get all submissions in hackathon
            all_submissions = await self.zerodb.tables.query_rows(
                "submissions",
                filter={
                    "hackathon_id": hackathon_id,
                    "status": "SUBMITTED",
                },
                limit=1000,
            )

            # Filter out already scored submissions
            unscored_submissions = [
                sub
                for sub in all_submissions
                if sub["submission_id"] not in scored_submission_ids
            ]

            # If judge has scored submissions, use those to find similar unscored ones
            if scored_submissions:
                # Get judge's highest-rated submissions
                high_rated = sorted(
                    scored_submissions,
                    key=lambda x: x.get("total_score", 0),
                    reverse=True,
                )[:3]

                # Build query from judge's preferences
                query_texts = []
                for submission_data in high_rated:
                    # Get full submission details
                    sub_rows = await self.zerodb.tables.query_rows(
                        "submissions",
                        filter={"submission_id": submission_data["submission_id"]},
                        limit=1,
                    )
                    if sub_rows:
                        sub = sub_rows[0]
                        query_texts.append(
                            f"{sub.get('project_name', '')} {sub.get('description', '')}"
                        )

                query = " ".join(query_texts)
                reason = "Based on your highly-rated submissions"
            else:
                # No scoring history - recommend diverse submissions
                query = "innovative creative unique interesting"
                reason = "Diverse submissions to start reviewing"

            # Search for relevant submissions
            search_results = await self.zerodb.embeddings.search(
                query=query,
                namespace=f"hackathons/{hackathon_id}/submissions",
                top_k=top_k * 2,  # Get extra to filter
                similarity_threshold=0.3,
                include_metadata=True,
            )

            # Filter and deduplicate recommendations
            recommendations = []
            seen_ids = set()

            for result in search_results:
                submission_id = result.get("id")

                # Skip if already scored or duplicate
                if (
                    submission_id in scored_submission_ids
                    or submission_id in seen_ids
                ):
                    continue

                # Get full submission details
                sub_rows = await self.zerodb.tables.query_rows(
                    "submissions",
                    filter={"submission_id": submission_id},
                    limit=1,
                )

                if sub_rows:
                    submission = sub_rows[0]
                    submission["relevance_score"] = result.get("score", 0.0)
                    recommendations.append(submission)
                    seen_ids.add(submission_id)

                if len(recommendations) >= top_k:
                    break

            execution_time = (time.time() - start_time) * 1000

            logger.info(
                f"Recommended {len(recommendations)} submissions for judge {judge_id} "
                f"in {execution_time:.2f}ms"
            )

            return {
                "recommended_submissions": recommendations,
                "total_recommended": len(recommendations),
                "recommendation_reason": reason,
                "execution_time_ms": round(execution_time, 2),
            }

        except HTTPException:
            raise
        except (ZeroDBError, ZeroDBTimeoutError) as e:
            logger.error(f"Error generating judge recommendations: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate recommendations",
            )

    async def suggest_team_formation(
        self,
        hackathon_id: str,
        participant_id: str,
        desired_skills: Optional[List[str]] = None,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """
        Suggest potential team members based on complementary skills.

        Args:
            hackathon_id: Hackathon ID
            participant_id: User seeking team members
            desired_skills: Optional list of desired skills
            top_k: Maximum number of suggestions (default: 10)

        Returns:
            Dict containing:
            - suggested_participants: List of participant suggestions
            - total_suggested: Total count
            - suggestion_reason: Why these were suggested

        Raises:
            HTTPException: 404 if participant or hackathon not found
            HTTPException: 500 if suggestion fails
        """
        start_time = time.time()

        try:
            # Verify participant exists in hackathon
            participant_rows = await self.zerodb.tables.query_rows(
                "hackathon_participants",
                filter={
                    "hackathon_id": hackathon_id,
                    "participant_id": participant_id,
                },
                limit=1,
            )

            if not participant_rows:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Participant {participant_id} not found in hackathon {hackathon_id}",
                )

            # Get participants already on teams
            team_members = await self.zerodb.tables.query_rows(
                "team_members",
                filter={"hackathon_id": hackathon_id},
                limit=1000,
            )
            participants_on_teams = {member["participant_id"] for member in team_members}

            # Get all BUILDER participants not on teams
            all_participants = await self.zerodb.tables.query_rows(
                "hackathon_participants",
                filter={
                    "hackathon_id": hackathon_id,
                    "role": "BUILDER",
                },
                limit=1000,
            )

            available_participants = [
                p
                for p in all_participants
                if p["participant_id"] not in participants_on_teams
                and p["participant_id"] != participant_id
            ]

            # Build search query from desired skills
            if desired_skills:
                query = " ".join(desired_skills)
                reason = f"Participants with skills: {', '.join(desired_skills)}"
            else:
                query = "experienced developer designer collaborative teamwork"
                reason = "Diverse skilled participants available for teaming"

            # Search for participants with matching skills
            # Note: This assumes participant profiles are embedded
            search_results = await self.zerodb.embeddings.search(
                query=query,
                namespace=f"hackathons/{hackathon_id}/participants",
                top_k=top_k * 2,
                similarity_threshold=0.3,
                include_metadata=True,
            )

            # Filter and build suggestions
            suggestions = []
            seen_ids = set()

            for result in search_results:
                participant_result_id = result.get("id")

                # Skip if already processed or on a team
                if (
                    participant_result_id in seen_ids
                    or participant_result_id in participants_on_teams
                    or participant_result_id == participant_id
                ):
                    continue

                # Find participant in available list
                matching_participant = next(
                    (
                        p
                        for p in available_participants
                        if p["participant_id"] == participant_result_id
                    ),
                    None,
                )

                if matching_participant:
                    matching_participant["match_score"] = result.get("score", 0.0)
                    suggestions.append(matching_participant)
                    seen_ids.add(participant_result_id)

                if len(suggestions) >= top_k:
                    break

            # If no semantic results, return random available participants
            if not suggestions and available_participants:
                suggestions = available_participants[:top_k]
                for suggestion in suggestions:
                    suggestion["match_score"] = 0.5
                reason = "Available participants in hackathon"

            execution_time = (time.time() - start_time) * 1000

            logger.info(
                f"Suggested {len(suggestions)} team members for participant {participant_id} "
                f"in {execution_time:.2f}ms"
            )

            return {
                "suggested_participants": suggestions,
                "total_suggested": len(suggestions),
                "suggestion_reason": reason,
                "execution_time_ms": round(execution_time, 2),
            }

        except HTTPException:
            raise
        except (ZeroDBError, ZeroDBTimeoutError) as e:
            logger.error(f"Error generating team suggestions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate team suggestions",
            )

    async def track_recommendation_feedback(
        self,
        recommendation_id: str,
        user_id: str,
        feedback_type: str,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Track user feedback on recommendations for RLHF improvement.

        Args:
            recommendation_id: Unique recommendation identifier
            user_id: User providing feedback
            feedback_type: "thumbs_up", "thumbs_down", or "rating"
            rating: Rating value 1-5 (required if feedback_type is "rating")
            comment: Optional feedback comment

        Returns:
            Dict with feedback confirmation

        Raises:
            HTTPException: 400 if invalid feedback_type or missing rating
            HTTPException: 500 if tracking fails
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

            # Store feedback using RLHF data collection
            feedback_record = {
                "recommendation_id": recommendation_id,
                "user_id": user_id,
                "feedback_type": feedback_type,
                "rating": rating,
                "comment": comment,
                "agent_id": "recommendations_service",
                "context": {
                    "recommendation_type": "ai_powered",
                    "service": "recommendations",
                },
            }

            # Note: In production, this would use mcp__zerodb__zerodb_rlhf_agent_feedback
            # For now, store in a custom feedback table
            await self.zerodb.tables.insert_rows(
                "recommendation_feedback",
                rows=[feedback_record],
            )

            logger.info(
                f"Tracked {feedback_type} feedback for recommendation {recommendation_id} "
                f"from user {user_id}"
            )

            return {
                "success": True,
                "recommendation_id": recommendation_id,
                "feedback_tracked": True,
            }

        except HTTPException:
            raise
        except ZeroDBError as e:
            logger.error(f"Error tracking recommendation feedback: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to track feedback",
            )
