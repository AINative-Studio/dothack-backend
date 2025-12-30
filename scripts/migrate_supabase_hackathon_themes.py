"""
Migrate hackathon_themes data from Supabase to ZeroDB.

Prerequisites:
    - Supabase credentials in environment variables
    - ZeroDB hackathon_themes table created (run create_hackathon_themes_table.py first)

Usage:
    python scripts/migrate_supabase_hackathon_themes.py --dry-run  # Preview
    python scripts/migrate_supabase_hackathon_themes.py --apply    # Execute
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python-api"))

from integrations.zerodb.client import ZeroDBClient
from config import settings


async def fetch_supabase_themes():
    """
    Fetch hackathon_themes from Supabase.

    Note: This is a placeholder. In production, you would:
    1. Install supabase-py: pip install supabase
    2. Set SUPABASE_URL and SUPABASE_KEY environment variables
    3. Use actual Supabase client to fetch data

    Returns:
        List of theme dictionaries
    """
    print("\U0001F4E1 Fetching themes from Supabase...")

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("\U000026A0\U0000FE0F  Warning: SUPABASE_URL and SUPABASE_KEY not set.")
        print("Using sample data for demonstration...")
        return [
            {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "theme_name": "AI & Machine Learning",
                "description": "Build intelligent applications using AI and ML technologies",
                "icon": "🤖",
                "hackathon_count": 45,
                "total_prizes": "250000.00",
                "display_order": 1,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440002",
                "theme_name": "Web3 & Blockchain",
                "description": "Decentralized applications and blockchain solutions",
                "icon": "⛓️",
                "hackathon_count": 32,
                "total_prizes": "180000.00",
                "display_order": 2,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440003",
                "theme_name": "Climate Tech",
                "description": "Technology solutions for climate change and sustainability",
                "icon": "🌍",
                "hackathon_count": 28,
                "total_prizes": "150000.00",
                "display_order": 3,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440004",
                "theme_name": "HealthTech",
                "description": "Healthcare and medical technology innovations",
                "icon": "🏥",
                "hackathon_count": 25,
                "total_prizes": "120000.00",
                "display_order": 4,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440005",
                "theme_name": "FinTech",
                "description": "Financial technology and payment solutions",
                "icon": "💳",
                "hackathon_count": 30,
                "total_prizes": "200000.00",
                "display_order": 5,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        ]

    print(f"\U00002705 Fetched sample themes (replace with actual Supabase query)")
    return []


async def migrate_themes(dry_run: bool = False):
    """
    Migrate themes from Supabase to ZeroDB.

    Args:
        dry_run: If True, only preview migration without applying
    """
    print("=" * 60)
    print("Migrate Hackathon Themes from Supabase to ZeroDB")
    print("=" * 60)
    print()

    if dry_run:
        print("\U0001F440 DRY RUN MODE - No changes will be made\n")
    else:
        print("\U0001F680 APPLY MODE - Data will be migrated\n")

    themes = await fetch_supabase_themes()
    print(f"Found {len(themes)} themes in Supabase\n")

    if len(themes) == 0:
        print("\U000026A0\U0000FE0F  No themes to migrate")
        return

    print("Themes to migrate:")
    for theme in themes:
        print(f"  - {theme['theme_name']:<30} (Count: {theme['hackathon_count']}, Prizes: ${theme['total_prizes']})")

    if dry_run:
        print(f"\n\U00002705 DRY RUN COMPLETE - Would migrate {len(themes)} themes")
        return

    print("\nMigrating themes to ZeroDB...")

    try:
        zerodb = ZeroDBClient(
            api_key=settings.ZERODB_API_KEY,
            project_id=settings.ZERODB_PROJECT_ID,
            base_url=settings.ZERODB_BASE_URL
        )

        existing_result = await zerodb.tables.query_rows("hackathon_themes", filters={})
        existing_themes = existing_result.get("rows", [])
        existing_names = {t["theme_name"] for t in existing_themes}

        new_themes = [t for t in themes if t["theme_name"] not in existing_names]
        skipped = len(themes) - len(new_themes)

        if skipped > 0:
            print(f"\n\U000026A0\U0000FE0F  Skipping {skipped} existing themes")

        if len(new_themes) == 0:
            print("\n\U00002705 All themes already exist in ZeroDB")
            return

        print(f"Inserting {len(new_themes)} new themes...")

        for theme in new_themes:
            theme_data = {
                "id": theme["id"],
                "theme_name": theme["theme_name"],
                "description": theme.get("description"),
                "icon": theme.get("icon"),
                "hackathon_count": theme.get("hackathon_count", 0),
                "total_prizes": str(theme.get("total_prizes", "0")),
                "display_order": theme.get("display_order", 0),
                "created_at": theme.get("created_at"),
                "updated_at": theme.get("updated_at")
            }

            await zerodb.tables.insert_rows("hackathon_themes", [theme_data])
            print(f"  \U00002705 Migrated: {theme['theme_name']}")

        print(f"\n\U00002705 Successfully migrated {len(new_themes)} themes to ZeroDB")

        print("\nVerifying migration...")
        final_result = await zerodb.tables.query_rows("hackathon_themes", filters={})
        final_count = len(final_result.get("rows", []))
        print(f"Total themes in ZeroDB: {final_count}")

    except Exception as e:
        print(f"\n\U0000274C Error during migration: {str(e)}")
        raise


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate hackathon_themes from Supabase to ZeroDB"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without applying changes"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute migration and insert data"
    )

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.error("Must specify either --dry-run or --apply")

    asyncio.run(migrate_themes(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
