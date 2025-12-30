"""
Migration script to move hackathon_themes data from Supabase to ZeroDB.

Exports data from Supabase and imports into ZeroDB with schema transformation.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from decimal import Decimal
from typing import List, Dict
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.zerodb.client import ZeroDBClient
from config import settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Supabase credentials (should be in environment variables)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


async def fetch_from_supabase() -> List[Dict]:
    """
    Fetch hackathon_themes data from Supabase.

    Returns:
        List of theme dictionaries

    Note:
        Requires SUPABASE_URL and SUPABASE_KEY environment variables.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        raise ValueError("Missing Supabase credentials")

    try:
        # Import supabase client
        from supabase import create_client, Client

        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Fetch all themes
        response = supabase.table("hackathon_themes").select("*").execute()

        logger.info(f"Fetched {len(response.data)} themes from Supabase")
        return response.data

    except ImportError:
        logger.error("supabase-py not installed. Run: pip install supabase")
        raise
    except Exception as e:
        logger.error(f"Error fetching from Supabase: {str(e)}")
        raise


def transform_theme_data(supabase_theme: Dict) -> Dict:
    """
    Transform Supabase theme data to ZeroDB schema.

    Supabase schema:
        - id (UUID)
        - theme_name (TEXT)
        - hackathon_count (INTEGER)
        - total_prizes (NUMERIC)
        - display_order (INTEGER)
        - created_at (TIMESTAMPTZ)

    ZeroDB schema:
        - id (string, UUID)
        - theme_name (string)
        - description (string, optional)
        - icon (string, optional)
        - hackathon_count (integer)
        - total_prizes (string, decimal)
        - display_order (integer)
        - created_at (string, ISO)
        - updated_at (string, ISO)

    Args:
        supabase_theme: Theme data from Supabase

    Returns:
        Transformed theme data for ZeroDB
    """
    # Convert UUID to string if needed
    theme_id = str(supabase_theme.get("id", uuid4()))

    # Convert timestamp to ISO string
    created_at = supabase_theme.get("created_at")
    if isinstance(created_at, str):
        created_at_iso = created_at
    else:
        created_at_iso = datetime.utcnow().isoformat()

    # Convert total_prizes to string
    total_prizes = supabase_theme.get("total_prizes", 0)
    if isinstance(total_prizes, (int, float, Decimal)):
        total_prizes_str = str(Decimal(str(total_prizes)))
    else:
        total_prizes_str = str(total_prizes)

    return {
        "id": theme_id,
        "theme_name": supabase_theme.get("theme_name", "Unknown"),
        "description": supabase_theme.get("description"),  # May be None
        "icon": supabase_theme.get("icon"),  # May be None
        "hackathon_count": supabase_theme.get("hackathon_count", 0),
        "total_prizes": total_prizes_str,
        "display_order": supabase_theme.get("display_order", 999),
        "created_at": created_at_iso,
        "updated_at": datetime.utcnow().isoformat()
    }


async def import_to_zerodb(themes: List[Dict], zerodb: ZeroDBClient) -> int:
    """
    Import transformed themes into ZeroDB.

    Args:
        themes: List of transformed theme dictionaries
        zerodb: ZeroDB client instance

    Returns:
        Number of themes successfully imported
    """
    imported_count = 0

    for theme in themes:
        try:
            # Check if theme already exists
            existing = await zerodb.tables.query_rows(
                table_id="hackathon_themes",
                filter={"theme_name": theme["theme_name"]},
                limit=1
            )

            if existing and existing.get("rows"):
                logger.warning(f"Theme '{theme['theme_name']}' already exists, skipping")
                continue

            # Insert theme
            await zerodb.tables.insert_rows(
                table_id="hackathon_themes",
                rows=[theme]
            )

            logger.info(f"Imported theme: {theme['theme_name']}")
            imported_count += 1

        except Exception as e:
            logger.error(f"Failed to import theme '{theme.get('theme_name')}': {str(e)}")
            continue

    return imported_count


async def verify_migration(zerodb: ZeroDBClient) -> Dict:
    """
    Verify migration by comparing counts and data integrity.

    Args:
        zerodb: ZeroDB client instance

    Returns:
        Dictionary with verification results
    """
    try:
        # Count themes in ZeroDB
        response = await zerodb.tables.query_rows(
            table_id="hackathon_themes",
            filter={},
            limit=1000
        )

        themes = response.get("rows", [])
        theme_count = len(themes)

        # Check for required fields
        missing_fields = []
        for theme in themes:
            if not theme.get("theme_name"):
                missing_fields.append(f"Theme {theme.get('id')} missing theme_name")
            if theme.get("display_order") is None:
                missing_fields.append(f"Theme {theme.get('id')} missing display_order")

        return {
            "success": len(missing_fields) == 0,
            "total_themes": theme_count,
            "missing_fields": missing_fields,
            "themes": [t.get("theme_name") for t in themes]
        }

    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def main():
    """
    Main migration flow.

    Steps:
    1. Fetch themes from Supabase
    2. Transform data to ZeroDB schema
    3. Import into ZeroDB
    4. Verify migration
    """
    logger.info("=" * 60)
    logger.info("Hackathon Themes Migration: Supabase → ZeroDB")
    logger.info("=" * 60)

    # Initialize ZeroDB client
    zerodb = ZeroDBClient(
        api_url=settings.ZERODB_API_URL,
        api_key=settings.ZERODB_API_KEY
    )

    try:
        # Step 1: Fetch from Supabase
        logger.info("\n[1/4] Fetching data from Supabase...")
        supabase_themes = await fetch_from_supabase()
        logger.info(f"✓ Fetched {len(supabase_themes)} themes")

        # Step 2: Transform data
        logger.info("\n[2/4] Transforming data...")
        transformed_themes = [transform_theme_data(theme) for theme in supabase_themes]
        logger.info(f"✓ Transformed {len(transformed_themes)} themes")

        # Step 3: Import to ZeroDB
        logger.info("\n[3/4] Importing to ZeroDB...")
        imported_count = await import_to_zerodb(transformed_themes, zerodb)
        logger.info(f"✓ Imported {imported_count}/{len(transformed_themes)} themes")

        # Step 4: Verify
        logger.info("\n[4/4] Verifying migration...")
        verification = await verify_migration(zerodb)

        if verification["success"]:
            logger.info(f"✓ Verification passed!")
            logger.info(f"  Total themes in ZeroDB: {verification['total_themes']}")
            logger.info(f"  Themes: {', '.join(verification['themes'])}")
        else:
            logger.error("✗ Verification failed!")
            if "missing_fields" in verification:
                for issue in verification["missing_fields"]:
                    logger.error(f"  - {issue}")
            if "error" in verification:
                logger.error(f"  Error: {verification['error']}")

        logger.info("\n" + "=" * 60)
        logger.info("Migration Complete")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"\n✗ Migration failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
