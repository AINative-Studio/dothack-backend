"""
Prize Service

Business logic for managing hackathon prizes.
Handles CRUD operations with validation, authorization checks, and prize pool calculations.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)

logger = logging.getLogger(__name__)


class PrizeService:
    """Service for managing hackathon prizes."""

    def __init__(self, zerodb_client: ZeroDBClient):
        """
        Initialize prize service.

        Args:
            zerodb_client: ZeroDB client instance
        """
        self.zerodb = zerodb_client

    async def create_prize(
        self,
        hackathon_id: str,
        title: str,
        rank: int,
        description: Optional[str] = None,
        amount: Optional[Decimal] = None,
        currency: str = "USD",
        track_id: Optional[str] = None,
        sponsor_name: Optional[str] = None,
        display_order: Optional[int] = None,
    ) -> Dict:
        """
        Create a new prize for a hackathon.

        Args:
            hackathon_id: UUID of the hackathon
            title: Prize title
            rank: Prize ranking (1=first place, 2=second, etc.)
            description: Optional prize description
            amount: Optional prize amount
            currency: Currency code (default: USD)
            track_id: Optional track ID for track-specific prizes
            sponsor_name: Optional sponsor name
            display_order: Optional display order (defaults to rank if not provided)

        Returns:
            Created prize record

        Raises:
            HTTPException: 404 if hackathon not found
            HTTPException: 404 if track_id provided but track not found
            HTTPException: 409 if rank conflicts with existing prize for same scope
            HTTPException: 500 for database errors
            HTTPException: 504 for timeout errors
        """
        try:
            # Verify hackathon exists
            hackathons = await self.zerodb.tables.query_rows(
                "hackathons",
                filter={"hackathon_id": hackathon_id},
            )

            if not hackathons:
                logger.warning(f"Hackathon {hackathon_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Hackathon {hackathon_id} not found",
                )

            # If track_id provided, verify track exists and belongs to hackathon
            if track_id:
                tracks = await self.zerodb.tables.query_rows(
                    "tracks",
                    filter={"track_id": track_id, "hackathon_id": hackathon_id},
                )

                if not tracks:
                    logger.warning(
                        f"Track {track_id} not found for hackathon {hackathon_id}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Track {track_id} not found for this hackathon",
                    )

            # Check for rank uniqueness within the same scope
            # (hackathon-level or track-level)
            prize_filter = {
                "hackathon_id": hackathon_id,
                "rank": rank,
            }

            if track_id:
                prize_filter["track_id"] = track_id
            else:
                # For hackathon-level prizes, ensure track_id is None
                prize_filter["track_id"] = None

            existing_prizes = await self.zerodb.tables.query_rows(
                "prizes",
                filter=prize_filter,
            )

            if existing_prizes:
                scope = f"track {track_id}" if track_id else "hackathon"
                logger.warning(
                    f"Prize with rank {rank} already exists for {scope} in hackathon {hackathon_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Prize with rank {rank} already exists for this {scope}",
                )

            # Create prize record
            prize_id = str(uuid4())
            now = datetime.utcnow()

            # Use rank as display_order if not provided
            if display_order is None:
                display_order = rank

            prize_data = {
                "prize_id": prize_id,
                "hackathon_id": hackathon_id,
                "title": title,
                "description": description,
                "amount": str(amount) if amount is not None else None,
                "currency": currency,
                "rank": rank,
                "track_id": track_id,
                "sponsor_name": sponsor_name,
                "display_order": display_order,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            await self.zerodb.tables.insert_rows("prizes", [prize_data])

            logger.info(f"Created prize {prize_id} for hackathon {hackathon_id}")

            # Convert amount back to Decimal for response
            return {
                "prize_id": prize_id,
                "hackathon_id": hackathon_id,
                "title": title,
                "description": description,
                "amount": amount,
                "currency": currency,
                "rank": rank,
                "track_id": track_id,
                "sponsor_name": sponsor_name,
                "display_order": display_order,
                "created_at": now,
                "updated_at": now,
            }

        except HTTPException:
            raise

        except ZeroDBTimeoutError as e:
            logger.error(f"Timeout creating prize: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timed out. Please try again.",
            )

        except (ZeroDBError, ZeroDBNotFound) as e:
            logger.error(f"Database error creating prize: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create prize. Please contact support.",
            )

        except Exception as e:
            logger.error(f"Unexpected error creating prize: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please contact support.",
            )

    async def list_prizes(
        self,
        hackathon_id: str,
        track_id: Optional[str] = None,
        rank: Optional[int] = None,
    ) -> Dict:
        """
        List all prizes for a hackathon with optional filters.

        Args:
            hackathon_id: UUID of the hackathon
            track_id: Optional filter by track ID
            rank: Optional filter by rank

        Returns:
            Dict with prizes list, total count, hackathon_id, and total_prize_pool

        Raises:
            HTTPException: 404 if hackathon not found
            HTTPException: 500 for database errors
            HTTPException: 504 for timeout errors
        """
        try:
            # Verify hackathon exists (skip if table not found)
            try:
                hackathons = await self.zerodb.tables.query_rows(
                    "hackathons",
                    filter={"hackathon_id": hackathon_id},
                )
                if not hackathons:
                    logger.warning(f"Hackathon {hackathon_id} not found")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Hackathon {hackathon_id} not found",
                    )
            except ZeroDBNotFound:
                logger.info(f"hackathons table not found, skipping verification")

            # Build query filter
            prize_filter: Dict = {"hackathon_id": hackathon_id}

            if track_id is not None:
                prize_filter["track_id"] = track_id

            if rank is not None:
                prize_filter["rank"] = rank

            # Query prizes - handle table not found gracefully
            try:
                prizes = await self.zerodb.tables.query_rows(
                    "prizes",
                    filter=prize_filter,
                )
            except ZeroDBNotFound:
                # Prizes table doesn't exist yet - return empty list
                logger.info("prizes table not found, returning empty list")
                return {
                    "prizes": [],
                    "total": 0,
                    "hackathon_id": hackathon_id,
                    "total_prize_pool": None,
                }

            # Parse datetime strings and amounts, map ZeroDB fields
            for prize in prizes:
                # Map _row_id to prize_id if prize_id is missing
                if not prize.get("prize_id") and prize.get("_row_id"):
                    prize["prize_id"] = prize["_row_id"]
                # Map _created_at to created_at if created_at is missing
                if not prize.get("created_at") and prize.get("_created_at"):
                    prize["created_at"] = prize["_created_at"]
                # Ensure updated_at has a value
                if not prize.get("updated_at"):
                    prize["updated_at"] = prize.get("created_at", datetime.utcnow().isoformat())
                # Ensure hackathon_id is present
                if not prize.get("hackathon_id"):
                    prize["hackathon_id"] = hackathon_id
                # Default display_order to rank if missing
                if prize.get("display_order") is None and prize.get("rank") is not None:
                    prize["display_order"] = prize["rank"]
                # Default currency if missing
                if not prize.get("currency"):
                    prize["currency"] = "USD"

                if "created_at" in prize and isinstance(prize["created_at"], str):
                    try:
                        prize["created_at"] = datetime.fromisoformat(prize["created_at"])
                    except (ValueError, TypeError):
                        prize["created_at"] = datetime.utcnow()
                if "updated_at" in prize and isinstance(prize["updated_at"], str):
                    try:
                        prize["updated_at"] = datetime.fromisoformat(prize["updated_at"])
                    except (ValueError, TypeError):
                        prize["updated_at"] = datetime.utcnow()
                if "amount" in prize and prize["amount"] is not None:
                    try:
                        prize["amount"] = Decimal(str(prize["amount"]))
                    except Exception:
                        prize["amount"] = None

            # Sort by display_order, then rank
            prizes.sort(key=lambda x: (x.get("display_order", 999), x.get("rank", 999)))

            # Calculate total prize pool by currency
            prize_pool = {}
            for prize in prizes:
                if prize.get("amount") is not None:
                    currency = prize.get("currency", "USD")
                    amount = prize["amount"]
                    prize_pool[currency] = prize_pool.get(currency, Decimal(0)) + amount

            # Convert Decimal to float for JSON serialization
            prize_pool_json = {k: float(v) for k, v in prize_pool.items()}

            logger.info(f"Retrieved {len(prizes)} prizes for hackathon {hackathon_id}")

            return {
                "prizes": prizes,
                "total": len(prizes),
                "hackathon_id": hackathon_id,
                "total_prize_pool": prize_pool_json if prize_pool_json else None,
            }

        except HTTPException:
            raise

        except ZeroDBTimeoutError as e:
            logger.error(f"Timeout listing prizes: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timed out. Please try again.",
            )

        except ZeroDBError as e:
            logger.error(f"Database error listing prizes: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve prizes. Please contact support.",
            )

        except Exception as e:
            logger.error(f"Unexpected error listing prizes: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please contact support.",
            )

    async def get_prize(self, hackathon_id: str, prize_id: str) -> Dict:
        """
        Get a specific prize by ID.

        Args:
            hackathon_id: UUID of the hackathon
            prize_id: UUID of the prize

        Returns:
            Prize record

        Raises:
            HTTPException: 404 if prize not found or doesn't belong to hackathon
            HTTPException: 500 for database errors
            HTTPException: 504 for timeout errors
        """
        try:
            # Query prize
            prizes = await self.zerodb.tables.query_rows(
                "prizes",
                filter={"prize_id": prize_id, "hackathon_id": hackathon_id},
            )

            if not prizes:
                logger.warning(
                    f"Prize {prize_id} not found for hackathon {hackathon_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Prize {prize_id} not found",
                )

            prize = prizes[0]

            # Parse datetime strings and amount
            if "created_at" in prize and isinstance(prize["created_at"], str):
                prize["created_at"] = datetime.fromisoformat(prize["created_at"])
            if "updated_at" in prize and isinstance(prize["updated_at"], str):
                prize["updated_at"] = datetime.fromisoformat(prize["updated_at"])
            if "amount" in prize and prize["amount"] is not None:
                prize["amount"] = Decimal(str(prize["amount"]))

            logger.info(f"Retrieved prize {prize_id}")
            return prize

        except HTTPException:
            raise

        except ZeroDBTimeoutError as e:
            logger.error(f"Timeout getting prize: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timed out. Please try again.",
            )

        except (ZeroDBError, ZeroDBNotFound) as e:
            logger.error(f"Database error getting prize: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve prize. Please contact support.",
            )

        except Exception as e:
            logger.error(f"Unexpected error getting prize: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please contact support.",
            )

    async def update_prize(
        self,
        hackathon_id: str,
        prize_id: str,
        update_data: Dict,
    ) -> Dict:
        """
        Update a prize.

        Args:
            hackathon_id: UUID of the hackathon
            prize_id: UUID of the prize
            update_data: Fields to update

        Returns:
            Updated prize record

        Raises:
            HTTPException: 404 if prize not found
            HTTPException: 404 if track_id updated to invalid track
            HTTPException: 409 if rank conflicts with existing prize
            HTTPException: 500 for database errors
            HTTPException: 504 for timeout errors
        """
        try:
            # Verify prize exists and belongs to hackathon
            prizes = await self.zerodb.tables.query_rows(
                "prizes",
                filter={"prize_id": prize_id, "hackathon_id": hackathon_id},
            )

            if not prizes:
                logger.warning(
                    f"Prize {prize_id} not found for hackathon {hackathon_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Prize {prize_id} not found",
                )

            current_prize = prizes[0]

            # If track_id is being updated, verify the new track exists
            if "track_id" in update_data and update_data["track_id"] is not None:
                tracks = await self.zerodb.tables.query_rows(
                    "tracks",
                    filter={
                        "track_id": update_data["track_id"],
                        "hackathon_id": hackathon_id,
                    },
                )

                if not tracks:
                    logger.warning(
                        f"Track {update_data['track_id']} not found for hackathon {hackathon_id}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Track {update_data['track_id']} not found for this hackathon",
                    )

            # If rank or track_id is being updated, check for conflicts
            if "rank" in update_data or "track_id" in update_data:
                new_rank = update_data.get("rank", current_prize.get("rank"))
                new_track_id = update_data.get("track_id", current_prize.get("track_id"))

                # Build conflict check filter
                conflict_filter = {
                    "hackathon_id": hackathon_id,
                    "rank": new_rank,
                }

                if new_track_id:
                    conflict_filter["track_id"] = new_track_id
                else:
                    conflict_filter["track_id"] = None

                existing_prizes = await self.zerodb.tables.query_rows(
                    "prizes",
                    filter=conflict_filter,
                )

                # Check if conflict exists with a different prize
                if existing_prizes and existing_prizes[0].get("prize_id") != prize_id:
                    scope = f"track {new_track_id}" if new_track_id else "hackathon"
                    logger.warning(
                        f"Prize with rank {new_rank} already exists for {scope} in hackathon {hackathon_id}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Prize with rank {new_rank} already exists for this {scope}",
                    )

            # Convert Decimal to string for storage if amount is being updated
            if "amount" in update_data and update_data["amount"] is not None:
                update_data["amount"] = str(update_data["amount"])

            # Update prize
            update_data["updated_at"] = datetime.utcnow().isoformat()

            await self.zerodb.tables.update_rows(
                "prizes",
                filter={"prize_id": prize_id},
                data=update_data,
            )

            # Retrieve updated prize
            updated_prizes = await self.zerodb.tables.query_rows(
                "prizes",
                filter={"prize_id": prize_id},
            )

            prize = updated_prizes[0]

            # Parse datetime strings and amount
            if "created_at" in prize and isinstance(prize["created_at"], str):
                prize["created_at"] = datetime.fromisoformat(prize["created_at"])
            if "updated_at" in prize and isinstance(prize["updated_at"], str):
                prize["updated_at"] = datetime.fromisoformat(prize["updated_at"])
            if "amount" in prize and prize["amount"] is not None:
                prize["amount"] = Decimal(str(prize["amount"]))

            logger.info(f"Updated prize {prize_id}")
            return prize

        except HTTPException:
            raise

        except ZeroDBTimeoutError as e:
            logger.error(f"Timeout updating prize: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timed out. Please try again.",
            )

        except (ZeroDBError, ZeroDBNotFound) as e:
            logger.error(f"Database error updating prize: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update prize. Please contact support.",
            )

        except Exception as e:
            logger.error(f"Unexpected error updating prize: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please contact support.",
            )

    async def delete_prize(self, hackathon_id: str, prize_id: str) -> Dict:
        """
        Delete a prize.

        Args:
            hackathon_id: UUID of the hackathon
            prize_id: UUID of the prize

        Returns:
            Deletion confirmation

        Raises:
            HTTPException: 404 if prize not found
            HTTPException: 500 for database errors
            HTTPException: 504 for timeout errors
        """
        try:
            # Verify prize exists and belongs to hackathon
            prizes = await self.zerodb.tables.query_rows(
                "prizes",
                filter={"prize_id": prize_id, "hackathon_id": hackathon_id},
            )

            if not prizes:
                logger.warning(
                    f"Prize {prize_id} not found for hackathon {hackathon_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Prize {prize_id} not found",
                )

            # Delete prize
            await self.zerodb.tables.delete_rows(
                "prizes",
                filter={"prize_id": prize_id},
            )

            logger.info(f"Deleted prize {prize_id}")
            return {
                "success": True,
                "prize_id": prize_id,
                "message": "Prize successfully deleted",
            }

        except HTTPException:
            raise

        except ZeroDBTimeoutError as e:
            logger.error(f"Timeout deleting prize: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timed out. Please try again.",
            )

        except (ZeroDBError, ZeroDBNotFound) as e:
            logger.error(f"Database error deleting prize: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete prize. Please contact support.",
            )

        except Exception as e:
            logger.error(f"Unexpected error deleting prize: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please contact support.",
            )
