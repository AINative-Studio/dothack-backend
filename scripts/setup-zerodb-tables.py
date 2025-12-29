#!/usr/bin/env python3
"""
ZeroDB Table Creation Script

Creates all 10 core tables for DotHack Backend.
Supports dry-run mode and idempotent execution.

Usage:
    python scripts/setup-zerodb-tables.py --dry-run   # Preview tables
    python scripts/setup-zerodb-tables.py --apply     # Create tables
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


# Table schemas from PRD Section 3.1
TABLE_SCHEMAS = {
    "hackathons": {
        "description": "Hackathon events and configuration",
        "schema": {
            "fields": {
                "hackathon_id": {"type": "uuid", "primary_key": True},
                "name": {"type": "text", "required": True},
                "description": {"type": "text"},
                "status": {
                    "type": "text",
                    "check": "status IN ('DRAFT', 'LIVE', 'CLOSED')"
                },
                "start_at": {"type": "timestamp"},
                "end_at": {"type": "timestamp"},
                "tracks_config": {"type": "jsonb"},
                "rubric_config": {"type": "jsonb"},
                "created_at": {"type": "timestamp", "default": "NOW()"},
                "updated_at": {"type": "timestamp", "default": "NOW()"}
            }
        }
    },

    "tracks": {
        "description": "Competition tracks within hackathons",
        "schema": {
            "fields": {
                "track_id": {"type": "uuid", "primary_key": True},
                "hackathon_id": {"type": "uuid", "required": True},
                "name": {"type": "text", "required": True},
                "description": {"type": "text"},
                "requirements": {"type": "jsonb"},
                "max_teams": {"type": "integer"},
                "created_at": {"type": "timestamp", "default": "NOW()"}
            }
        }
    },

    "participants": {
        "description": "User profiles and skills",
        "schema": {
            "fields": {
                "participant_id": {"type": "uuid", "primary_key": True},
                "email": {"type": "text", "unique": True, "required": True},
                "name": {"type": "text", "required": True},
                "org": {"type": "text"},
                "skills": {"type": "jsonb"},
                "bio": {"type": "text"},
                "created_at": {"type": "timestamp", "default": "NOW()"}
            }
        }
    },

    "hackathon_participants": {
        "description": "User-hackathon-role mapping (junction table)",
        "schema": {
            "fields": {
                "id": {"type": "uuid", "primary_key": True},
                "hackathon_id": {"type": "uuid", "required": True},
                "participant_id": {"type": "uuid", "required": True},
                "role": {
                    "type": "text",
                    "check": "role IN ('BUILDER', 'ORGANIZER', 'JUDGE', 'MENTOR')"
                },
                "metadata": {"type": "jsonb"},
                "joined_at": {"type": "timestamp", "default": "NOW()"}
            }
        }
    },

    "teams": {
        "description": "Team information within hackathons",
        "schema": {
            "fields": {
                "team_id": {"type": "uuid", "primary_key": True},
                "hackathon_id": {"type": "uuid", "required": True},
                "name": {"type": "text", "required": True},
                "track_id": {"type": "uuid"},
                "description": {"type": "text"},
                "status": {
                    "type": "text",
                    "check": "status IN ('FORMING', 'ACTIVE', 'SUBMITTED')"
                },
                "created_at": {"type": "timestamp", "default": "NOW()"}
            }
        }
    },

    "team_members": {
        "description": "Team membership tracking (junction table)",
        "schema": {
            "fields": {
                "id": {"type": "uuid", "primary_key": True},
                "team_id": {"type": "uuid", "required": True},
                "participant_id": {"type": "uuid", "required": True},
                "role": {
                    "type": "text",
                    "check": "role IN ('LEAD', 'MEMBER')"
                },
                "joined_at": {"type": "timestamp", "default": "NOW()"}
            }
        }
    },

    "projects": {
        "description": "Project submissions",
        "schema": {
            "fields": {
                "project_id": {"type": "uuid", "primary_key": True},
                "hackathon_id": {"type": "uuid", "required": True},
                "team_id": {"type": "uuid", "required": True},
                "title": {"type": "text", "required": True},
                "one_liner": {"type": "text"},
                "description": {"type": "text"},
                "status": {
                    "type": "text",
                    "check": "status IN ('IDEA', 'BUILDING', 'SUBMITTED')"
                },
                "repo_url": {"type": "text"},
                "demo_url": {"type": "text"},
                "tech_stack": {"type": "jsonb"},
                "created_at": {"type": "timestamp", "default": "NOW()"},
                "updated_at": {"type": "timestamp", "default": "NOW()"}
            }
        }
    },

    "submissions": {
        "description": "Submission artifacts and descriptions",
        "schema": {
            "fields": {
                "submission_id": {"type": "uuid", "primary_key": True},
                "project_id": {"type": "uuid", "required": True},
                "submitted_at": {"type": "timestamp"},
                "submission_text": {"type": "text", "required": True},
                "artifact_links": {"type": "jsonb"},
                "video_url": {"type": "text"},
                "vector_namespace": {"type": "text"},
                "created_at": {"type": "timestamp", "default": "NOW()"}
            }
        }
    },

    "rubrics": {
        "description": "Judging criteria and scoring frameworks",
        "schema": {
            "fields": {
                "rubric_id": {"type": "uuid", "primary_key": True},
                "hackathon_id": {"type": "uuid", "required": True},
                "title": {"type": "text", "required": True},
                "criteria": {"type": "jsonb", "required": True},
                "total_points": {"type": "integer"},
                "created_at": {"type": "timestamp", "default": "NOW()"}
            }
        }
    },

    "scores": {
        "description": "Judge scores and feedback",
        "schema": {
            "fields": {
                "score_id": {"type": "uuid", "primary_key": True},
                "submission_id": {"type": "uuid", "required": True},
                "judge_participant_id": {"type": "uuid", "required": True},
                "rubric_id": {"type": "uuid", "required": True},
                "scores_breakdown": {"type": "jsonb"},
                "total_score": {"type": "real"},
                "feedback": {"type": "text"},
                "created_at": {"type": "timestamp", "default": "NOW()"}
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
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_warning(message: str):
    """Print warning message in yellow."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


