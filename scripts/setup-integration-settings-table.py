#!/usr/bin/env python3
"""
Integration Settings Table Creation Script

Creates the integration_settings table for storing encrypted API keys
and external service configuration.

Usage:
    python scripts/setup-integration-settings-table.py --dry-run   # Preview table
    python scripts/setup-integration-settings-table.py --apply     # Create table
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add python-api to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python-api"))

from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.tables import TablesAPI


# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


TABLE_SCHEMAS = {
    "integration_settings": {
        "description": "External integration settings and encrypted API keys",
        "schema": {
            "fields": {
                "id": {"type": "uuid", "primary_key": True},
                "user_id": {"type": "text", "required": True},
                "integration_type": {"type": "text", "required": True},
                "api_key_encrypted": {"type": "text", "required": True},
                "calendar_name": {"type": "text"},
                "status": {"type": "text", "check": "status IN ('connected', 'disconnected', 'error')"},
                "sync_options": {"type": "jsonb"},
                "last_synced_at": {"type": "timestamp"},
                "created_at": {"type": "timestamp", "default": "NOW()"},
                "updated_at": {"type": "timestamp", "default": "NOW()"}
            }
        }
    }
}


def print_header(message: str):
    """Print colored header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message:^70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def print_success(message: str):
    """Print success message in green."""
    print(f"{Colors.GREEN}+ {message}{Colors.END}")


def print_warning(message: str):
    """Print warning message in yellow."""
    print(f"{Colors.YELLOW}! {message}{Colors.END}")


def print_error(message: str):
    """Print error message in red."""
    print(f"{Colors.RED}x {message}{Colors.END}")


def print_info(message: str):
    """Print info message in blue."""
    print(f"{Colors.BLUE}i {message}{Colors.END}")


async def check_existing_tables(tables_api: TablesAPI) -> set:
    """Check which tables already exist in ZeroDB."""
    try:
        existing_tables = await tables_api.list()
        table_names = {table.get("name") for table in existing_tables.get("tables", [])}
        return table_names
    except Exception as e:
        print_warning(f"Could not fetch existing tables: {e}")
        return set()


async def create_table(
    tables_api: TablesAPI,
    table_name: str,
    table_config: dict,
    dry_run: bool = False
) -> bool:
    """Create a single table in ZeroDB."""
    try:
        if dry_run:
            print_info(f"Would create table: {table_name}")
            print(f"  Description: {table_config['description']}")
            print(f"  Fields: {len(table_config['schema']['fields'])} columns")
            return True

        result = await tables_api.create(
            name=table_name,
            schema=table_config["schema"],
            description=table_config["description"]
        )

        print_success(f"Created table: {table_name}")
        return True

    except Exception as e:
        print_error(f"Failed to create table {table_name}: {e}")
        return False


async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Create integration_settings table in ZeroDB"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview table without creating it"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create table in ZeroDB"
    )

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.print_help()
        print_error("\nError: Must specify either --dry-run or --apply")
        sys.exit(1)

    mode = "DRY RUN MODE" if args.dry_run else "APPLY MODE"
    print_header(f"Integration Settings Table Setup - {mode}")

    # Initialize ZeroDB client
    try:
        client = ZeroDBClient()
        tables_api = TablesAPI(client)
        print_success("Connected to ZeroDB")
    except Exception as e:
        print_error(f"Failed to connect to ZeroDB: {e}")
        print_info("Make sure ZERODB_API_KEY and ZERODB_PROJECT_ID are set")
        sys.exit(1)

    # Check existing tables
    existing_tables = set()
    if not args.dry_run:
        print_info("Checking for existing tables...")
        existing_tables = await check_existing_tables(tables_api)

    # Create tables
    print_info(f"\nProcessing {len(TABLE_SCHEMAS)} table(s)...\n")

    created = 0
    skipped = 0
    failed = 0

    for table_name, table_config in TABLE_SCHEMAS.items():
        if not args.dry_run and table_name in existing_tables:
            print_warning(f"Skipped table (already exists): {table_name}")
            skipped += 1
            continue

        success = await create_table(tables_api, table_name, table_config, args.dry_run)

        if success:
            created += 1
        else:
            failed += 1

    # Print summary
    print_header("Summary")

    if args.dry_run:
        print_info(f"Would create: {created} table(s)")
    else:
        print_success(f"Created: {created} table(s)")
        if skipped > 0:
            print_warning(f"Skipped: {skipped} table(s) (already exist)")
        if failed > 0:
            print_error(f"Failed: {failed} table(s)")

    if failed > 0:
        sys.exit(1)
    else:
        print_success("\nTable setup complete!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
