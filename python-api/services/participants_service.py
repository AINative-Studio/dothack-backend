"""
Participant Management Service

Business logic for participant operations.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import ZeroDBError

logger = logging.getLogger(__name__)


class ParticipantsService:
    """Service for managing hackathon participants."""

    def __init__(self, zerodb_client: ZeroDBClient):
        """
        Initialize participants service.

        Args:
            zerodb_client: ZeroDB client instance
        """
        self.zerodb = zerodb_client

    async def join_hackathon(
        self,
        hackathon_id: str,
        user_id: str,
        user_email: str,
        user_name: str,
        role: str = "BUILDER",
    ) -> dict:
        """
        Add user as participant to hackathon.

        Args:
            hackathon_id: Hackathon UUID
            user_id: User UUID from AINative auth
            user_email: User email
            user_name: User name
            role: Participant role (default: BUILDER)

        Returns:
            Created participant record

        Raises:
            HTTPException: 404 if hackathon not found
            HTTPException: 409 if already a participant
            HTTPException: 500 if database error
        """
        try:
            # Check if hackathon exists
            hackathon_rows = await self.zerodb.tables.query_rows(
                "hackathons", filter={"hackathon_id": hackathon_id}, limit=1
            )

            if not hackathon_rows:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Hackathon {hackathon_id} not found",
                )

            # Check if user is already a participant
            existing = await self.zerodb.tables.query_rows(
                "hackathon_participants",
                filter={"hackathon_id": hackathon_id, "participant_id": user_id},
                limit=1,
            )

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User is already a participant in this hackathon",
                )

            # Create participant record
            participant_record = {
                "id": str(uuid4()),
                "hackathon_id": hackathon_id,
                "participant_id": user_id,
                "role": role,
                "metadata": {
                    "ainative_user_email": user_email,
                    "ainative_user_name": user_name,
                },
                "joined_at": datetime.utcnow().isoformat(),
            }

            # Insert into database
            await self.zerodb.tables.insert_rows(
                "hackathon_participants", [participant_record]
            )

            logger.info(f"User {user_id} joined hackathon {hackathon_id} as {role}")

            # Add email and name to response for convenience
            participant_record["email"] = user_email
            participant_record["name"] = user_name

            return participant_record

        except HTTPException:
            raise
        except ZeroDBError as e:
            logger.error(f"Database error joining hackathon: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to join hackathon",
            )

    async def invite_judges(
        self,
        hackathon_id: str,
        organizer_id: str,
        judge_emails: list[str],
        message: Optional[str] = None,
    ) -> dict:
        """
        Invite judges to hackathon (ORGANIZER only).

        Args:
            hackathon_id: Hackathon UUID
            organizer_id: Organizer user ID (for logging)
            judge_emails: List of judge emails to invite
            message: Optional custom message

        Returns:
            Invite summary with count

        Note:
            For MVP, this creates placeholder participant records.
            In production, this would send email invitations.
        """
        try:
            # Check if hackathon exists
            hackathon_rows = await self.zerodb.tables.query_rows(
                "hackathons", filter={"hackathon_id": hackathon_id}, limit=1
            )

            if not hackathon_rows:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Hackathon {hackathon_id} not found",
                )

            # For MVP: Create placeholder JUDGE participant records
            # In production: Send emails via notification service
            invited_count = 0
            invited_emails_list = []

            for email in judge_emails:
                # Check if already invited (search by email in metadata)
                existing = await self.zerodb.tables.query_rows(
                    "hackathon_participants",
                    filter={"hackathon_id": hackathon_id},
                    limit=1000,  # Get all participants to check emails
                )

                # Check if email already exists
                already_invited = False
                for participant in existing:
                    participant_metadata = participant.get("metadata", {})
                    if participant_metadata.get("ainative_user_email") == email:
                        already_invited = True
                        break

                if already_invited:
                    logger.warning(
                        f"Judge {email} already invited to {hackathon_id}"
                    )
                    continue

                # Create placeholder judge record
                judge_record = {
                    "id": str(uuid4()),
                    "hackathon_id": hackathon_id,
                    "participant_id": str(
                        uuid4()
                    ),  # Placeholder until they register
                    "role": "JUDGE",
                    "metadata": {
                        "ainative_user_email": email,
                        "invited_by": organizer_id,
                        "invitation_message": message,
                        "status": "invited",  # invited | accepted | declined
                    },
                    "joined_at": datetime.utcnow().isoformat(),
                }

                await self.zerodb.tables.insert_rows(
                    "hackathon_participants", [judge_record]
                )

                invited_count += 1
                invited_emails_list.append(email)

            logger.info(
                f"Organizer {organizer_id} invited {invited_count} judges "
                f"to hackathon {hackathon_id}"
            )

            return {"invited_count": invited_count, "invited_emails": invited_emails_list}

        except HTTPException:
            raise
        except ZeroDBError as e:
            logger.error(f"Database error inviting judges: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to invite judges",
            )

    async def list_participants(
        self, hackathon_id: str, role: Optional[str] = None
    ) -> list[dict]:
        """
        List all participants in a hackathon.

        Args:
            hackathon_id: Hackathon UUID
            role: Optional role filter (BUILDER, JUDGE, etc.)

        Returns:
            List of participant records
        """
        try:
            # Build filter
            filter_dict = {"hackathon_id": hackathon_id}
            if role:
                filter_dict["role"] = role.upper()

            # Query participants
            participants = await self.zerodb.tables.query_rows(
                "hackathon_participants",
                filter=filter_dict,
                limit=1000,  # Reasonable limit for most hackathons
            )

            # Enrich with email and name from metadata
            for participant in participants:
                metadata = participant.get("metadata", {})
                participant["email"] = metadata.get("ainative_user_email")
                participant["name"] = metadata.get("ainative_user_name")

            logger.info(
                f"Listed {len(participants)} participants for hackathon {hackathon_id}"
            )

            return participants

        except ZeroDBError as e:
            logger.error(f"Database error listing participants: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list participants",
            )

    async def leave_hackathon(self, hackathon_id: str, user_id: str) -> bool:
        """
        Remove user as participant from hackathon.

        Args:
            hackathon_id: Hackathon UUID
            user_id: User UUID

        Returns:
            True if successful

        Raises:
            HTTPException: 404 if not a participant
            HTTPException: 409 if user has submissions (can't leave)
        """
        try:
            # Check if user is a participant
            participant_rows = await self.zerodb.tables.query_rows(
                "hackathon_participants",
                filter={"hackathon_id": hackathon_id, "participant_id": user_id},
                limit=1,
            )

            if not participant_rows:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User is not a participant in this hackathon",
                )

            participant = participant_rows[0]

            # Check if user has any submissions (business rule: can't leave after submitting)
            # First, find user's team(s) in this hackathon
            team_memberships = await self.zerodb.tables.query_rows(
                "team_members", filter={"participant_id": user_id}, limit=100
            )

            # For each team, check if there are submissions
            for membership in team_memberships:
                team_id = membership.get("team_id")

                submissions = await self.zerodb.tables.query_rows(
                    "projects",
                    filter={
                        "hackathon_id": hackathon_id,
                        "team_id": team_id,
                        "status": "SUBMITTED",
                    },
                    limit=1,
                )

                if submissions:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Cannot leave hackathon after submitting a project",
                    )

            # Delete participant record
            participant_id = participant.get("id")
            await self.zerodb.tables.delete_rows(
                "hackathon_participants", filter={"id": participant_id}
            )

            logger.info(f"User {user_id} left hackathon {hackathon_id}")

            return True

        except HTTPException:
            raise
        except ZeroDBError as e:
            logger.error(f"Database error leaving hackathon: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to leave hackathon",
            )
