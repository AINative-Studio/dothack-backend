"""
Create hackathon_themes table in ZeroDB.

Usage:
    python scripts/create_hackathon_themes_table.py --dry-run  # Preview only
    python scripts/create_hackathon_themes_table.py --apply    # Create table
"""

import asyncio
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python-api"))

from integrations.zerodb.client import ZeroDBClient
from config import settings


HACKATHON_THEMES_SCHEMA = {
    "name": "hackathon_themes",
    "columns": [
        {
            "name": "id",
            "type": "uuid",
            "nullable": False,
            "primary_key": True,
            "description": "Unique theme identifier"
        },
        {
            "name": "theme_name",
            "type": "text",
            "nullable": False,
            "unique": True,
            "description": "Name of the hackathon theme (must be unique)"
        },
        {
            "name": "description",
            "type": "text",
            "nullable": True,
            "description": "Theme description"
        },
        {
            "name": "icon",
            "type": "text",
            "nullable": True,
            "description": "Icon name or emoji for the theme"
        },
        {
            "name": "hackathon_count",
            "type": "integer",
            "nullable": False,
            "default": 0,
            "description": "Number of hackathons with this theme"
        },
        {
            "name": "total_prizes",
            "type": "numeric",
            "nullable": False,
            "default": 0,
            "description": "Total prize pool across all hackathons with this theme"
        },
        {
            "name": "display_order",
            "type": "integer",
            "nullable": False,
            "default": 0,
            "description": "Display order for homepage (lower = higher priority)"
        },
        {
            "name": "created_at",
            "type": "timestamptz",
            "nullable": False,
            "description": "Creation timestamp"
        },
        {
            "name": "updated_at",
            "type": "timestamptz",
            "nullable": False,
            "description": "Last update timestamp"
        }
    ],
    "indexes": [
        {
            "columns": ["theme_name"],
            "unique": True
        },
        {
            "columns": ["display_order"]
        }
    ]
}


async def create_table(dry_run: bool = False):
    """
    Create hackathon_themes table in ZeroDB.

    Args:
        dry_run: If True, only print what would be created
    """
    print("=" * 60)
    print("Create hackathon_themes Table Script")
    print("=" * 60)
    print()

    if dry_run:
        print("\U0001F440 DRY RUN MODE - No changes will be made\n")
    else:
        print("\U0001F680 APPLY MODE - Table will be created\n")

    print(f"Table: {HACKATHON_THEMES_SCHEMA['name']}")
    print(f"Columns: {len(HACKATHON_THEMES_SCHEMA['columns'])}")
    print(f"Indexes: {len(HACKATHON_THEMES_SCHEMA['indexes'])}")
    print()

    print("Schema:")
    for col in HACKATHON_THEMES_SCHEMA['columns']:
        nullable = "" if col['nullable'] else "NOT NULL"
        pk = "PRIMARY KEY" if col.get('primary_key') else ""
        unique = "UNIQUE" if col.get('unique') else ""
        default = f"DEFAULT {col['default']}" if 'default' in col else ""
        print(f"  - {col['name']:<20} {col['type']:<15} {nullable:<10} {pk:<12} {unique:<8} {default}")

    print("\nIndexes:")
    for idx in HACKATHON_THEMES_SCHEMA['indexes']:
        unique_idx = "UNIQUE" if idx.get('unique') else ""
        print(f"  - {', '.join(idx['columns'])} {unique_idx}")

    if dry_run:
        print("\n\U00002705 DRY RUN COMPLETE - No changes made")
        return

    print("\nCreating table...")

    try:
        zerodb = ZeroDBClient(
            api_key=settings.ZERODB_API_KEY,
            project_id=settings.ZERODB_PROJECT_ID,
            base_url=settings.ZERODB_BASE_URL
        )

        existing_tables = await zerodb.tables.list_tables()
        if HACKATHON_THEMES_SCHEMA['name'] in [t['name'] for t in existing_tables.get('tables', [])]:
            print(f"\n\U000026A0\U0000FE0F  Table '{HACKATHON_THEMES_SCHEMA['name']}' already exists. Skipping creation.")
            return

        await zerodb.tables.create_table(HACKATHON_THEMES_SCHEMA)

        print(f"\n\U00002705 Successfully created table: {HACKATHON_THEMES_SCHEMA['name']}")

    except Exception as e:
        print(f"\n\U0000274C Error creating table: {str(e)}")
        raise


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Create hackathon_themes table in ZeroDB"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes and create table"
    )

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.error("Must specify either --dry-run or --apply")

    asyncio.run(create_table(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
