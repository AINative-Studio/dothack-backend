"""
Pytest environment setup for integration tests.

This module is loaded BEFORE conftest to set up environment variables.
"""

import os


def pytest_configure(config):
    """
    Set up test environment variables before any tests run.

    This runs before conftest.py imports, ensuring environment is set up correctly.
    """
    # Set test environment variables
    os.environ["ENVIRONMENT"] = "test"
    os.environ["LOG_LEVEL"] = "INFO"
    os.environ["API_VERSION"] = "v1"
    os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000,http://localhost:5173"
    os.environ["ZERODB_API_KEY"] = "test_key"
    os.environ["ZERODB_PROJECT_ID"] = "test_project"
    os.environ["ZERODB_BASE_URL"] = "https://api.ainative.studio"
    os.environ["ZERODB_TIMEOUT"] = "30.0"
