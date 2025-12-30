#!/usr/bin/env python3
"""
Verify ZeroDB connection and credentials
"""
import asyncio
import os
import sys
from pathlib import Path

# Add python-api to path
sys.path.insert(0, str(Path(__file__).parent / "python-api"))

from dotenv import load_dotenv
from integrations.zerodb.client import ZeroDBClient


async def verify_connection():
    """Test ZeroDB connection with credentials from .env"""

    # Load environment variables
    load_dotenv()

    print("=" * 60)
    print("ZeroDB Connection Verification")
    print("=" * 60)

    # Display configuration (masked)
    api_key = os.getenv("ZERODB_API_KEY", "")
    project_id = os.getenv("ZERODB_PROJECT_ID", "")
    base_url = os.getenv("ZERODB_BASE_URL", "")

    print(f"\nConfiguration:")
    print(f"  Base URL: {base_url}")
    print(f"  Project ID: {project_id}")
    print(f"  API Key: {'*' * 20}{api_key[-8:] if len(api_key) > 8 else '***'}")

    # Test connection
    print(f"\nTesting connection...")

    try:
        async with ZeroDBClient() as client:
            # Get project info
            project_info = await client.get_project_info()

            print("\n✅ Connection successful!")
            print(f"\nProject Information:")
            print(f"  Name: {project_info.get('name', 'N/A')}")
            print(f"  ID: {project_info.get('id', 'N/A')}")
            print(f"  Status: {project_info.get('status', 'N/A')}")

            # Check enabled features
            if 'features' in project_info:
                print(f"\nEnabled Features:")
                for feature, enabled in project_info['features'].items():
                    status = "✅" if enabled else "❌"
                    print(f"  {status} {feature}")

            return True

    except Exception as e:
        print(f"\n❌ Connection failed!")
        print(f"Error: {type(e).__name__}: {str(e)}")
        return False


if __name__ == "__main__":
    success = asyncio.run(verify_connection())
    sys.exit(0 if success else 1)