def print_error(message: str):
    """Print error message in red."""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message: str):
    """Print info message in blue."""
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")


async def check_existing_tables(tables_api: TablesAPI) -> set:
    """
    Check which tables already exist in ZeroDB.

    Returns:
        Set of existing table names
    """
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
    """
    Create a single table in ZeroDB.

    Args:
        tables_api: ZeroDB Tables API client
        table_name: Name of the table
        table_config: Table configuration with schema
        dry_run: If True, only print what would be created

    Returns:
        True if successful, False otherwise
    """
    try:
        if dry_run:
            print_info(f"Would create table: {table_name}")
            print(f"  Description: {table_config['description']}")
            print(f"  Fields: {len(table_config['schema']['fields'])} columns")
            return True

        # Create the table
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
        description="Create ZeroDB tables for DotHack Backend"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview tables without creating them"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create tables in ZeroDB"
    )

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.print_help()
        print_error("\nError: Must specify either --dry-run or --apply")
        sys.exit(1)

    # Print header
    mode = "DRY RUN MODE" if args.dry_run else "APPLY MODE"
    print_header(f"ZeroDB Table Setup - {mode}")

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
    if not args.dry_run:
        print_info("Checking for existing tables...")
        existing_tables = await check_existing_tables(tables_api)
        if existing_tables:
            print_warning(f"Found {len(existing_tables)} existing tables: {', '.join(existing_tables)}")

    # Create tables
    print_info(f"\nProcessing {len(TABLE_SCHEMAS)} tables...\n")

    created = 0
    skipped = 0
    failed = 0

    for table_name, table_config in TABLE_SCHEMAS.items():
        # Skip if table already exists
        if not args.dry_run and table_name in existing_tables:
            print_warning(f"Skipped table (already exists): {table_name}")
            skipped += 1
            continue

        # Create table
        success = await create_table(tables_api, table_name, table_config, args.dry_run)

        if success:
            created += 1
        else:
            failed += 1

    # Print summary
    print_header("Summary")

    if args.dry_run:
        print_info(f"Would create: {created} tables")
    else:
        print_success(f"Created: {created} tables")
        if skipped > 0:
            print_warning(f"Skipped: {skipped} tables (already exist)")
        if failed > 0:
            print_error(f"Failed: {failed} tables")

    # Exit with appropriate code
    if failed > 0:
        sys.exit(1)
    else:
        print_success("\n✓ Table setup complete!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
