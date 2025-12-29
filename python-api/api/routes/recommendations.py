"""
Recommendations API Routes

REST API endpoints for AI-powered recommendations including judge recommendations,
team formation suggestions, and RLHF feedback tracking.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.schemas.recommendations import (
    JudgeRecommendationsResponse,
    RecommendationFeedbackRequest,
    RecommendationFeedbackResponse,
    TeamSuggestionsRequest,
    TeamSuggestionsResponse,
)
from api.dependencies import get_current_user
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.dependencies import get_zerodb_client
from services.recommendations_service import RecommendationsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Recommendations"])


@router.get(
    "/hackathons/{hackathon_id}/recommendations/judge",
    response_model=JudgeRecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get judge recommendations",
    description="""
    Get AI-powered submission recommendations for a judge.

    Uses the judge's past evaluations and scoring patterns to recommend
    relevant submissions they haven't scored yet. For new judges without
    scoring history, returns diverse submissions to start reviewing.

    Requires JUDGE role in the hackathon.
    """,
)
async def get_judge_recommendations(
    hackathon_id: UUID,
    top_k: int = Query(
        10,
        ge=1,
        le=50,
        description="Maximum number of recommendations to return",
    ),
    current_user: dict = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> JudgeRecommendationsResponse:
    """
    Get AI-powered submission recommendations for a judge.

    Args:
        hackathon_id: Hackathon UUID
        top_k: Maximum number of recommendations (1-50)
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        JudgeRecommendationsResponse with recommended submissions

    Raises:
        HTTPException: 404 if judge not found in hackathon
        HTTPException: 500 if recommendation generation fails
    """
    service = RecommendationsService(zerodb_client)

    judge_id = current_user["user_id"]

    logger.info(
        f"Generating judge recommendations: "
        f"hackathon={hackathon_id}, judge={judge_id}, top_k={top_k}"
    )

    try:
        result = await service.recommend_submissions_for_judge(
            judge_id=judge_id,
            hackathon_id=str(hackathon_id),
            top_k=top_k,
        )

        return JudgeRecommendationsResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate judge recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations",
        )


@router.post(
    "/hackathons/{hackathon_id}/recommendations/team",
    response_model=TeamSuggestionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get team formation suggestions",
    description="""
    Get AI-powered suggestions for team formation based on complementary skills.

    Suggests available participants (not currently on teams) who match the
    requested skills or have complementary expertise. Uses semantic search
    to find participants with relevant experience.

    Requires BUILDER role in the hackathon.
    """,
)
async def get_team_suggestions(
    hackathon_id: UUID,
    request: TeamSuggestionsRequest,
    current_user: dict = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> TeamSuggestionsResponse:
    """
    Get AI-powered team formation suggestions.

    Args:
        hackathon_id: Hackathon UUID
        request: Team suggestions request with desired skills
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        TeamSuggestionsResponse with suggested participants

    Raises:
        HTTPException: 404 if participant not found in hackathon
        HTTPException: 500 if suggestion generation fails
    """
    service = RecommendationsService(zerodb_client)

    participant_id = current_user["user_id"]

    logger.info(
        f"Generating team suggestions: "
        f"hackathon={hackathon_id}, participant={participant_id}, "
        f"skills={request.desired_skills}, top_k={request.top_k}"
    )

    try:
        result = await service.suggest_team_formation(
            hackathon_id=str(hackathon_id),
            participant_id=participant_id,
            desired_skills=request.desired_skills,
            top_k=request.top_k,
        )

        return TeamSuggestionsResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate team suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate team suggestions",
        )


@router.post(
    "/recommendations/{recommendation_id}/feedback",
    response_model=RecommendationFeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Track recommendation feedback",
    description="""
    Track user feedback on recommendations for RLHF (Reinforcement Learning
    from Human Feedback) improvement.

    Feedback helps improve the quality of future recommendations by learning
    from user preferences and satisfaction levels.

    Feedback types:
    - thumbs_up: Positive feedback
    - thumbs_down: Negative feedback
    - rating: Numeric rating from 1-5 (requires rating field)
    """,
)
async def track_recommendation_feedback(
    recommendation_id: UUID,
    request: RecommendationFeedbackRequest,
    current_user: dict = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> RecommendationFeedbackResponse:
    """
    Track user feedback on a recommendation for RLHF improvement.

    Args:
        recommendation_id: Unique recommendation identifier
        request: Feedback request with type, rating, and optional comment
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        RecommendationFeedbackResponse confirming feedback was tracked

    Raises:
        HTTPException: 400 if invalid feedback type or missing rating
        HTTPException: 500 if feedback tracking fails
    """
    service = RecommendationsService(zerodb_client)

    user_id = current_user["user_id"]

    logger.info(
        f"Tracking recommendation feedback: "
        f"recommendation={recommendation_id}, user={user_id}, "
        f"type={request.feedback_type}, rating={request.rating}"
    )

    try:
        result = await service.track_recommendation_feedback(
            recommendation_id=str(recommendation_id),
            user_id=user_id,
            feedback_type=request.feedback_type,
            rating=request.rating,
            comment=request.comment,
        )

        return RecommendationFeedbackResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to track recommendation feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to track feedback",
        )
