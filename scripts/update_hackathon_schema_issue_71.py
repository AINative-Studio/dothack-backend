"""
Migrate existing hackathons to add new fields (Issue #71).

Adds the following fields to existing hackathon records:
- logo_url (optional string)
- is_online (boolean, default False)
- participant_count (integer, calculated from hackathon_participants)

Usage:
    python scripts/update_hackathon_schema_issue_71.py --dry-run  # Preview only
    python scripts/update_hackathon_schema_issue_71.py --apply    # Apply changes
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent / "python-api"))

from integrations.zerodb.client import ZeroDBClient
from config import settings


async def count_participants(zerodb: ZeroDBClient, hackathon_id: str) -> int:
    """
    Count participants for a hackathon.

    Args:
        zerodb: ZeroDB client instance
        hackathon_id: Hackathon UUID

    Returns:
        Number of participants (including organizers)
    """
    try:
        participants = await zerodb.tables.query_rows(
            "hackathon_participants",
            filter={"hackathon_id": hackathon_id}
        )
        return len(participants) if participants else 0
    except Exception as e:
        print(f"    Warning: Could not count participants for {hackathon_id}: {str(e)}")
        return 0


async def migrate_hackathons(dry_run: bool = False):
    """
    Migrate existing hackathons to add new fields.

    Args:
        dry_run: If True, only print what would be updated
    """
    print("=" * 60)
    print("Update Hackathon Schema Migration (Issue #71)")
    print("=" * 60)
    print()

    if dry_run:
        print("DRY RUN MODE - No changes will be made\n")
    else:
        print("APPLY MODE - Hackathons will be updated\n")

    try:
        zerodb = ZeroDBClient(
            api_key=settings.ZERODB_API_KEY,
            project_id=settings.ZERODB_PROJECT_ID,
            base_url=settings.ZERODB_BASE_URL
        )

        # Fetch all hackathons
        print("Fetching existing hackathons...")
        hackathons = await zerodb.tables.query_rows("hackathons", filter={})

        if not hackathons:
            print("\nNo hackathons found. Nothing to migrate.")
            return

        print(f"Found {len(hackathons)} hackathons to update\n")

        updated_count = 0
        skipped_count = 0

        for hackathon in hackathons:
            hackathon_id = hackathon.get("hackathon_id")
            name = hackathon.get("name", "Unknown")

            # Check if hackathon already has the new fields
            has_logo_url = "logo_url" in hackathon
            has_is_online = "is_online" in hackathon
            has_participant_count = "participant_count" in hackathon

            if has_logo_url and has_is_online and has_participant_count:
                print(f"  SKIP: {name} (already has new fields)")
                skipped_count += 1
                continue

            print(f"  UPDATE: {name}")

            # Calculate participant count
            participant_count = await count_participants(zerodb, hackathon_id)
            print(f"    - Calculated participant_count: {participant_count}")

            update_fields: Dict[str, Any] = {}

            if not has_logo_url:
                update_fields["logo_url"] = None
                print("    - Adding logo_url: null")

            if not has_is_online:
                update_fields["is_online"] = False
                print("    - Adding is_online: false")

            if not has_participant_count:
                update_fields["participant_count"] = participant_count
                print(f"    - Adding participant_count: {participant_count}")

            if dry_run:
                print("    - [DRY RUN] Would update with above fields")
            else:
                # Apply updates
                await zerodb.tables.update_rows(
                    "hackathons",
                    filter={"hackathon_id": hackathon_id},
                    update={"$set": update_fields}
                )
                print("    - Successfully updated")
                updated_count += 1

            print()

        print("=" * 60)
        print("Migration Summary")
        print("=" * 60)
        print(f"Total hackathons: {len(hackathons)}")
        print(f"Updated: {updated_count}")
        print(f"Skipped (already migrated): {skipped_count}")

        if dry_run:
            print("\nDRY RUN COMPLETE - No changes made")
        else:
            print("\nMigration complete!")

    except Exception as e:
        print(f"\nError during migration: {str(e)}")
        raise


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate existing hackathons to add new fields (Issue #71)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes and update hackathons"
    )

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.error("Must specify either --dry-run or --apply")

    asyncio.run(migrate_hackathons(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
